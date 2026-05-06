import ast
import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Análise de Processos", layout="wide")

st.title("Análise de Processos por Classe, Assunto e Fluxo")


def parse_assuntos(value):
    if pd.isna(value):
        return []

    if isinstance(value, list):
        return value

    text = str(value).strip()

    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
        if not text:
            return []
        return [x.strip().strip('"') for x in text.split(",") if x.strip()]

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    return [text]


def load_default_file():
    for file_name in ["base_processos.csv", "base_processos.xlsx"]:
        if os.path.exists(file_name):
            return file_name
    return None


def read_file(file):
    dtype_map = {
        "id": str,
        "procedure_flow_id": str,
        "judicial_process_number": str,
    }

    if isinstance(file, str):
        if file.endswith(".csv"):
            return pd.read_csv(file, dtype=dtype_map)
        return pd.read_excel(file, dtype=dtype_map)

    if file.name.endswith(".csv"):
        return pd.read_csv(file, dtype=dtype_map)

    return pd.read_excel(file, dtype=dtype_map)


uploaded_file = st.sidebar.file_uploader(
    "Enviar CSV ou Excel",
    type=["csv", "xlsx"]
)

if uploaded_file:
    df = read_file(uploaded_file)
    st.sidebar.success("Arquivo carregado via upload")
else:
    default_file = load_default_file()

    if default_file:
        df = read_file(default_file)
        st.sidebar.info(f"Arquivo carregado: {default_file}")
    else:
        st.warning("Nenhum arquivo encontrado. Coloque base_processos.csv ou base_processos.xlsx na pasta do app.")
        st.stop()
        raise SystemExit(0)


expected_cols = [
    "id",
    "procedure_flow_id",
    "fluxo",
    "judicial_process_number",
    "valor_classe",
    "assuntos",
]

missing = [c for c in expected_cols if c not in df.columns]

if missing:
    st.error(f"Colunas ausentes: {missing}")
    st.stop()


for col in ["id", "procedure_flow_id", "judicial_process_number"]:
    df[col] = df[col].astype(str)

df["fluxo"] = df["fluxo"].fillna("Sem fluxo").astype(str)
df["valor_classe"] = df["valor_classe"].fillna("Sem classe").astype(str)
df["assuntos_lista"] = df["assuntos"].apply(parse_assuntos)


assuntos_df = (
    df[["id", "procedure_flow_id", "fluxo", "assuntos_lista"]]
    .explode("assuntos_lista")
    .dropna(subset=["assuntos_lista"])
    .rename(columns={"assuntos_lista": "assunto"})
)

assuntos_df["assunto"] = assuntos_df["assunto"].astype(str)


# =====================================================
# PAINEL PRINCIPAL
# =====================================================

st.subheader("Painel geral")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de processos", df["id"].nunique())
col2.metric("Fluxos distintos", df["procedure_flow_id"].nunique())
col3.metric("Classes distintas", df["valor_classe"].nunique())
col4.metric("Assuntos distintos", assuntos_df["assunto"].nunique())

st.divider()


# =====================================================
# TOP 50 CLASSES E ASSUNTOS
# =====================================================

st.subheader("Top 50 por volume de processos")

col_left, col_right = st.columns(2)

top_classes = (
    df.groupby("valor_classe", dropna=False)
    .agg(total_processos=("id", "nunique"))
    .reset_index()
    .sort_values("total_processos", ascending=False)
    .head(50)
)

top_assuntos = (
    assuntos_df.groupby("assunto", dropna=False)
    .agg(total_processos=("id", "nunique"))
    .reset_index()
    .sort_values("total_processos", ascending=False)
    .head(50)
)

with col_left:
    st.markdown("### 50 maiores classes")
    st.dataframe(top_classes, use_container_width=True, hide_index=True)

with col_right:
    st.markdown("### 50 maiores assuntos")
    st.dataframe(top_assuntos, use_container_width=True, hide_index=True)

st.divider()


# =====================================================
# CONCENTRAÇÃO POR FLUXO
# =====================================================

st.subheader("Maior concentração por fluxo")

classes_fluxo = (
    df.groupby(["valor_classe", "fluxo"], dropna=False)
    .agg(processos_no_fluxo=("id", "nunique"))
    .reset_index()
)

total_por_classe = (
    df.groupby("valor_classe", dropna=False)
    .agg(total_processos=("id", "nunique"))
    .reset_index()
)

classes_concentracao = classes_fluxo.merge(
    total_por_classe,
    on="valor_classe",
    how="left"
)

classes_concentracao["percentual_no_fluxo"] = (
    classes_concentracao["processos_no_fluxo"]
    / classes_concentracao["total_processos"]
    * 100
).round(2)

