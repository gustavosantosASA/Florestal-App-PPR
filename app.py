import streamlit as st
import pandas as pd
from utils.google_sheets import read_sheet_to_dataframe

# Configurações
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1VZpV97NIhd16jAyzMpVE_8VhSs-bSqi4DXmySsx2Kc4/edit#gid=761491838"
WORKSHEET_NAME = "Cronograma"

# Configuração da página
st.set_page_config(page_title="Visualizador de Cronograma", layout="wide")
st.title("📅 Visualizador de Cronograma")

# Carrega os dados
@st.cache_data(ttl=300)
def load_data():
    return read_sheet_to_dataframe(SPREADSHEET_URL, WORKSHEET_NAME)

df = load_data()

if df is not None:
    # --- SEÇÃO DE FILTROS DINÂMICOS ---
    st.header("Filtros", divider="rainbow")
    
    # Função auxiliar para opções de filtro
    def get_filter_options(column, base_df):
        options = base_df[column].unique()
        return ["Todos"] + sorted(filter(None, set(str(x) for x in options)))

    # Layout dos filtros (3 colunas)
    col1, col2, col3 = st.columns(3)
    
    # Dicionário para armazenar seleções
    selections = {}
    
    with col1:
        # Filtro de Referência
        selections['Referência'] = st.selectbox(
            "Referência",
            options=get_filter_options('Referência', df),
            index=0
        )
        
        # Filtro de Setor (dinâmico)
        temp_df = df[df['Referência'] == selections['Referência']] if selections['Referência'] != "Todos" else df
        selections['Setor'] = st.selectbox(
            "Setor",
            options=get_filter_options('Setor', temp_df),
            index=0
        )

    with col2:
        # Filtro de Responsável (dinâmico)
        if selections['Setor'] != "Todos":
            temp_df = temp_df[temp_df['Setor'] == selections['Setor']]
        
        selections['Responsável'] = st.selectbox(
            "Responsável",
            options=get_filter_options('Responsável', temp_df),
            index=0
        )
        
        # Filtro de Descrição Meta (dinâmico)
        if selections['Responsável'] != "Todos":
            temp_df = temp_df[temp_df['Responsável'] == selections['Responsável']]
        
        selections['Descrição Meta'] = st.selectbox(
            "Descrição Meta",
            options=get_filter_options('Descrição Meta', temp_df),
            index=0
        )

    with col3:
        # Filtro de Responsável Área (dinâmico)
        if selections['Descrição Meta'] != "Todos":
            temp_df = temp_df[temp_df['Descrição Meta'] == selections['Descrição Meta']]
        
        selections['Responsável Área'] = st.selectbox(
            "Responsável Área",
            options=get_filter_options('Responsável Área', temp_df),
            index=0
        )
        
        # Filtro de E-mail (dinâmico)
        if selections['Responsável Área'] != "Todos":
            temp_df = temp_df[temp_df['Responsável Área'] == selections['Responsável Área']]
        
        selections['E-mail'] = st.selectbox(
            "E-mail",
            options=get_filter_options('E-mail', temp_df),
            index=0
        )

    # --- APLICA FILTROS ---
    filtered_df = df.copy()
    for col, val in selections.items():
        if val != "Todos":
            filtered_df = filtered_df[filtered_df[col] == val]
    
    # --- EXIBIÇÃO DOS RESULTADOS ---
    st.header("Resultados", divider="rainbow")
    st.subheader(f"🚀 Total de registros encontrados: {len(filtered_df)}")
    
    # Estilização do DataFrame
    st.dataframe(
        filtered_df,
        height=600,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Referência': st.column_config.TextColumn(width="medium"),
            'Descrição Meta': st.column_config.TextColumn(width="large"),
            'E-mail': st.column_config.TextColumn(width="medium")
        }
    )
    
    # Mensagem alternativa se não houver resultados
    if filtered_df.empty:
        st.warning("Nenhum registro encontrado com os filtros selecionados!")

elif df is not None and df.empty:
    st.warning("A planilha está vazia!")
else:
    st.error("❌ Falha ao carregar os dados. Verifique:")
    st.markdown("""
    - Conexão com a internet
    - Permissões da planilha
    - Nome correto da aba ('Cronograma')
    - Configuração do service account
    """)