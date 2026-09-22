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
    """Procura qualquer imagem na pasta assets ou na raiz"""
    for pasta in ["assets", "."]:
        for extensao in ["png", "jpg", "jpeg"]:
            arquivos = glob.glob(f"{pasta}/*.{extensao}")
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

# ---------- Análise automática do período selecionado ----------
st.subheader("📌 Análise do período selecionado")

if not resumo_f.empty:
    melhor_faturamento = resumo_f.loc[resumo_f[coluna_fat].idxmax()]
    pior_faturamento   = resumo_f.loc[resumo_f[coluna_fat].idxmin()]
    media_fat          = resumo_f[coluna_fat].mean()
    total_fat          = resumo_f[coluna_fat].sum()
    total_gastos       = resumo_f['gastos_total'].sum()
    total_lucro        = resumo_f['lucro_bruto'].sum()
    margem_media       = resumo_f['margem_liquida'].mean()

    st.markdown(f"""
    - 📅 **Período analisado:** {resumo_f['mes_ano'].min()} a {resumo_f['mes_ano'].max()}
    - 💰 **Faturamento total:** {fmt_brl(total_fat)}
    - 💸 **Gastos totais:** {fmt_brl(total_gastos)}
    - 📈 **Lucro total:** {fmt_brl(total_lucro)}
    - 📊 **Margem média:** {margem_media:.1f}%
    - 🏆 **Melhor mês:** {nome_mes(melhor_faturamento)} — {fmt_brl(melhor_faturamento[coluna_fat])}
    - 📉 **Menor faturamento:** {nome_mes(pior_faturamento)} — {fmt_brl(pior_faturamento[coluna_fat])}
    """)

st.divider()

# ---------- Gráfico 1: Faturamento por mês ----------
st.subheader("📊 Faturamento Líquido por Mês")

df_plot = resumo_f.copy()
df_plot["mes_label"] = df_plot.apply(nome_mes, axis=1)

if unidade_selecionada == "Todas as unidades":
    df_melt = df_plot[["mes_label","fat_liquido_esmeralda","fat_liquido_safira"]].melt(
        id_vars="mes_label", var_name="Unidade", value_name="Faturamento"
    )
    df_melt["Unidade"] = df_melt["Unidade"].map({
        "fat_liquido_esmeralda": "Esmeralda",
        "fat_liquido_safira":    "Safira"
    })
    fig1 = px.bar(df_melt, x="mes_label", y="Faturamento", color="Unidade",
                  barmode="group",
                  color_discrete_map={"Esmeralda": VERDE_ESMERALDA, "Safira": AZUL_MARINHO},
                  labels={"mes_label": "Mês", "Faturamento": "R$"})
else:
    fig1 = px.bar(df_plot, x="mes_label", y=coluna_fat,
                  color_discrete_sequence=[VERDE_ESMERALDA],
                  labels={"mes_label": "Mês", coluna_fat: "Faturamento (R$)"})

fig1.update_layout(plot_bgcolor="white", paper_bgcolor="white")
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ---------- Gráfico 2: Lucro por mês ----------
st.subheader("📈 Lucro Líquido por Mês")

fig2 = px.bar(df_plot, x="mes_label", y="lucro_bruto",
              color="lucro_bruto",
              color_continuous_scale=["#D64545","#f0f0f0","#189030"],
              labels={"mes_label": "Mês", "lucro_bruto": "Lucro (R$)"})
fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white", coloraxis_showscale=False)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------- Gráfico 3: Margem líquida ----------
st.subheader("📉 Margem Líquida Mensal (%)")

fig3 = px.line(df_plot, x="mes_label", y="margem_liquida", markers=True,
               color_discrete_sequence=[AZUL_MARINHO],
               labels={"mes_label": "Mês", "margem_liquida": "Margem (%)"})
fig3.add_hline(y=20, line_dash="dash", line_color="gray",
               annotation_text="Meta 20%", annotation_position="top left")
fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white")
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------- Gráfico 4: Distribuição de gastos ----------
st.subheader("🧾 Distribuição de Gastos por Categoria")

