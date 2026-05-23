import requests
from bs4 import BeautifulSoup
import re


# -------------------------
# FETCH BASE
# -------------------------
def fetch_tournament(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


# -------------------------
# NORMALIZA NOME
# -------------------------
def normalize_name(name: str):
    return re.sub(r"\s+", " ", name.strip().lower())


# -------------------------
# PLAYERS
# -------------------------
def extract_players(url: str):
    soup = fetch_tournament(url)

    players = set()

    for row in soup.find_all("tr"):
        cols = row.find_all("td")

        if len(cols) >= 4:
            white = cols[1].get_text(strip=True)
            black = cols[3].get_text(strip=True)

            if white:
                players.add(white)
            if black:
                players.add(black)

    return list(players)


# -------------------------
# GAMES (COM RODADA)
# -------------------------

def extract_games(url: str):
    soup = fetch_tournament(url)

    games = []

    round_number = 1

    for row in soup.find_all("tr"):
        cols = row.find_all("td")

        if len(cols) >= 6:
            try:
                white = cols[1].get_text(strip=True)
                black = cols[3].get_text(strip=True)
                result = cols[5].get_text(strip=True)

                # ignora linhas inválidas
                if not white or not black:
                    continue

                # normaliza resultado
                if result in ["½-½", "0.5-0.5", "="]:
                    result = "0.5-0.5"

                if result in ["1-0", "0-1", "0.5-0.5"]:

                    games.append({
                        "round": round_number,
                        "white": white,
                        "black": black,
                        "result": result
                    })

            except:
                continue

    return games