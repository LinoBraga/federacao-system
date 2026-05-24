import pandas as pd
from sqlalchemy import create_engine, inspect

DATABASE_URL = "postgresql://neondb_owner:npg_4vnuWGH6PNbo@ep-lingering-thunder-apxpp9te-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"
ARQUIVO_CSV = "fpbx_players.csv"

try:
    print("🔌 Conectando ao Banco de Dados do Neon...")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    colunas_no_banco = [col['name'] for col in inspector.get_columns('players')]
    
    print("\n🔄 Lendo o arquivo CSV da FPBX...")
    df_csv = pd.read_csv(ARQUIVO_CSV, sep=',')
    
    # Mapeamento manual para garantir que colunas certas vão para os lugares certos
    # Ajuste os nomes da esquerda se o seu CSV tiver nomes diferentes
    mapeamento_manual = {
        'Nome': 'nome',
        'Rating STD': 'rating_std',
        'Rating RPD': 'rating_rpd',
        'Rating Blitz': 'rating_blz'
    }

    mapeamento = {}
    for csv_col, db_col in mapeamento_manual.items():
        if csv_col in df_csv.columns and db_col in colunas_no_banco:
            mapeamento[csv_col] = db_col
    
    print(f"\n🧠 Mapeamento aplicado: {mapeamento}")

    print("🧹 Filtrando e renomeando colunas...")
    df = df_csv[list(mapeamento.keys())].copy()
    df = df.rename(columns=mapeamento)

    # Convertendo para float e substituindo erros/nulos por 0.0
    for col in ['rating_std', 'rating_rpd', 'rating_blz']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)

    print("🚀 Descarregando enxadristas no Neon...")
    df.to_sql("players", con=engine, if_exists='append', index=False)

    print(f"✅ Sucesso! {len(df)} enxadristas importados.")

except Exception as e:
    print(f"❌ Erro durante a importação: {e}")