import os
import re
import glob
import streamlit as st
import plotly.express as px
from calculos import get_dados
from conexao import conectar

st.set_page_config(page_title="Little Market — Dashboard Financeiro", layout="wide")

# ---------- Identidade visual Little Market ----------
AZUL_MARINHO = "#003048"
VERDE_ESMERALDA = "#189030"
VERMELHO_GASTOS = "#D64545"
CINZA_CONSOLIDADO = "#607890"

def fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def encontrar_logo():
    """Procura qualquer imagem na pasta assets"""
    for extensao in ["png", "jpg", "jpeg"]:
        arquivos = glob.glob(f"assets/*.{extensao}")
        if arquivos:
            return arquivos[0]
    return None

def nome_mes(linha):
    """Retorna o nome do mês; se estiver vazio, usa o código (ex: 2026-01)"""
    if isinstance(linha["mes_nome"], str) and linha["mes_nome"].strip():
        return linha["mes_nome"]
    return linha["mes_ano"]

# ---------- Cabeçalho com logo ----------
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    logo = encontrar_logo()
    if logo:
        st.image(logo, width=110)
with col_titulo:
    st.title("Little Market — Dashboard Financeiro")
    st.caption("Ferramenta analítica de apoio à decisão — Unidades Esmeralda e Safira")

resumo, fat_detalhado, gastos_detalhado = get_dados()

# ---------- Filtros (menu lateral) ----------
with st.sidebar:
    st.header("🔎 Filtros")

    meses_opcoes = sorted(resumo['mes_ano'].unique())
    meses_selecionados = st.multiselect(
        "Período (meses)",
        meses_opcoes,
        default=meses_opcoes
    )

    unidade_selecionada = st.selectbox(
        "Unidade",
        ["Todas as unidades", "Esmeralda", "Safira"]
    )

    st.caption("Projeto Integrador VA — Little Market")

# Se nada for selecionado, mostra todos os meses
if not meses_selecionados:
    meses_selecionados = list(meses_opcoes)

resumo_f = resumo[resumo['mes_ano'].isin(meses_selecionados)]

if 'mes_ano' in gastos_detalhado.columns:
    gastos_det_f = gastos_detalhado[gastos_detalhado['mes_ano'].isin(meses_selecionados)]
else:
    gastos_det_f = gastos_detalhado

# Define a coluna de faturamento conforme a unidade selecionada
if unidade_selecionada == "Todas as unidades":
    coluna_fat = 'fat_liquido_geral'
elif unidade_selecionada == 'Esmeralda':
    coluna_fat = 'fat_liquido_esmeralda'
else:
    coluna_fat = 'fat_liquido_safira'

# ---------- KPIs ----------
col1, col2, col3, col4 = st.columns(4)

if unidade_selecionada == "Todas as unidades":
    fat_periodo = resumo_f['fat_liquido_geral'].sum()
    gastos_periodo = resumo_f['gastos_total'].sum()
    lucro_periodo = resumo_f['lucro_bruto'].sum()
    margem_periodo = (lucro_periodo / fat_periodo * 100) if fat_periodo > 0 else 0

    col1.metric("💰 Faturamento Total", fmt_brl(fat_periodo))
    col2.metric("💸 Gastos Totais", fmt_brl(gastos_periodo))
    col3.metric("📈 Lucro Líquido", fmt_brl(lucro_periodo))
    col4.metric("📊 Margem Líquida", f"{margem_periodo:.1f}%".replace(".", ","))
else:
    fat_unidade = resumo_f[coluna_fat].sum()
    fat_total_geral = resumo_f['fat_liquido_geral'].sum()
    participacao = (fat_unidade / fat_total_geral * 100) if fat_total_geral > 0 else 0
    media_mensal = resumo_f[coluna_fat].mean() if len(resumo_f) > 0 else 0
    melhor_mes = "—"
    if len(resumo_f) > 0 and resumo_f[coluna_fat].sum() > 0:
        melhor_mes = nome_mes(resumo_f.loc[resumo_f[coluna_fat].idxmax()])

    col1.metric(f"💰 Faturamento {unidade_selecionada}", fmt_brl(fat_unidade))
    col2.metric("📊 Participação no Total", f"{participacao:.1f}%".replace(".", ","))
    col3.metric("📆 Média Mensal", fmt_brl(media_mensal))
    col4.metric("🏆 Melhor Mês", melhor_mes)

