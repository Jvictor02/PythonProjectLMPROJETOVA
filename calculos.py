import pandas as pd
from conexao import conectar

def get_dados():
    conn = conectar()

    fat_detalhado = pd.read_sql("SELECT * FROM faturamento_mensal", conn)
    gastos_detalhado = pd.read_sql("SELECT * FROM gastos_mensais_detalhados", conn)
    gastos_consolidado = pd.read_sql("SELECT * FROM gastos_mensais_consolidados", conn)

    conn.close()

    # --- Limpeza: remove espaços extras e normaliza textos ---
    for df in (fat_detalhado, gastos_detalhado, gastos_consolidado):
        if 'mes_ano' in df.columns:
            df['mes_ano'] = df['mes_ano'].astype(str).str.strip()
        if 'mes_nome' in df.columns:
            df['mes_nome'] = df['mes_nome'].astype(str).str.strip()

    if 'unidade' in fat_detalhado.columns:
        fat_detalhado['unidade'] = fat_detalhado['unidade'].astype(str).str.strip().str.title()

    # --- Garantir tipos numéricos ---
    for df, cols in [(fat_detalhado, ['valor_bruto', 'valor_liquido']),
                     (gastos_consolidado, ['valor_total']),
                     (gastos_detalhado, ['valor'])]:
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # --- Faturamento por unidade ---
    def soma_unidade(nome):
        filtro = fat_detalhado[fat_detalhado['unidade'] == nome]
        return (filtro.groupby('mes_ano', as_index=False)['valor_liquido'].sum()
                .rename(columns={'valor_liquido': f'fat_liquido_{nome.lower()}'}))

    esmeralda = soma_unidade('Esmeralda')
    safira = soma_unidade('Safira')

    # Meses gravados como 'Consolidado' (sem unidade separada)
    consolidado = (fat_detalhado[fat_detalhado['unidade'] == 'Consolidado']
                   .groupby('mes_ano', as_index=False)['valor_liquido'].sum()
                   .rename(columns={'valor_liquido': 'fat_liquido_consolidado'}))

    gastos = (gastos_consolidado
              .groupby('mes_ano', as_index=False)['valor_total'].sum()
              .rename(columns={'valor_total': 'gastos_total'}))

    # --- Monta o resumo com TODOS os meses (outer join não perde nada) ---
    resumo = (esmeralda.merge(safira, on='mes_ano', how='outer')
                       .merge(consolidado, on='mes_ano', how='outer')
                       .merge(gastos, on='mes_ano', how='outer'))

    # Nomes dos meses
    nomes = pd.concat([fat_detalhado[['mes_ano', 'mes_nome']],
                       gastos_consolidado[['mes_ano', 'mes_nome']]])
    nomes = nomes.drop_duplicates(subset='mes_ano', keep='first')
    resumo = resumo.merge(nomes, on='mes_ano', how='left')

    # --- Métricas financeiras ---
    for c in ['fat_liquido_esmeralda', 'fat_liquido_safira',
              'fat_liquido_consolidado', 'gastos_total']:
        resumo[c] = resumo[c].fillna(0)

    # Faturamento geral: usa Esmeralda + Safira; se o mês só tem 'Consolidado', usa ele
    soma_unidades = resumo['fat_liquido_esmeralda'] + resumo['fat_liquido_safira']
    resumo['fat_liquido_geral'] = soma_unidades.where(
        soma_unidades > 0, resumo['fat_liquido_consolidado'])

    resumo['lucro_bruto'] = resumo['fat_liquido_geral'] - resumo['gastos_total']
    resumo['margem_liquida'] = (resumo['lucro_bruto'] / resumo['fat_liquido_geral'] * 100).fillna(0)

    resumo = resumo.sort_values('mes_ano').reset_index(drop=True)

    return resumo, fat_detalhado, gastos_detalhado