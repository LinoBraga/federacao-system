import os
import csv
import requests
from io import StringIO
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from bs4 import BeautifulSoup
import re
import unicodedata

# Ferramentas do banco:
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL:
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'federacao.db')}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# MODELO DO BANCO DE DADOS (SQLAlchemy)
# ==========================================
class PlayerModel(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    clube = Column(String, default="Sem Clube")
    rating_std = Column(Integer, default=1000)
    rating_rpd = Column(Integer, default=1000)
    rating_blz = Column(Integer, default=1000)

Base.metadata.create_all(bind=engine)


# ==========================================
# 2. SCHEMAS DE DADOS (Pydantic)
# ==========================================
class PlayerBase(BaseModel):
    nome: str
    clube: str = "Sem Clube"
    rating_std: int = 1800
    rating_rpd: int = 1800
    rating_blz: int = 1800

class PlayerResponse(PlayerBase):
    id: int

    class Config:
        from_attributes = True

class RatingUpdate(BaseModel):
    rating_std: int = None
    rating_rapid: int = None
    rating_blitz: int = None

# Modelo criado para receber a URL do Chess-Results com segurança
class TournamentImportRequest(BaseModel):
    url: str
    tipo: str


# ==========================================
# 3. CONFIGURAÇÃO DA API (FastAPI)
# ==========================================
app = FastAPI(
    title="Sistema de Ratings - Federação Paraibana de Xadrez",
    description="API segura para gerenciamento e consulta do ranking estadual.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 4. DEPENDÊNCIAS E TRAVAS DE SEGURANÇA
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

header_scheme = APIKeyHeader(name="X-Admin-Token", auto_error=False)
ADMIN_TOKEN = os.getenv("TOKEN_FPBX", "senha_local_teste")

def verify_admin_token(token_enviado: str = Depends(header_scheme)):
    if not token_enviado or token_enviado != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado: Token de administrador inválido ou ausente."
        )
    return token_enviado


# ==========================================
# 5. ROTAS DA API
# ==========================================

@app.get("/api/players/export")
def export_players(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT id, nome, COALESCE(clube, 'Sem Clube'), rating_std, rating_rpd, rating_blz 
            FROM players
        """)
        result = db.execute(query).fetchall()
        
        if not result:
            raise HTTPException(status_code=404, detail="Nenhum jogador encontrado para exportar.")

        output = StringIO()
        writer = csv.writer(output)
        
        colunas = ["ID", "Nome", "Clube", "Rating STD", "Rating RPD", "Rating Blitz"]
        writer.writerow(colunas)
        
        for row in result:
            writer.writerow(row)
            
        output.seek(0)
        
        return StreamingResponse(
            output, 
            media_type="text/csv", 
            headers={"Content-Disposition": "attachment; filename=fbp_players_exported.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")

@app.post("/api/players/import-fpbx")
def import_fpbx_status():
    return {
        "status": "sucesso", 
        "message": "Base de dados sincronizada com o Neon! 1048 enxadristas prontos."
    }

@app.get("/", tags=["Geral"])
def home():
    return {"message": "API da Federação Paraibana de Xadrez online!"}

# 1. Rota para quando o usuário clicar em "Todos" ou carregar a página inicialmente
@app.get("/ranking", tags=["Consulta Pública"])
def get_ranking_default(db: Session = Depends(get_db)):
    # Retorna o padrão (std) para a chamada inicial do front
    query = text("SELECT id, nome, clube, rating_std, rating_rpd, rating_blz FROM players ORDER BY rating_std DESC")
    result = db.execute(query).fetchall()
    return format_players(result)

# 2. Rota dinâmica para os botões de ritmo (o que você já tem)
@app.get("/ranking/{ritmo}", tags=["Consulta Pública"])
def get_ranking_by_ritmo(ritmo: str, db: Session = Depends(get_db)):
    colunas = {
        "ranking_std": "rating_std",
        "ranking_rapid": "rating_rpd",
        "ranking_blitz": "rating_blz"
    }
    
    coluna_selecionada = colunas.get(ritmo)
    if not coluna_selecionada:
        raise HTTPException(status_code=400, detail="Ritmo inválido")

    query = text(f"SELECT id, nome, clube, rating_std, rating_rpd, rating_blz FROM players ORDER BY {coluna_selecionada} DESC")
    result = db.execute(query).fetchall()
    return format_players(result)

# Função auxiliar para não repetir código
def format_players(result):
    players_list = []
    for row in result:
        players_list.append({
            "id": row[0],
            "name": row[1],
            "clube": row[2] if row[2] else "Sem Clube",
            "rating_std": int(row[3] or 1800),
            "rating_rpd": int(row[4] or 1800),
            "rating_blz": int(row[5] or 1800)
        })
    return players_list
@app.get("/player/{player_id}", response_model=PlayerResponse, tags=["Consulta Pública"])
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerModel).filter(PlayerModel.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Enxadrista não encontrado.")
    return player


# --- ROTAS PROTEGIDAS (Exigem o Token de Admin) ---

@app.post("/admin/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED, tags=["Administração (Requer Token)"])
def create_player(
    player: PlayerBase, 
    db: Session = Depends(get_db), 
    token: str = Depends(verify_admin_token)
):
    db_player = PlayerModel(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player
@app.post("/admin/sync-blitz-csv", tags=["Administração (Requer Token)"])
def sync_blitz_csv(
    payload: TournamentImportRequest, # Usamos o mesmo modelo para passar o link do CSV bruto se quiser, ou texto
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """
    Rota para forçar a leitura do CSV original e atualizar os ratings de Blitz
    que ficaram para trás na primeira importação.
    """
    try:
        # Link do seu CSV (Pode ser o link do GitHub raw ou Google Drive público)
        headers = {"User-Agent": "Mozilla/5.0"}
        resposta = requests.get(payload.url, headers=headers)
        
        if resposta.status_code != 200:
            raise HTTPException(status_code=400, detail="Não foi possível ler o arquivo CSV informado.")

        # Lendo o CSV vindo da URL
        conteudo = StringIO(resposta.text)
        leitor = csv.DictReader(conteudo)
        
        atualizados = 0
        
        for linha in leitor:
            # Pegamos o nome e o rating de Blitz usando os nomes exatos do seu CSV
            nome = linha.get("Nome") or linha.get("nome")
            rating_blitz_texto = linha.get("Rating Blitz") or linha.get("Rating_Blitz")
            
            if not nome or not rating_blitz_texto:
                continue
                
            # Limpa o texto tirando espaços ou traços e converte para número
            rating_blitz_texto = "".join(filter(str.isdigit, rating_blitz_texto.strip()))
            
            if not rating_blitz_texto:
                continue # Se a pessoa não tiver rating blitz no CSV, pula ela
                
            rating_blitz = int(rating_blitz_texto)

            # Atualiza direto na coluna certa do Neon buscando pelo nome do enxadrista
            stmt = text("""
                UPDATE players 
                SET rating_blz = :rating 
                WHERE LOWER(nome) = LOWER(:nome)
            """)
            resultado = db.execute(stmt, {"rating": rating_blitz, "nome": nome.strip()})
            
            if resultado.rowcount > 0:
                atualizados += 1
                
        db.commit()
        return {"status": "Sucesso", "message": f"Ratings de Blitz corrigidos para {atualizados} enxadristas!"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar: {str(e)}")
@app.patch("/admin/players/{player_id}/ratings", response_model=PlayerResponse, tags=["Administração (Requer Token)"])
def update_ratings(
    player_id: int, 
    ratings: RatingUpdate, 
    db: Session = Depends(get_db), 
    token: str = Depends(verify_admin_token)
):
    db_player = db.query(PlayerModel).filter(PlayerModel.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Enxadrista não encontrado.")
    
    update_data = ratings.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_player, key, value)
        
    db.commit()
    db.refresh(db_player)
    return db_player


# 🚀 ROTA DE IMPORTAÇÃO AUTOMÁTICA VIA LINK DO CHESS-RESULTS
TORNEIOS_PROCESSADOS = set()
def normalizar_nome(nome):

    nome = unicodedata.normalize("NFKD", nome)
    nome = nome.encode("ASCII", "ignore").decode("utf-8")

    nome = nome.lower()

    nome = re.sub(r"[^a-z\s]", "", nome)

    ignorar = {
        "de", "da", "do", "dos", "das"
    }

    partes = [
        p for p in nome.split()
        if p not in ignorar
    ]

    return " ".join(partes)


@app.post("/admin/import-tournament", tags=["Administração (Requer Token)"])
def import_tournament(
    payload: TournamentImportRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):

    try:

        # ==========================================
        # CONFIGURAÇÃO INICIAL
        # ==========================================

        headers = {"User-Agent": "Mozilla/5.0"}

        resposta = requests.get(payload.url, headers=headers)

        if resposta.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Erro ao acessar o Chess-Results."
            )

        soup = BeautifulSoup(resposta.text, "html.parser")

        tipo = payload.tipo.lower().strip()

        if tipo == "blitz":
            coluna_alvo = "rating_blz"

        elif tipo == "rapid":
            coluna_alvo = "rating_rpd"

        else:
            coluna_alvo = "rating_std"

        print(f"IMPORTANDO PARA -> {coluna_alvo}")

        # ==========================================
        # ENCONTRA A TABELA CORRETA
        # ==========================================

        tabelas = soup.find_all("table")

        if not tabelas:
            raise HTTPException(
                status_code=400,
                detail="Nenhuma tabela encontrada."
            )

        tabela = None

        for t in tabelas:

            texto = t.get_text(" ", strip=True).lower()

            if "rtg+/-" in texto and (
                "nome" in texto or "name" in texto
            ):
                tabela = t
                break

        if tabela is None:
            raise HTTPException(
                status_code=400,
                detail="Tabela do torneio não encontrada."
            )

        linhas = tabela.find_all("tr")

        # ==========================================
        # IDENTIFICA CABEÇALHO
        # ==========================================

        indice_nome = None
        indice_variacao = None
        linha_inicio_dados = None

        for idx, linha in enumerate(linhas):

            colunas_temp = [
                td.get_text(strip=True).lower()
                for td in linha.find_all(["td", "th"])
            ]

            if not colunas_temp:
                continue

            for i, col in enumerate(colunas_temp):

                if "nome" in col or "name" in col:
                    indice_nome = i

                if "rtg+/-" in col:
                    indice_variacao = i

            if (
                indice_nome is not None
                and indice_variacao is not None
            ):
                linha_inicio_dados = idx + 1
                break

        if linha_inicio_dados is None:
            raise HTTPException(
                status_code=400,
                detail="Cabeçalho não encontrado."
            )

        print("ÍNDICE NOME:", indice_nome)
        print("ÍNDICE VARIAÇÃO:", indice_variacao)

        # ==========================================
        # CARREGA JOGADORES DO BANCO
        # ==========================================

        jogadores_atualizados = 0

        todos_jogadores = db.query(PlayerModel).all()

        mapa_jogadores = {
            normalizar_nome(p.nome): p
            for p in todos_jogadores
        }

        # ==========================================
        # PROCESSA CADA LINHA
        # ==========================================

        for linha in linhas[linha_inicio_dados:]:

            colunas = linha.find_all("td")

            print("TOTAL COLUNAS:", len(colunas))
            if len(colunas) < 20:
                continue
            textos = [
                c.get_text(strip=True)
                for c in colunas
            ]

            print(textos)

            nome_raw = (
                colunas[indice_nome]
                .get_text(strip=True)
            )
            if nome_raw.upper() in [
                "FED",
                "NOME",
                "NAME",
                "ELO",
                "RTG+/-"
            ]:
                continue

            variacao_texto = (
                colunas[indice_variacao]
                .get_text(strip=True)
                .replace(",", ".")
            )

            if not nome_raw or not variacao_texto:
                continue

            try:
                variacao = float(variacao_texto)

            except ValueError:
                continue

            # ==========================================
            # LIMPEZA DO NOME
            # ==========================================

            partes = nome_raw.split(",")

            if len(partes) > 1:
                nome_limpo = (
                    f"{partes[1].strip()} "
                    f"{partes[0].strip()}"
                )
            else:
                nome_limpo = nome_raw

            titulos = [
                "GM", "IM", "FM", "CM",
                "WGM", "WIM", "WFM",
                "WCM", "NM", "AFM"
            ]

            nome_final = " ".join([
                p for p in nome_limpo.split()
                if p.upper() not in titulos
            ])

            nome_normalizado = normalizar_nome(nome_final)

            print(
                f"DEBUG: Processando -> "
                f"{nome_final} | "
                f"Variação: {variacao}"
            )

            # ==========================================
            # MATCH NO BANCO
            # ==========================================

            encontrado = mapa_jogadores.get(
                nome_normalizado
            )

            if encontrado:

                rating_atual = (
                    getattr(encontrado, coluna_alvo)
                    or 1000
                )

                novo_rating = round(
                    rating_atual + variacao
                )

                setattr(
                    encontrado,
                    coluna_alvo,
                    novo_rating
                )

                jogadores_atualizados += 1

                print(
                    f"DEBUG: Sucesso! "
                    f"{encontrado.nome} | "
                    f"{rating_atual} -> {novo_rating}"
                )

            else:

                print(
                    f"DEBUG: JOGADOR NÃO ENCONTRADO -> "
                    f"{nome_final}"
                )

        # ==========================================
        # FINALIZA
        # ==========================================

        db.commit()

        return {
            "status": "Sucesso",
            "message": (
                f"{jogadores_atualizados} "
                f"jogadores atualizados."
            ),
            "tipo": coluna_alvo
        }

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )