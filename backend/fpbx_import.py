import pandas as pd
from sqlalchemy import create_engine, inspect

# 1. Sua URL do Neon
DATABASE_URL = "postgresql://neondb_owner:npg_4vnuWGH6PNbo@ep-lingering-thunder-apxpp9te-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"
ARQUIVO_CSV = "fpbx_players.csv"

try:
    print("🔌 Conectando ao Banco de Dados do Neon para inspecionar a tabela...")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Pega as colunas reais que existem na tabela 'players'
    colunas_no_banco = [col['name'] for col in inspector.get_columns('players')]
    print(f"📋 Colunas encontradas na tabela 'players' do seu Neon: {colunas_no_banco}")

    print("\n🔄 Lendo o arquivo CSV da FPBX...")
    df_csv = pd.read_csv(ARQUIVO_CSV, sep=',')
    print(f"📋 Colunas originais do CSV: {list(df_csv.columns)}")

    # Regras inteligentes de mapeamento automático baseadas no que costuma mudar
    mapeamento = {}
    
    # 1. Tratamento do Nome
    if 'nome' in colunas_no_banco: mapeamento['Nome'] = 'nome'
    elif 'name' in colunas_no_banco: mapeamento['Nome'] = 'name'
    
    # 2. Tratamento do Município
    if 'municipio' in colunas_no_banco: mapeamento['MUNICÍPIO'] = 'municipio'
    elif 'city' in colunas_no_banco: mapeamento['MUNICÍPIO'] = 'city'
    elif 'location' in colunas_no_banco: mapeamento['MUNICÍPIO'] = 'location'

    # 3. Tratamento dos Ratings
    for csv_col, db_options in [
        ('Rating STD', ['rating_std', 'rating_standard', 'std_rating']),
        ('Rating RPD', ['rating_rapid', 'rating_rpd', 'rating_rapido', 'rapid_rating']),
        ('Rating Blitz', ['rating_blitz', 'blitz_rating'])
    ]:
        for opt in db_options:
            if opt in colunas_no_banco:
                mapeamento[csv_col] = opt
                break

    # 4. Tratamento da Última Movimentação
    for opt in ['ultima_movimentacao', 'last_move', 'updated_at']:
        if opt in colunas_no_banco:
            mapeamento['Última movimentação'] = opt
            break

    print(f"\n🧠 Mapeamento gerado dinamicamente: {mapeamento}")

    print("🧹 Filtrando e renomeando colunas...")
    # Mantém apenas o que conseguimos mapear que existe no banco
    df = df_csv[list(mapeamento.keys())].copy()
    df = df.rename(columns=mapeamento)

    # Identifica quais colunas de rating restaram no DataFrame final para converter em float
    colunas_std = [v for k, v in mapeamento.items() if 'std' in v or 'standard' in v]
    colunas_rpd = [v for k, v in mapeamento.items() if 'rapid' in v or 'rpd' in v or 'rapido' in v]
    colunas_blz = [v for k, v in mapeamento.items() if 'blitz' in v]

    for col in colunas_std + colunas_rpd + colunas_blz:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(1800.0).astype(float)

    print("🚀 Descarregando enxadristas no Neon...")
    df.to_sql("players", con=engine, if_exists='append', index=False)

    print(f"✅ Sucesso absoluto! {len(df)} enxadristas foram importados para o Neon.")

except Exception as e:
    print(f"❌ Erro durante a importação: {e}")