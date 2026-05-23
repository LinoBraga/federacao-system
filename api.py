from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, engine, Base
import models

# Importando as funções corretas dos seus submódulos
from importer import extract_games, extract_players, fetch_tournament
from elo import expected, update_rating
from utils import normalize_name
from fpbx_import import import_official_list
from fastapi.responses import StreamingResponse  # Adicione esta importação no topo do arquivo
import io
import csv
# Cria as tabelas do banco de dados caso não existam
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Federação FPBX")

# Gerenciador de conexão com o banco de dados (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# HOME
# -------------------------
@app.get("/")
def home():
    return {"status": "FPBX online"}


# -------------------------
# PLAYERS
# -------------------------
@app.post("/import-fpbx")
def import_fpbx(db: Session = Depends(get_db)):
    count = import_official_list(db, "fpbx_players.csv")
    return {
        "status": "ok",
        "imported": count
    }


@app.get("/players")
def list_players(db: Session = Depends(get_db)):
    return db.query(models.Player).all()


# -------------------------
# RANKING FPBX
# -------------------------
def detect_mode(soup):
    text = soup.get_text(" ").lower()

    # Padrões reais de Chess-Results para detectar o ritmo do torneio
    if "blitz" in text or "b l i t z" in text:
        return "blitz"
    if "rapid" in text or "rpd" in text or "rápido" in text:
        return "rapid"
    if "standard" in text or "std" in text or "clássico" in text:
        return "std"

    # Fallback seguro caso não identifique textualmente
    return "std"


@app.get("/ranking/{mode}")
def ranking_by_mode(mode: str, db: Session = Depends(get_db)):
    if mode == "std":
        order_field = models.Player.rating_std
    elif mode == "rapid":
        order_field = models.Player.rating_rapid
    elif mode == "blitz":
        order_field = models.Player.rating_blitz
    else:
        return {"error": "invalid mode"}

    players = db.query(models.Player).order_by(order_field.desc()).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "rating_std": p.rating_std,
            "rating_rapid": p.rating_rapid,
            "rating_blitz": p.rating_blitz,
            "rating": getattr(p, f"rating_{mode}")
        }
        for p in players
    ]


@app.get("/ranking")
def ranking_general(db: Session = Depends(get_db)):
    players = db.query(models.Player).order_by(
        models.Player.rating_std.desc()
    ).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "rating_std": p.rating_std or 1800,
            "rating_rapid": p.rating_rapid or 1800,
            "rating_blitz": p.rating_blitz or 1800
        }
        for p in players
    ]


