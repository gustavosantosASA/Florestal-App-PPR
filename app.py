import streamlit as st
import pandas as pd
import hashlib
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
# FUNÇÕES DE AUTENTICAÇÃO
# ==================================================
def hash_password(password):
    """Cria hash SHA-256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(login, password):
    """Verifica as credenciais do usuário"""
    user = get_user_by_login(SPREADSHEET_URL, WORKSHEET_USERS, login)
    if user and user['Senha'] == hash_password(password):
        return True, user
    return False, None

def show_login_form():
    """Exibe o formulário de login"""
    st.title("🔒 Acesso ao Sistema")
    
    with st.form("login_form"):
        login = st.text_input("Login")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            if not login or not password:
                st.error("Preencha todos os campos!")
            else:
                success, user = check_login(login, password)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = user
                    st.rerun()
                else:
                    st.error("Login ou senha incorretos!")
    
    if st.button("Não tem conta? Cadastre-se"):
        st.session_state['show_register'] = True
        st.rerun()

def show_register_form():
    """Exibe o formulário de cadastro"""
    st.title("📝 Cadastro de Usuário")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            login = st.text_input("Login*")
            password = st.text_input("Senha*", type="password")
        with col2:
            email = st.text_input("Email*")
            confirm_password = st.text_input("Confirmar Senha*", type="password")
        
        user_type = st.selectbox("Tipo de Usuário", ["Usuário", "Administrador"])
        
        submitted = st.form_submit_button("Cadastrar")
        
        if submitted:
            if not all([login, email, password, confirm_password]):
                st.error("Preencha todos os campos obrigatórios!")
            elif password != confirm_password:
                st.error("As senhas não coincidem!")
            elif len(password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres")
            else:
                user_data = {
                    'Login': login,
                    'Email': email,
                    'Senha': hash_password(password),
                    'Tipo de Usuário': user_type
                }
                success, message = register_user(SPREADSHEET_URL, WORKSHEET_USERS, user_data)
                if success:
                    st.success("Cadastro realizado! Faça login.")
                    st.session_state['show_register'] = False
                    st.rerun()
                else:
                    st.error(message)
    
    if st.button("Voltar para Login"):
        st.session_state['show_register'] = False
        st.rerun()

# ==================================================
# FUNÇÕES PRINCIPAIS DO SISTEMA
# ==================================================
@st.cache_data(ttl=300)
def load_data(user_email=None):
    """Carrega os dados do cronograma"""
    return read_sheet_to_dataframe(SPREADSHEET_URL, WORKSHEET_DATA, user_email)

def show_main_app():
    """Conteúdo principal após login"""
    # 1. Verificação de segurança
    if 'user' not in st.session_state:
        st.error("Erro de autenticação. Redirecionando para login...")
        st.session_state.clear()
        st.rerun()
    
    # 2. Define o tipo de usuário
    user_type = st.session_state['user']['Tipo de Usuário']
    is_admin = user_type == "Administrador"
    user_email = None if is_admin else st.session_state['user']['Email']
    
    # 3. Barra lateral
    st.sidebar.title(f"👤 {st.session_state['user']['Login']}")
    st.sidebar.write(f"Tipo: {user_type}")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
    
    # 4. Carrega dados (com filtro para não-admins)
    df = load_data(user_email)
    
    # 5. Exibe mensagem de contexto
    st.title("📅 Visualizador de Cronograma")
    if is_admin:
        st.success("🔧 Modo Administrador: Visualizando todos os registros")
    else:
        st.info(f"👤 Visualizando apenas seus registros (E-mail: {user_email})")
    
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
    """Função principal que controla o fluxo da aplicação"""
    # Inicializa variáveis de sessão
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    
    # Controle de fluxo
    if not st.session_state['logged_in']:
        if st.session_state['show_register']:
            show_register_form()
        else:
            show_login_form()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
