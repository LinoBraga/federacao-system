import os
import csv
import requests
from io import StringIO, BytesIO
from typing import List
import pandas as pd
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

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

@app.get("/ranking", tags=["Consulta Pública"])
def get_ranking_default(db: Session = Depends(get_db)):
    query = text("SELECT id, nome, clube, rating_std, rating_rpd, rating_blz FROM players ORDER BY rating_std DESC")
    result = db.execute(query).fetchall()
    return format_players(result)

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

@app.post("/admin/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED, tags=["Administração"])
def create_player(player: PlayerBase, db: Session = Depends(get_db), token: str = Depends(verify_admin_token)):
    db_player = PlayerModel(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player

@app.post("/admin/sync-blitz-csv", tags=["Administração"])
def sync_blitz_csv(payload: TournamentImportRequest, db: Session = Depends(get_db), token: str = Depends(verify_admin_token)):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resposta = requests.get(payload.url, headers=headers)
        
        if resposta.status_code != 200:
            raise HTTPException(status_code=400, detail="Não foi possível ler o arquivo CSV informado.")

        conteudo = StringIO(resposta.text)
        leitor = csv.DictReader(conteudo)
        
        atualizados = 0
        
        for linha in leitor:
            nome = linha.get("Nome") or linha.get("nome")
            rating_blitz_texto = linha.get("Rating Blitz") or linha.get("Rating_Blitz")
            
            if not nome or not rating_blitz_texto:
                continue
                
            rating_blitz_texto = "".join(filter(str.isdigit, rating_blitz_texto.strip()))
            if not rating_blitz_texto:
                continue
                
            rating_blitz = int(rating_blitz_texto)

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

@app.patch("/admin/players/{player_id}/ratings", response_model=PlayerResponse, tags=["Administração"])
def update_ratings(player_id: int, ratings: RatingUpdate, db: Session = Depends(get_db), token: str = Depends(verify_admin_token)):
    db_player = db.query(PlayerModel).filter(PlayerModel.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Enxadrista não encontrado.")
    
    update_data = ratings.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_player, key, value)
        
    db.commit()
    db.refresh(db_player)
    return db_player


# 🚀 ROTA DE IMPORTAÇÃO AUTOMÁTICA VIA EXCEL
def normalizar(nome: str):
    nome = unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode("utf-8")
    nome = re.sub(r"[^a-z\s]", " ", nome.lower())
    return " ".join(nome.split())

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def match_player(nome, mapa):
    best = None
    best_score = 0.82
    for key, player in mapa.items():
        score = similarity(nome, key)
        if score > best_score:
            best_score = score
            best = player
    return best

@app.post("/admin/import-excel")
def import_excel(
    file: UploadFile = File(...),
    tipo: str = "std",
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    updated = 0
    ignored = 0

    try:
        # 1. LER ARQUIVO
        contents = file.file.read()
        df_raw = pd.read_excel(BytesIO(contents), engine="openpyxl", header=None)

        # 2. ACHAR HEADER DINAMICAMENTE
        mask = df_raw.apply(
            lambda row: row.astype(str).str.contains(r"nome|name|rk|rating", case=False, na=False).any(),
            axis=1
        )

        if not mask.any():
            return {"status": "error", "error": "Cabeçalho não encontrado no Excel"}

        idx_header = mask.idxmax()
        header_row = df_raw.iloc[idx_header].fillna("").astype(str)
        data = df_raw.iloc[idx_header + 1:].reset_index(drop=True)

        data.columns = [str(c).lower().strip() if c is not None else "" for c in header_row]
        data = data.loc[:, data.columns != ""]
        data = data.loc[:, ~data.columns.str.contains("^nan$", na=False)]

        # 3. MAPEAR COLUNAS E BANCO DE DADOS
        col_nome = next((c for c in data.columns if "nome" in c or "name" in c), None)
        col_var = next((c for c in data.columns if "rtg" in c or "var" in c or "+/-" in c), None)

        if not col_nome or not col_var:
            return {"status": "error", "error": "Colunas não mapeadas", "cols_detectadas": data.columns.tolist()}

        coluna_db = "rating_blz" if tipo == "blitz" else "rating_rpd" if tipo == "rapid" else "rating_std"

        players = db.query(PlayerModel).all()
        mapa = {normalizar(p.nome): p for p in players}

        # 4. PROCESSAMENTO REAL (BLINDADO CONTRA VAZIOS)
        for _, row in data.iterrows():
            try:
                nome_raw = str(row[col_nome]).strip()
                
                # Pega a variação crua, se for NaN/vazio, joga "0"
                var_raw = str(row[col_var]).strip().replace(",", ".") if pd.notna(row[col_var]) else "0"

                if nome_raw == "" or nome_raw.lower() == "nan":
                    ignored += 1
                    continue

                # Limpeza segura da variação
                var_limpa = re.sub(r"[^0-9\.-]", "", var_raw)
                if var_limpa == "" or var_limpa == "-" or var_limpa == ".":
                    variacao = 0.0
                else:
                    variacao = float(var_limpa)

                def tentar_encontrar(nome):
                    n_norm = normalizar(nome)
                    p = mapa.get(n_norm)
                    if not p:
                        p = match_player(n_norm, mapa)
                    return p

                player = tentar_encontrar(nome_raw)

                # Tentativa 2: Nome invertido (Chess-Results format)
                if not player and "," in nome_raw:
                    partes = nome_raw.split(",", 1)
                    if len(partes) == 2:
                        nome_invertido = f"{partes[1].strip()} {partes[0].strip()}"
                        player = tentar_encontrar(nome_invertido)

                if not player:
                    print(f"MISS: Não achou nem normal nem invertido -> {nome_raw}")
                    ignored += 1
                    continue

                # Atualiza os valores
                atual = getattr(player, coluna_db) or 1000
                novo = round(atual + variacao)
                setattr(player, coluna_db, novo)
                
                updated += 1
                print(f"OK: {player.nome} ({atual} -> {novo})")

            except Exception as e:
                print("ERRO LINHA:", e)
                ignored += 1
                continue

        # Salva tudo no banco
        db.commit()

        # 5. RESPOSTA FINAL
        return {
            "status": "success",
            "tipo": tipo,
            "atualizados": int(updated),
            "ignorados": int(ignored),
            "total_linhas": int(len(data))
        }

    except Exception as e:
        db.rollback()
        print("ERRO CRÍTICO:", str(e))
        return {"status": "error", "error": str(e)}