# ---------- Análise automática do período ----------
st.subheader("📌 Análise do período selecionado")

if not resumo_f.empty:
    melhor_faturamento = resumo_f.loc[resumo_f[coluna_fat].idxmax()]
    pior_faturamento = resumo_f.loc[resumo_f[coluna_fat].idxmin()]

    media_faturamento = resumo_f[coluna_fat].mean()

    resumo_ordenado = resumo_f.sort_values("mes_ano")
    primeiro_faturamento = resumo_ordenado.iloc[0][coluna_fat]
    ultimo_faturamento = resumo_ordenado.iloc[-1][coluna_fat]

    if primeiro_faturamento != 0:
        crescimento = ((ultimo_faturamento - primeiro_faturamento) / primeiro_faturamento) * 100
    else:
        crescimento = 0

    analise1, analise2, analise3, analise4 = st.columns(4)

    analise1.metric(
        "🏆 Melhor faturamento",
        nome_mes(melhor_faturamento),
        fmt_brl(melhor_faturamento[coluna_fat])
    )

    analise2.metric(
        "📉 Menor faturamento",
        nome_mes(pior_faturamento),
        fmt_brl(pior_faturamento[coluna_fat])
    )

    if unidade_selecionada == "Todas as unidades":
        melhor_lucro = resumo_f.loc[resumo_f["lucro_bruto"].idxmax()]
        analise3.metric(
            "💰 Melhor lucro",
            nome_mes(melhor_lucro),
            fmt_brl(melhor_lucro["lucro_bruto"])
        )
    else:
        analise3.metric(
            "📆 Média mensal da unidade",
            fmt_brl(media_faturamento)
        )

    analise4.metric(
        "📈 Variação do período",
        f"{crescimento:.1f}%".replace(".", ","),
        f"Média: {fmt_brl(media_faturamento)}"
    )
else:
    st.info("Não há dados para o período selecionado.")

# ---------- Gráfico 1: Faturamento por Unidade ----------
st.subheader("Faturamento por Unidade — Esmeralda vs Safira")
fig1 = px.bar(resumo_f, x='mes_ano',
              y=['fat_liquido_esmeralda', 'fat_liquido_safira', 'fat_liquido_consolidado'],
              barmode='group',
              labels={'value': 'R$', 'mes_ano': 'Mês', 'variable': 'Unidade'},
              color_discrete_map={
                  'fat_liquido_esmeralda': VERDE_ESMERALDA,
                  'fat_liquido_safira': AZUL_MARINHO,
                  'fat_liquido_consolidado': CINZA_CONSOLIDADO
              })
st.plotly_chart(fig1, use_container_width=True)

# ---------- Gráfico 2: Lucro ou Faturamento da unidade ----------
if unidade_selecionada == "Todas as unidades":
    st.subheader("Lucro Líquido por Mês")
    fig2 = px.line(resumo_f, x='mes_ano', y='lucro_bruto', markers=True,
                   labels={'lucro_bruto': 'Lucro (R$)', 'mes_ano': 'Mês'},
                   color_discrete_sequence=[VERDE_ESMERALDA])
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Faturamento vs Gastos por Mês")
    fig3 = px.bar(resumo_f, x='mes_ano',
                  y=['fat_liquido_geral', 'gastos_total'],
                  barmode='group',
                  labels={'value': 'R$', 'mes_ano': 'Mês', 'variable': 'Categoria'},
                  color_discrete_map={
                      'fat_liquido_geral': AZUL_MARINHO,
                      'gastos_total': VERMELHO_GASTOS
                  })
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Margem Líquida (%) por Mês")
    fig4 = px.bar(resumo_f, x='mes_ano', y='margem_liquida',
                  labels={'margem_liquida': 'Margem (%)', 'mes_ano': 'Mês'},
                  color_discrete_sequence=[AZUL_MARINHO])
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.subheader(f"Faturamento da Unidade {unidade_selecionada} por Mês")
    fig2 = px.line(resumo_f, x='mes_ano', y=coluna_fat, markers=True,
                   labels={coluna_fat: 'Faturamento (R$)', 'mes_ano': 'Mês'},
                   color_discrete_sequence=[VERDE_ESMERALDA if unidade_selecionada == 'Esmeralda' else AZUL_MARINHO])
    st.plotly_chart(fig2, use_container_width=True)

    st.info("ℹ️ Os gastos, o lucro e a margem são calculados de forma consolidada (Esmeralda + Safira), pois os gastos não são registrados separadamente por unidade.")