gastos_cat = (gastos_det_f[~gastos_det_f['categoria'].str.contains('labore', case=False, na=False)]
              .groupby("categoria", as_index=False)["valor"].sum()
              .sort_values("valor", ascending=False))

if not gastos_cat.empty:
    fig4 = px.pie(gastos_cat, names="categoria", values="valor",
                  color_discrete_sequence=px.colors.qualitative.Set2)
    fig4.update_layout(paper_bgcolor="white")
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Sem dados de gastos detalhados para o período selecionado.")

st.divider()

# ---------- Tabela resumo ----------
st.subheader("📋 Tabela Resumo Mensal")

df_tabela = df_plot[["mes_label","fat_liquido_esmeralda","fat_liquido_safira",
                      "fat_liquido_geral","gastos_total","lucro_bruto",
                      "margem_liquida","prolabore"]].copy()
df_tabela.columns = ["Mês","Fat. Esmeralda","Fat. Safira","Fat. Geral",
                     "Gastos","Lucro","Margem (%)","Pró-labore (info)"]

for c in ["Fat. Esmeralda","Fat. Safira","Fat. Geral","Gastos","Lucro","Pró-labore (info)"]:
    df_tabela[c] = df_tabela[c].apply(fmt_brl)
df_tabela["Margem (%)"] = df_tabela["Margem (%)"].apply(
    lambda x: f"{x:.1f}%".replace(".", ","))

st.dataframe(df_tabela, use_container_width=True)

st.divider()

# ---------- Formulário: Inserir Novo Mês ----------
st.subheader("➕ Inserir Novo Mês")

with st.form("form_novo_mes"):
    col_a, col_b = st.columns(2)
    with col_a:
        mes_ano        = st.text_input("Mês/Ano (ex: 2026-09)")
        mes_nome_input = st.text_input("Nome do mês (ex: Setembro/2026)")
        fat_bruto_esm  = st.number_input("Fat. Bruto Esmeralda (R$)",   min_value=0.0, step=100.0)
        fat_liq_esm    = st.number_input("Fat. Líquido Esmeralda (R$)", min_value=0.0, step=100.0)
        fat_bruto_saf  = st.number_input("Fat. Bruto Safira (R$)",      min_value=0.0, step=100.0)
        fat_liq_saf    = st.number_input("Fat. Líquido Safira (R$)",    min_value=0.0, step=100.0)
    with col_b:
        gastos_val    = st.number_input("Gastos Totais (R$)",                  min_value=0.0, step=100.0)
        prolabore_val = st.number_input("Pró-labore (retirada do sócio, R$)", min_value=0.0, step=100.0)
        notas         = st.text_area("Observações (opcional)")

    submitted = st.form_submit_button("💾 Salvar Mês")

    if submitted:
        try:
            conn   = conectar()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO faturamento_mensal (mes_ano, mes_nome, unidade, valor_bruto, valor_liquido, fonte)
                VALUES (%s, %s, 'Esmeralda', %s, %s, 'Manual')
            """, (mes_ano, mes_nome_input, fat_bruto_esm, fat_liq_esm))

            cursor.execute("""
                INSERT INTO faturamento_mensal (mes_ano, mes_nome, unidade, valor_bruto, valor_liquido, fonte)
                VALUES (%s, %s, 'Safira', %s, %s, 'Manual')
            """, (mes_ano, mes_nome_input, fat_bruto_saf, fat_liq_saf))

            cursor.execute("""
                INSERT INTO gastos_mensais_consolidados (mes_ano, mes_nome, valor_total, fonte, notas)
                VALUES (%s, %s, %s, 'Manual', %s)
            """, (mes_ano, mes_nome_input, gastos_val, notas))

            if prolabore_val > 0:
                cursor.execute("""
                    INSERT INTO gastos_mensais_detalhados (mes_ano, mes_nome, categoria, unidade, valor, fonte, notas)
                    VALUES (%s, %s, 'Pró-labore', NULL, %s, 'Manual', 'Retirada do sócio')
                """, (mes_ano, mes_nome_input, prolabore_val))

            conn.commit()
            cursor.close()
            conn.close()
            st.success(f"✅ Mês {mes_nome_input} salvo com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