# -------------------------
# IMPORT TORNEIO (MOTOR FPBX CORRIGIDO)
# -------------------------
@app.post("/import-tournament")
def import_tournament(url: str, db: Session = Depends(get_db)):
    # 1. Validação Amigável da URL
    url = url.strip()
    if "chess-results.com" not in url.lower():
        raise HTTPException(
            status_code=400, 
            detail="URL inválida. Certifique-se de que está colando um link do site Chess-Results."
        )

    # 2. Inteligência de URL: Auto-ajusta para a página de partidas/confrontos se o usuário colar a errada
    # No Chess-Results, art=2 ou art=4 mostram as tabelas de jogos por rodada.
    if "art=" in url:
        # Substitui qualquer art=X por art=2 (tabela de confrontos/cruza)
        url = re.sub(r"art=\d+", "art=2", url)
    else:
        # Se não tiver o parâmetro art, adiciona ele para forçar a página de partidas
        connector = "&" if "?" in url else "?"
        url = f"{url}{connector}art=2"

    # 3. Evita reprocessar o mesmo torneio
    existing = db.query(models.Tournament).filter_by(url=url).first()
    if existing:
        return {
            "status": "warning",
            "message": "Este torneio já foi importado e os ratings já foram calculados anteriormente."
        }

    # 4. Tenta buscar a página com tratamento de erro amigável
    try:
        soup = fetch_tournament(url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível acessar o Chess-Results. O site pode estar fora do ar ou o link está quebrado. Erro original: {str(e)}"
        )

    # 5. Extração com verificação de conteúdo
    players_names = extract_players(url)
    games = extract_games(url)

    if not games:
        raise HTTPException(
            status_code=422,
            detail="Nenhuma partida válida foi encontrada nesta página. Verifique se o torneio já começou ou se os resultados foram lançados."
        )

    # Cria o registro do torneio apenas se tudo acima deu certo
    tournament = models.Tournament(url=url)
    db.add(tournament)
    db.commit()

    # Garante a ordem cronológica por rodadas
    games = sorted(games, key=lambda g: g["round"])

    # Mapeamento dos Enxadristas
    players_map = {}
    new_players_count = 0

    for name in players_names:
        player = db.query(models.Player).filter_by(name=name).first()

        if not player:
            player = models.Player(
                name=name,
                cbx_id=None,
                rating_std=1800.0,
                rating_rapid=1800.0,
                rating_blitz=1800.0
            )
            db.add(player)
            db.commit()
            db.refresh(player)
            new_players_count += 1

        players_map[name] = player

    # Processamento do Motor Elo
    mode = detect_mode(soup)
    mode_pt = {"std": "Clássico (Standard)", "rapid": "Rápido", "blitz": "Blitz"}.get(mode, mode)

    for game in games:
        white = players_map.get(game["white"])
        black = players_map.get(game["black"])

        if not white or not black:
            continue

        if mode == "std":
            w_r, b_r = white.rating_std, black.rating_std
        elif mode == "rapid":
            w_r, b_r = white.rating_rapid, black.rating_rapid
        else:
            w_r, b_r = white.rating_blitz, black.rating_blitz

        if game["result"] == "1-0":
            s_w, s_b = 1.0, 0.0
        elif game["result"] == "0-1":
            s_w, s_b = 0.0, 1.0
        else:
            s_w, s_b = 0.5, 0.5

        exp_w = expected(w_r, b_r)
        exp_b = expected(b_r, w_r)

        if mode == "std":
            white.rating_std = update_rating(white.rating_std, s_w, exp_w)
            black.rating_std = update_rating(black.rating_std, s_b, exp_b)
        elif mode == "rapid":
            white.rating_rapid = update_rating(white.rating_rapid, s_w, exp_w)
            black.rating_rapid = update_rating(black.rating_rapid, s_b, exp_b)
        elif mode == "blitz":
            white.rating_blitz = update_rating(white.rating_blitz, s_w, exp_w)
            black.rating_blitz = update_rating(black.rating_blitz, s_b, exp_b)

        db.flush()

    db.commit()

    # Retorno rico em informações e amigável
    return {
        "status": "success",
        "message": f"Torneio de ritmo '{mode_pt}' importado com sucesso!",
        "detalhes": {
            "total_jogadores_identificados": len(players_names),
            "novos_jogadores_cadastrados": new_players_count,
            "total_partidas_processadas": len(games)
        }
    }
    # -------------------------
    # EXTRAÇÃO DE DADOS do HTML
    # -------------------------
    players_names = extract_players(url)
    games = extract_games(url)
    
    # Garante a ordem cronológica por rodadas
    games = sorted(games, key=lambda g: g["round"])

    # -------------------------
    # MAPEAMENTO DOS ENXADRISTAS
    # -------------------------
    players_map = {}

    for name in players_names:
        player = db.query(models.Player).filter_by(name=name).first()

        # Se o enxadrista jogou mas não está na base da FPBX, cadastra com rating inicial base
        if not player:
            player = models.Player(
                name=name,
                cbx_id=None,
                rating_std=1800.0,
                rating_rapid=1800.0,
                rating_blitz=1800.0
            )
            db.add(player)
            db.commit()
            db.refresh(player)

        players_map[name] = player

    # -------------------------
    # PROCESSAMENTO DO MOTOR ELO
    # -------------------------
    soup = fetch_tournament(url)
    mode = detect_mode(soup)

    # Varre partida por partida aplicando as atualizações de forma cumulativa
    for game in games:
        white = players_map.get(game["white"])
        black = players_map.get(game["black"])

        if not white or not black:
            continue

        # 1. Captura o rating atual correto dependendo da modalidade ativa do torneio
        if mode == "std":
            w_r, b_r = white.rating_std, black.rating_std
        elif mode == "rapid":
            w_r, b_r = white.rating_rapid, black.rating_rapid
        else:  # blitz
            w_r, b_r = white.rating_blitz, black.rating_blitz

        # 2. Converte o resultado textual do jogo para pontuação decimal do xadrez
        if game["result"] == "1-0":
            s_w, s_b = 1.0, 0.0
        elif game["result"] == "0-1":
            s_w, s_b = 0.0, 1.0
        else:
            s_w, s_b = 0.5, 0.5

        # 3. Executa as equações de probabilidade esperada do ELO
        exp_w = expected(w_r, b_r)
        exp_b = expected(b_r, w_r)

        # 4. Atualiza os ratings nos objetos (Ajustado para dentro do loop)
        if mode == "std":
            white.rating_std = update_rating(white.rating_std, s_w, exp_w)
            black.rating_std = update_rating(black.rating_std, s_b, exp_b)
        elif mode == "rapid":
            white.rating_rapid = update_rating(white.rating_rapid, s_w, exp_w)
            black.rating_rapid = update_rating(black.rating_rapid, s_b, exp_b)
        elif mode == "blitz":
            white.rating_blitz = update_rating(white.rating_blitz, s_w, exp_w)
            black.rating_blitz = update_rating(black.rating_blitz, s_b, exp_b)

        # Atualiza a sessão em memória para a próxima iteração usar os pontos novos
        db.flush()

    # Salva em definitivo as alterações cumulativas de todos os jogos no SQLite
    db.commit()

    return {
        "status": "success",
        "mode_detected": mode,
        "players": len(players_names),
        "games": len(games)
    }

