import datetime
import os

import altair as alt
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(page_title="Monitoramento de Preços", page_icon="🐾")
st.title("🐾 Monitoramento de Preços - Cesta Básica Animal")
st.write(
    """
    Esta ferramenta auxilia no monitoramento de preços de produtos essenciais para abrigos de animais em Porto Alegre. 
    Voluntários podem registrar os preços encontrados, contribuindo para uma base de dados colaborativa que facilita a doação com melhor custo-benefício.
    """
)

# Caminhos dos arquivos
CSV_PRECOS = "dados_precos.csv"
CSV_CESTA = "cesta_basica_animal.csv"

# Carregar a cesta básica animal
df_cesta = pd.read_csv(CSV_CESTA)

# Criar coluna de chave combinada
df_cesta["Chave"] = df_cesta["Idade"].str.capitalize() + " / " + df_cesta["Porte"].str.capitalize()

# Obter combinações únicas
combinacoes = sorted(df_cesta["Chave"].unique())

# Inicializar CSV de preços se não existir
if os.path.exists(CSV_PRECOS):
    df_precos = pd.read_csv(CSV_PRECOS, parse_dates=["Data da Consulta"])
else:
    df_precos = pd.DataFrame(columns=[
        "Código do Usuário", "Porte", "Idade", "Categoria", "Item",
        "Preço Unitário (R$)", "Data da Consulta", "Local da Consulta"
    ])

# --- Formulário de coleta de preços ---
st.header("📋 Registrar preços por porte e idade")

# Etapa 1: Escolha da combinação
combinacao_escolhida = st.selectbox("Selecione a combinação de porte e idade do animal:", combinacoes)

if combinacao_escolhida:
    idade, porte = [parte.strip() for parte in combinacao_escolhida.split("/")]

    produtos_filtrados = df_cesta[
        (df_cesta["Porte"].str.lower() == porte.lower()) &
        (df_cesta["Idade"].str.lower() == idade.lower())
    ]

    st.markdown(f"**Itens da cesta para {combinacao_escolhida}:**")

    # ... código anterior até o formulário permanece igual ...

    with st.form("formulario_precos"):
        registros = []

        codigo_usuario = st.text_input("Código do Usuário (15 caracteres)").strip()
        data_consulta = st.date_input("Data da Consulta", datetime.date.today())
        local_consulta = st.text_input("Local da Consulta")

        for _, row in produtos_filtrados.iterrows():
            st.markdown(f"**{row['Item']}**  \n_{row['Descrição']}_")
            preco = st.number_input(
                f"Preço unitário (R$) para '{row['Item']}'", 
                key=row['Item'], 
                min_value=0.0, 
                step=0.01
            )
            registros.append({
                "Categoria": row["Categoria"],
                "Item": row["Item"],
                "Preço Unitário (R$)": preco
            })

        enviado = st.form_submit_button("Registrar preços")

    if enviado:
        if len(codigo_usuario) != 15:
            st.error("O código do usuário deve conter exatamente 15 caracteres.")
        elif not local_consulta:
            st.error("Informe o local da consulta.")
        else:
            # Verificar autorização
            try:
                df_autorizados = pd.read_csv("autorizados.csv")
            except Exception as e:
                st.error(f"Erro ao carregar arquivo de autorizados: {e}")
                df_autorizados = pd.DataFrame()

            if df_autorizados.empty or codigo_usuario not in df_autorizados["chave"].values:
                st.error("Chave de autorização não encontrada. Os dados não foram enviados.")
            else:
                # Obter nome completo correspondente
                nome_completo = df_autorizados.loc[df_autorizados["chave"] == codigo_usuario, "nome_completo"].values[0]

                novas_linhas = []
                for reg in registros:
                    if reg["Preço Unitário (R$)"] > 0:
                        novas_linhas.append({
                            "Código do Usuário": nome_completo,  # substituído aqui
                            "Porte": porte,
                            "Idade": idade,
                            "Categoria": reg["Categoria"],
                            "Item": reg["Item"],
                            "Preço Unitário (R$)": reg["Preço Unitário (R$)"],
                            "Data da Consulta": data_consulta,
                            "Local da Consulta": local_consulta
                        })

                if novas_linhas:
                    df_precos = pd.concat([pd.DataFrame(novas_linhas), df_precos], ignore_index=True)
                    df_precos.to_csv(CSV_PRECOS, index=False)
                    st.success(f"{len(novas_linhas)} registro(s) salvos com sucesso!")
                else:
                    st.warning("Nenhum preço foi informado. Nenhum dado foi salvo.")


# --- Visualização dos dados ---
st.header("📊 Dados Coletados")
st.write(f"Total de registros: `{len(df_precos)}`")
st.data_editor(
    df_precos,
    use_container_width=True,
    hide_index=True,
    disabled=["Código do Usuário", "Data da Consulta", "Categoria", "Item", "Porte", "Idade"]
)

# Estatísticas
st.header("📈 Estatísticas")

if not df_precos.empty:
    col1, col2 = st.columns(2)
    preco_medio_total = df_precos["Preço Unitário (R$)"].mean()
    item_popular = df_precos["Item"].mode().iloc[0]

    col1.metric("Preço médio geral (R$)", f"{preco_medio_total:.2f}")
    col2.metric("Item mais registrado", item_popular)

    st.write("##### Preço por categoria")
    chart_categoria = (
        alt.Chart(df_precos)
        .mark_boxplot()
        .encode(
            x="Categoria:N",
            y="Preço Unitário (R$):Q",
            color="Categoria:N"
        )
        .properties(height=300)
    )
    st.altair_chart(chart_categoria, use_container_width=True)

    st.write("##### Evolução média de preços ao longo do tempo")
    chart_tempo = (
        alt.Chart(df_precos)
        .mark_line(point=True)
        .encode(
            x="Data da Consulta:T",
            y="mean(Preço Unitário (R$)):Q",
            color="Categoria:N"
        )
        .properties(height=300)
    )
    st.altair_chart(chart_tempo, use_container_width=True)
else:
    st.info("Nenhum dado foi registrado ainda.")