classes_concentracao = (
    classes_concentracao
    .sort_values(
        ["valor_classe", "percentual_no_fluxo", "processos_no_fluxo"],
        ascending=[True, False, False]
    )
    .drop_duplicates(subset=["valor_classe"])
)

classes_concentracao = (
    top_classes[["valor_classe"]]
    .merge(classes_concentracao, on="valor_classe", how="left")
    [
        [
            "valor_classe",
            "fluxo",
            "percentual_no_fluxo",
            "processos_no_fluxo",
            "total_processos",
        ]
    ]
)


assunto_fluxo = (
    assuntos_df.groupby(["assunto", "fluxo"], dropna=False)
    .agg(processos_no_fluxo=("id", "nunique"))
    .reset_index()
)

total_por_assunto = (
    assuntos_df.groupby("assunto", dropna=False)
    .agg(total_processos=("id", "nunique"))
    .reset_index()
)

assuntos_concentracao = assunto_fluxo.merge(
    total_por_assunto,
    on="assunto",
    how="left"
)

assuntos_concentracao["percentual_no_fluxo"] = (
    assuntos_concentracao["processos_no_fluxo"]
    / assuntos_concentracao["total_processos"]
    * 100
).round(2)

assuntos_concentracao = (
    assuntos_concentracao
    .sort_values(
        ["assunto", "percentual_no_fluxo", "processos_no_fluxo"],
        ascending=[True, False, False]
    )
    .drop_duplicates(subset=["assunto"])
)

assuntos_concentracao = (
    top_assuntos[["assunto"]]
    .merge(assuntos_concentracao, on="assunto", how="left")
    [
        [
            "assunto",
            "fluxo",
            "percentual_no_fluxo",
            "processos_no_fluxo",
            "total_processos",
        ]
    ]
)


col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### Classes: fluxo de maior concentração")

    classe_event = st.dataframe(
        classes_concentracao,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="classe_concentracao_table",
    )

with col_right:
    st.markdown("### Assuntos: fluxo de maior concentração")

    assunto_event = st.dataframe(
        assuntos_concentracao,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="assunto_concentracao_table",
    )


st.divider()
st.subheader("Detalhamento da seleção")


# =====================================================
# DETALHE DA CLASSE
# =====================================================

classe_rows = classe_event.selection.rows

if classe_rows:
    classe_selecionada = classes_concentracao.iloc[
        classe_rows[0]
    ]["valor_classe"]

    st.markdown(f"### Classe selecionada: `{classe_selecionada}`")

    detalhe_classe = (
        classes_fluxo[
            classes_fluxo["valor_classe"] == classe_selecionada
        ]
        .merge(
            total_por_classe,
            on="valor_classe",
            how="left"
        )
    )

    detalhe_classe["percentual_no_fluxo"] = (
        detalhe_classe["processos_no_fluxo"]
        / detalhe_classe["total_processos"]
        * 100
    ).round(2)

    detalhe_classe = detalhe_classe[
        [
            "valor_classe",
            "fluxo",
            "percentual_no_fluxo",
            "processos_no_fluxo",
            "total_processos",
        ]
    ].sort_values(
        "processos_no_fluxo",
        ascending=False
    )

    st.dataframe(
        detalhe_classe,
        use_container_width=True,
        hide_index=True
    )


# =====================================================
# DETALHE DO ASSUNTO
# =====================================================

assunto_rows = assunto_event.selection.rows

if assunto_rows:
    assunto_selecionado = assuntos_concentracao.iloc[
        assunto_rows[0]
    ]["assunto"]

    st.markdown(f"### Assunto selecionado: `{assunto_selecionado}`")

    detalhe_assunto = (
        assunto_fluxo[
            assunto_fluxo["assunto"] == assunto_selecionado
        ]
        .merge(
            total_por_assunto,
            on="assunto",
            how="left"
        )
    )

    detalhe_assunto["percentual_no_fluxo"] = (
        detalhe_assunto["processos_no_fluxo"]
        / detalhe_assunto["total_processos"]
        * 100
    ).round(2)

    detalhe_assunto = detalhe_assunto[
        [
            "assunto",
            "fluxo",
            "percentual_no_fluxo",
            "processos_no_fluxo",
            "total_processos",
        ]
    ].sort_values(
        "processos_no_fluxo",
        ascending=False
    )

    st.dataframe(
        detalhe_assunto,
        use_container_width=True,
        hide_index=True
    )


if not classe_rows and not assunto_rows:
    st.info(
        "Clique em uma linha da tabela de classes ou assuntos para ver o detalhamento completo por fluxo."
    )