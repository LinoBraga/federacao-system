from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
import models

from importer import extract_games, extract_players, normalize_name
from elo import expected, update_rating
from utils import normalize_name
from fastapi.middleware.cors import CORSMiddleware
from fpbx_import import import_official_list


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Federação FPBX")


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

    # padrões reais de Chess-Results
    if "blitz" in text or "b l i t z" in text:
        return "blitz"

    if "rapid" in text or "rpd" in text:
        return "rapid"

    if "standard" in text or "std" in text:
        return "std"

    # fallback seguro
    return "std"
@app.get("/ranking/{mode}")
def ranking(mode: str, db: Session = Depends(get_db)):

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
def ranking(db: Session = Depends(get_db)):

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
# IMPORT TORNEIO (FPBX ENGINE)
# -------------------------
@app.post("/import-tournament")
def import_tournament(url: str, db: Session = Depends(get_db)):

    # evita duplicar torneio
    existing = db.query(models.Tournament).filter_by(url=url).first()
    if existing:
        return {"status": "already_processed"}

    tournament = models.Tournament(url=url)
    db.add(tournament)
    db.commit()

    # -------------------------
    # EXTRAÇÃO
    # -------------------------
    
    players_names = extract_players(url)
    games = extract_games(url)
    # ordena por rodada
    games = sorted(games, key=lambda g: g["round"])

    # -------------------------
    # MAPA DE JOGADORES
    # -------------------------
    players_map = {}

    for name in players_names:

        player = db.query(models.Player).filter_by(name=name).first()

        if not player:
            player = models.Player(
                name=name,
                name_norm=normalize_name(name),
                rating_fpbx=1800,
                rating_std=1800,
                rating_rapid=1800,
                rating_blitz=1800
            )
            db.add(player)
            db.commit()
            db.refresh(player)

        players_map[name] = player

    # -------------------------
    # MOTOR FPBX (ESSENCIAL)
    # -------------------------
    soup = fetch_tournament(url)
    mode = detect_mode(soup)
    for game in games:

        white = players_map.get(game["white"])
        black = players_map.get(game["black"])

        if not white or not black:
            continue

        # rating atual FPBX
        w_r = white.rating_fpbx
        b_r = black.rating_fpbx

        # resultado
        if game["result"] == "1-0":
            s_w, s_b = 1, 0
        elif game["result"] == "0-1":
            s_w, s_b = 0, 1
        else:
            s_w, s_b = 0.5, 0.5

        # expectativa
        exp_w = expected(w_r, b_r)
        exp_b = expected(b_r, w_r)

        # atualização Elo FPBX
    if mode == "std":
        white.rating_std = update_rating(white.rating_std, s_w, exp_w)
        black.rating_std = update_rating(black.rating_std, s_b, exp_b)

    elif mode == "rapid":
        white.rating_rapid = update_rating(white.rating_rapid, s_w, exp_w)
        black.rating_rapid = update_rating(black.rating_rapid, s_b, exp_b)

    elif mode == "blitz":
        white.rating_blitz = update_rating(white.rating_blitz, s_w, exp_w)
        black.rating_blitz = update_rating(black.rating_blitz, s_b, exp_b)

    db.commit()

    return {
        "status": "success",
        "players": len(players_names),
        "games": len(games)
    }


# -------------------------
# DEBUG
# -------------------------
@app.get("/debug-db")
def debug_db(db: Session = Depends(get_db)):

    players = db.query(models.Player).all()

    return {
        "count": len(players),
        "sample": [
            {"id": p.id, "name": p.name}
            for p in players[:5]
        ]
    }
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)