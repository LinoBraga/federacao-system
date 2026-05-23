import csv
from models import Player
from database import SessionLocal  # Importa a conexão do seu próprio projeto
from fpbx_import import import_official_list

def executar():
    print("Conectando ao banco de dados do Neon e iniciando importação...")
    
    # Abre a conexão com o banco (que já está usando a URL do Neon configurada no seu projeto)
    db = SessionLocal()
    
    try:
        # Altere "fpbx_players.csv" para o nome exato do seu arquivo com a extensão (.csv)
        total = import_official_list(db, "fpbx_players.csv") 
        print(f"Sucesso! {total} jogadores foram importados/atualizados no banco do Neon.")
    except Exception as e:
        print(f"Ocorreu um erro durante a importação: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    executar()
def import_official_list(db, filepath: str):

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        count = 0

        for row in reader:

            cbx_id = row["cbx_id"]

            player = db.query(Player).filter_by(cbx_id=cbx_id).first()

            rating_std = int(row["Rating STD"] or 1800)
            rating_rapid = int(row["Rating RPD"] or 1800)
            rating_blitz = int(row["Rating Blitz"] or 1800)

            if player:
                player.name = row["Nome"]
                player.rating_std = rating_std
                player.rating_rapid = rating_rapid
                player.rating_blitz = rating_blitz

            else:
                player = Player(
                    cbx_id=cbx_id,
                    name=row["Nome"],
                    rating_std=rating_std,
                    rating_rapid=rating_rapid,
                    rating_blitz=rating_blitz,
                )
                db.add(player)

            count += 1

    db.commit()
    return count