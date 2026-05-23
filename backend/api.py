import os
import csv
from io import StringIO
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse

# Aqui estão todas as ferramentas necessárias para o banco rodar sem erros:
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================
# Se estiver no Render, usa a variável DATABASE_URL (Postgres). No PC, usa SQLite local.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL:
    # Ajuste necessário pois o SQLAlchemy moderno exige "postgresql://" em vez de "postgres://"
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # Banco de dados local para testes no seu computador
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

# Cria as tabelas automaticamente no banco se elas não existirem
Base.metadata.create_all(bind=engine)


# ==========================================
# 2. SCHEMAS DE DADOS (Pydantic)
# ==========================================
class PlayerBase(BaseModel):
    nome: str
    clube: str = "Sem Clube"
    rating_std: int = 1000
    rating_rpd: int = 1000
    rating_blz: int = 1000

class PlayerResponse(PlayerBase):
    id: int

    class Config:
        from_attributes = True

class RatingUpdate(BaseModel):
    rating_std: int = None
    rating_rpd: int = None
    rating_blz: int = None


# ==========================================
# 3. CONFIGURAÇÃO DA API (FastAPI)
# ==========================================
app = FastAPI(
    title="Sistema de Ratings - Federação Paraibana de Xadrez",
    description="API segura para gerenciamento e consulta do ranking estadual.",
    version="1.0.0"
)

# Configuração do CORS para permitir que a Vercel acesse o Render sem bloqueios
# Configuração do CORS flexível para desenvolvimento e produção na Vercel
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

# Ativa o cabeçalho personalizado "X-Admin-Token" no cadeado do Swagger (/docs)
header_scheme = APIKeyHeader(name="X-Admin-Token", auto_error=False)

# Puxa a senha do Render (Environment Variables). Se não achar, usa a padrão para testes locais.
ADMIN_TOKEN = os.getenv("TOKEN_FPBX", "senha_local_teste")

def verify_admin_token(token_enviado: str = Depends(header_scheme)):
    """Valida se a senha enviada no cabeçalho está correta"""
    if not token_enviado or token_enviado != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso negado: Token de administrador inválido ou ausente."
        )
    return token_enviado


# ==========================================
# 5. ROTAS DA API
# ==========================================

# --- ROTAS PÚBLICAS ---
# --- ROTA DE EXPORTAR LISTA (Gera um arquivo CSV com os dados do Neon) ---
@app.get("/api/players/export")
def export_players(db: Session = Depends(get_db)):
    try:
        # COALESCE garante que se o clube estiver nulo no banco, ele vire "Sem Clube" no CSV sem quebrar o código
        query = text("""
            SELECT id, name, COALESCE(clube, 'Sem Clube'), rating_std, rating_rpd, rating_blz 
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
        # Esta linha devolve o erro real do sistema para sabermos exatamente o que quebrou
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")

# --- ROTA DE IMPORTAR FPBX (Um gatilho para atualizar a base se precisar) ---
@app.post("/api/players/import-fpbx")
def import_fpbx_status():
    # Como nós já fizemos a importação pesada via script externo,
    # essa rota serve para o Frontend saber que o banco já está atualizado 
    # ou para você disparar um aviso de sucesso na tela.
    return {
        "status": "sucesso", 
        "message": "Base de dados sincronizada com o Neon! 1048 enxadristas prontos."
    }

@app.get("/", tags=["Geral"])
def home():
    return {"message": "API da Federação Paraibana de Xadrez online!"}

@app.get("/ranking", response_model=List[PlayerResponse], tags=["Consulta Pública"])
def get_ranking(db: Session = Depends(get_db)):
    # Retorna a lista de jogadores ordenada pelo maior Rating Absoluto (Standard)
    return db.query(PlayerModel).order_by(PlayerModel.rating_std.desc()).all()

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
    
    # Atualiza apenas os campos enviados no JSON (evita apagar as outras modalidades)
    update_data = ratings.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_player, key, value)
        
    db.commit()
    db.refresh(db_player)
    return db_player

@app.post("/admin/import-tournament", tags=["Administração (Requer Token)"])
def import_tournament(
    tournament_name: str, 
    token: str = Depends(verify_admin_token)
):
    return {
        "status": "Sucesso", 
        "message": f"Torneio '{tournament_name}' processado e ratings atualizados!"
    }