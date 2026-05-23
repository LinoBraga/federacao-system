import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader  # <-- IMPORTANTE: Mudamos aqui para ativar o cadeado
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.exists("/data"):
    SQLALCHEMY_DATABASE_URL = "sqlite:////data/federacao.db"
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'federacao.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 4. DEPENDÊNCIAS E TRAVAS DE SEGURANÇA (Cadeado Ativado)
# ==========================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Isso avisa o FastAPI para criar o botão de "Authorize" (cadeado) na interface de testes
header_scheme = APIKeyHeader(name="X-Admin-Token", auto_error=False)

ADMIN_TOKEN = os.getenv("TOKEN_FPBX", "senha_local_teste")

def verify_admin_token(token_enviado: str = Depends(header_scheme)):
    """Valida se a senha digitada no cadeado está correta"""
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

@app.get("/", tags=["Geral"])
def home():
    return {"message": "API da Federação Paraibana de Xadrez online!"}

@app.get("/ranking", response_model=List[PlayerResponse], tags=["Consulta Pública"])
def get_ranking(db: Session = Depends(get_db)):
    return db.query(PlayerModel).order_by(PlayerModel.rating_std.desc()).all()

@app.get("/player/{player_id}", response_model=PlayerResponse, tags=["Consulta Pública"])
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerModel).filter(PlayerModel.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Enxadrista não encontrado.")
    return player


# --- ROTAS PROTEGIDAS (Agora vinculadas ao cadeado do Swagger) ---

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