# ---------- Gastos por Categoria ----------
st.subheader("💸 Gastos por Categoria")

if not gastos_det_f.empty and "categoria" in gastos_det_f.columns:
    gastos_categoria = (
        gastos_det_f
        .groupby("categoria", as_index=False)["valor"]
        .sum()
        .sort_values("valor", ascending=False)
    )

    fig5 = px.bar(
        gastos_categoria,
        x="categoria",
        y="valor",
        text_auto=".2f",
        labels={
            "categoria": "Categoria",
            "valor": "Total de Gastos (R$)"
        },
        color_discrete_sequence=[VERMELHO_GASTOS]
    )

    fig5.update_layout(
        xaxis_title="Categoria",
        yaxis_title="Valor (R$)",
        xaxis_tickangle=-35
    )

    st.plotly_chart(fig5, use_container_width=True)

    st.dataframe(
        gastos_categoria.rename(columns={
            "categoria": "Categoria",
            "valor": "Total de Gastos"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Ainda não existem gastos detalhados cadastrados.")

# ---------- Tabela Resumo ----------
st.subheader("📋 Tabela Resumo")
st.dataframe(resumo_f[['mes_ano', 'mes_nome', 'fat_liquido_geral',
                      'fat_liquido_esmeralda', 'fat_liquido_safira',
                      'gastos_total', 'lucro_bruto', 'margem_liquida']].rename(columns={
    'mes_ano': 'Mês',
    'mes_nome': 'Nome',
    'fat_liquido_geral': 'Fat. Total',
    'fat_liquido_esmeralda': 'Esmeralda',
    'fat_liquido_safira': 'Safira',
    'gastos_total': 'Gastos',
    'lucro_bruto': 'Lucro',
    'margem_liquida': 'Margem %'
}), use_container_width=True)

# ---------- Formulário de inserção ----------
st.subheader("➕ Inserir Novo Mês")
with st.form("novo_mes"):
    mes_ano = st.text_input("Mês/Ano (ex: 2026-10)")
    mes_nome = st.text_input("Nome do Mês (ex: Outubro/2026)")
    fat_esmeralda = st.number_input("Faturamento Líquido Esmeralda (R$)", min_value=0.0)
    fat_safira = st.number_input("Faturamento Líquido Safira (R$)", min_value=0.0)
    gastos = st.number_input("Gastos Totais (R$)", min_value=0.0)
    salvar = st.form_submit_button("💾 Salvar")

    if salvar:
        if not re.fullmatch(r"\d{4}-\d{2}", mes_ano):
            st.error("Digite o mês no formato AAAA-MM. Exemplo: 2026-10.")
            st.stop()

        mes = int(mes_ano[5:7])
        if mes < 1 or mes > 12:
            st.error("O mês deve estar entre 01 e 12.")
            st.stop()

        ordem_mes = mes
        fat_total = fat_esmeralda + fat_safira
        lucro = fat_total - gastos

        conn = conectar()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO dim_mes (mes_ano, mes_nome, ordem_mes)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    mes_nome = VALUES(mes_nome),
                    ordem_mes = VALUES(ordem_mes)
                """,
                (mes_ano, mes_nome, ordem_mes)
            )
            cursor.execute(
                "INSERT INTO faturamento_mensal (mes_ano, mes_nome, unidade, valor_bruto, valor_liquido, fonte) VALUES (%s, %s, 'Esmeralda', %s, %s, 'Dashboard')",
                (mes_ano, mes_nome, fat_esmeralda, fat_esmeralda)
            )
            cursor.execute(
                "INSERT INTO faturamento_mensal (mes_ano, mes_nome, unidade, valor_bruto, valor_liquido, fonte) VALUES (%s, %s, 'Safira', %s, %s, 'Dashboard')",
                (mes_ano, mes_nome, fat_safira, fat_safira)
            )
            cursor.execute(
                "INSERT INTO gastos_mensais_consolidados (mes_ano, mes_nome, valor_total, fonte) VALUES (%s, %s, %s, 'Dashboard')",
                (mes_ano, mes_nome, gastos)
            )
            conn.commit()
            st.success(f"✅ Dados de {mes_nome} salvos com sucesso!")
            st.rerun()
        except Exception as erro:
            conn.rollback()
            st.error(f"❌ Não foi possível salvar os dados: {erro}")
        finally:
            cursor.close()
            conn.close()