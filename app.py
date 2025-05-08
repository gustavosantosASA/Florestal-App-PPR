import streamlit as st
import pandas as pd
from utils.google_sheets import (
    read_sheet_to_dataframe,
    get_user_by_login,
    register_user,
    update_row_in_sheet,
    delete_row_in_sheet
)

# ==================================================
# CONFIGURAÇÕES
# ==================================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1VZpV97NIhd16jAyzMpVE_8VhSs-bSqi4DXmySsx2Kc4/edit#gid=761491838"
WORKSHEET_DATA = "Cronograma"
WORKSHEET_USERS = "Usuários"

# Configuração da página
st.set_page_config(
    page_title="Sistema de Cronograma", 
    layout="wide",
    page_icon="📅"
)

# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================
def apply_dynamic_filters(df, filters):
    """Aplica filtros dinâmicos ao DataFrame"""
    for column, value in filters.items():
        if value != "Todos":
            df = df[df[column] == value]
    return df

def get_filter_options(df, column):
    """Gera opções para os filtros dinâmicos"""
    options = ["Todos"] + sorted(df[column].dropna().unique().tolist())
    return [str(x) for x in options if x]

# ==================================================
# INTERFACE PRINCIPAL
# ==================================================
def show_main_app():
    """Conteúdo principal após login"""
    # Configurações de usuário
    user = st.session_state['user']
    is_admin = user['Tipo de Usuário'] == "Administrador"
    
    # Barra lateral
    st.sidebar.title(f"👤 {user['Login']}")
    st.sidebar.write(f"Tipo: {user['Tipo de Usuário']}")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
    
    # Título e status
    st.title("📅 Visualizador de Cronograma")
    if is_admin:
        st.success("🔧 Modo Administrador: Visualizando todos os registros")
    else:
        st.info(f"👤 Visualizando apenas seus registros (E-mail: {user['Email']})")
    
    # Carrega dados
    df = load_data(user['Email'] if not is_admin else None)
    
    if df is not None and not df.empty:
        # ========================================
        # SEÇÃO DE FILTROS DINÂMICOS
        # ========================================
        st.header("Filtros Avançados", divider="rainbow")
        
        # Seleciona apenas colunas relevantes para filtros
        filter_columns = ['Referência', 'Setor', 'Responsável', 'Status']  # Ajuste conforme suas colunas
        
        # Cria filtros dinâmicos
        cols = st.columns(len(filter_columns))
        filters = {}
        
        for i, col in enumerate(filter_columns):
            with cols[i]:
                filters[col] = st.selectbox(
                    f"Filtrar por {col}",
                    options=get_filter_options(df, col),
                    key=f"filter_{col}"
                )
        
        # Aplica filtros
        filtered_df = apply_dynamic_filters(df.copy(), filters)
        
        # ========================================
        # EXIBIÇÃO DOS CARDS (CONTAINER APPROACH)
        # ========================================
        st.header("Resultados", divider="rainbow")
        st.subheader(f"📊 Total de registros: {len(filtered_df)}")
        
        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    # Layout do card
                    cols = st.columns([4, 1])
                    
                    # Coluna esquerda: Dados
                    with cols[0]:
                        st.markdown(f"**Referência:** `{row['Referência']}`")
                        st.markdown(f"**Descrição:** {row['Descrição Meta']}")
                        st.markdown(f"**Responsável:** {row['Responsável']}")
                        st.markdown(f"**Status:** {row.get('Status', 'N/A')}")
                    
                    # Coluna direita: Botões de ação
                    with cols[1]:
                        if st.button("📝 Editar", key=f"edit_{idx}"):
                            st.session_state['editing_row'] = row.to_dict()
                        
                        if st.button("🗑️ Excluir", key=f"delete_{idx}"):
                            st.session_state['deleting_row'] = row.to_dict()
                        
                        if st.button("🔍 Detalhes", key=f"details_{idx}"):
                            st.session_state['viewing_row'] = row.to_dict()
            
            # ========================================
            # MODAIS DE AÇÃO (EDITAR/EXCLUIR/DETALHES)
            # ========================================
            if 'editing_row' in st.session_state:
                show_edit_modal(pd.Series(st.session_state['editing_row']))
                
            if 'deleting_row' in st.session_state:
                show_delete_modal(pd.Series(st.session_state['deleting_row']))
                
            if 'viewing_row' in st.session_state:
                show_details_modal(pd.Series(st.session_state['viewing_row']))
        
        else:
            st.warning("Nenhum registro encontrado com os filtros selecionados!")
    
    elif df is not None and df.empty:
        st.warning("Nenhum registro encontrado na planilha!")
    else:
        st.error("Erro ao carregar dados. Verifique sua conexão.")

# ==================================================
# FUNÇÕES DOS MODAIS
# ==================================================
def show_edit_modal(row):
    """Modal de edição"""
    with st.expander(f"📝 Editando: {row['Referência']}", expanded=True):
        with st.form(f"edit_form_{row.name}"):
            # Campos editáveis (ajuste conforme suas colunas)
            referencia = st.text_input("Referência", value=row['Referência'])
            descricao = st.text_area("Descrição", value=row['Descrição Meta'])
            status = st.selectbox(
                "Status", 
                options=["Em andamento", "Concluído", "Pendente"],
                index=["Em andamento", "Concluído", "Pendente"].index(row.get('Status', 'Pendente'))
            )
            
            if st.form_submit_button("💾 Salvar Alterações"):
                try:
                    # Atualiza a planilha
                    updated = update_row_in_sheet(
                        SPREADSHEET_URL,
                        WORKSHEET_DATA,
                        row.name + 2,  # +2 para compensar cabeçalho e index 0
                        [referencia, descricao, status]  # Ajuste conforme suas colunas
                    )
                    if updated:
                        st.success("Registro atualizado com sucesso!")
                        st.cache_data.clear()
                        del st.session_state['editing_row']
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar: {str(e)}")
            
            if st.button("❌ Cancelar"):
                del st.session_state['editing_row']
                st.rerun()

def show_delete_modal(row):
    """Modal de exclusão"""
    with st.expander(f"🗑️ Excluir: {row['Referência']}", expanded=True):
        st.warning("Tem certeza que deseja excluir este registro?")
        st.json(row.to_dict())
        
        if st.button("✅ Confirmar Exclusão", type="primary"):
            try:
                deleted = delete_row_in_sheet(
                    SPREADSHEET_URL,
                    WORKSHEET_DATA,
                    row.name + 2
                )
                if deleted:
                    st.success("Registro excluído com sucesso!")
                    st.cache_data.clear()
                    del st.session_state['deleting_row']
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {str(e)}")
        
        if st.button("❌ Cancelar"):
            del st.session_state['deleting_row']
            st.rerun()

def show_details_modal(row):
    """Modal de detalhes"""
    with st.expander(f"🔍 Detalhes: {row['Referência']}", expanded=True):
        st.json(row.to_dict())
        
        if st.button("⬅️ Voltar"):
            del st.session_state['viewing_row']
            st.rerun()

# ==================================================
# PONTO DE ENTRADA
# ==================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    
    if not st.session_state['logged_in']:
        if st.session_state['show_register']:
            show_register_form()
        else:
            show_login_form()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