@app.get("/export-ratings", tags=["Administração FPBX"], summary="Exportar planilha Excel/CSV com os ratings atualizados")
def export_ratings(db: Session = Depends(get_db)):
    # 1. Busca todos os jogadores ordenados por nome
    players = db.query(models.Player).order_by(models.Player.name).all()
    
    # 2. Cria um arquivo de texto temporário na memória RAM do servidor
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';') # Usamos ponto e vírgula para o Excel brasileiro abrir certinho
    
    # 3. Escreve o cabeçalho das colunas
    writer.writerow(["ID FPBX", "Nome do Enxadrista", "ID CBX", "Rating Standard", "Rating Rapido", "Rating Blitz"])
    
    # 4. Preenche as linhas com os dados do banco de dados
    for p in players:
        writer.writerow([
            p.id,
            p.name,
            p.cbx_id or "Não Informado",
            round(p.rating_std, 1) if p.rating_std else 1800.0,
            round(p.rating_rapid, 1) if p.rating_rapid else 1800.0,
            round(p.rating_blitz, 1) if p.rating_blitz else 1800.0
        ])
        
    # 5. Move o ponteiro para o início do arquivo na memória
    output.seek(0)
    
    # 6. Faz o FastAPI entregar isso como um arquivo de download para o seu navegador
    headers = {
        'Content-Disposition': 'attachment; filename="ranking_oficial_fpbx.csv"'
    }
    
    return StreamingResponse(
        io.StringIO(output.getvalue()), 
        media_type="text/csv", 
        headers=headers
    )
# -------------------------
# DEBUG
# -------------------------
@app.get("/debug-db")
def debug_db(db: Session = Depends(get_db)):
    players = db.query(models.Player).all()
    return {
        "count": len(players),
        "sample": [
            {"id": p.id, "name": p.name, "std": p.rating_std}
            for p in players[:5]
        ]
    }


# Configuração Global de CORS para permitir acesso seguro pelo frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)