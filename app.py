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
# FUNÇÕES DE AUTENTICAÇÃO (MANTIDAS)
# ==================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(login, password):
    user = get_user_by_login(SPREADSHEET_URL, WORKSHEET_USERS, login)
    if user and user['Senha'] == hash_password(password):
        return True, user
    return False, None

def show_login_form():
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
                    st.error("Credenciais inválidas!")
    
    if st.button("📝 Criar nova conta"):
        st.session_state['show_register'] = True
        st.rerun()

def show_register_form():
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
    
    if st.button("⬅️ Voltar para Login"):
        st.session_state['show_register'] = False
        st.rerun()

# ==================================================
# FUNÇÕES PRINCIPAIS (COM CONTAINER APPROACH)
# ==================================================
@st.cache_data(ttl=300)
def load_data(user_email=None):
    df = read_sheet_to_dataframe(SPREADSHEET_URL, WORKSHEET_DATA)
    if df is not None and user_email and 'E-mail' in df.columns:
        df = df[df['E-mail'].str.lower() == user_email.lower()]
    return df

def show_row_actions(row):
    """Mostra botões de ação para cada linha"""
    cols = st.columns([1, 1, 2])
    with cols[0]:
        if st.button("📝 Editar", key=f"edit_{row.name}"):
            st.session_state['editing_row'] = row.to_dict()
    with cols[1]:
        if st.button("🗑️ Excluir", key=f"delete_{row.name}"):
            st.session_state['deleting_row'] = row.to_dict()
    with cols[2]:
        if st.button("🔍 Detalhes", key=f"details_{row.name}"):
            st.session_state['viewing_row'] = row.to_dict()

def show_row_details(row):
    """Mostra detalhes expandidos de uma linha"""
    with st.expander(f"Detalhes: {row['Referência']}", expanded=True):
        st.json(row.to_dict())

def handle_edit(row_data):
    """Lógica para edição de registro"""
    with st.form(f"edit_form_{row_data['Referência']}"):
        st.write("### Editar Registro")
        
        # Crie campos de edição para cada coluna necessária
        referencia = st.text_input("Referência", value=row_data['Referência'])
        descricao = st.text_area("Descrição", value=row_data['Descrição Meta'])
        
        if st.form_submit_button("Salvar Alterações"):
            try:
                # Atualize a planilha (implemente esta função no google_sheets.py)
                updated = update_row_in_sheet(
                    SPREADSHEET_URL,
                    WORKSHEET_DATA,
                    row_data.name + 2,  # +2 porque a planilha começa na linha 1 e tem cabeçalho
                    [referencia, descricao]  # Ajuste conforme suas colunas
                )
                if updated:
                    st.success("Registro atualizado!")
                    st.cache_data.clear()
                    del st.session_state['editing_row']
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {str(e)}")

def handle_delete(row_data):
    """Lógica para exclusão de registro"""
    st.warning(f"Tem certeza que deseja excluir: {row_data['Referência']}?")
    if st.button("✅ Confirmar Exclusão", key=f"confirm_del_{row_data.name}"):
        try:
            # Implemente delete_row_in_sheet no google_sheets.py
            deleted = delete_row_in_sheet(
                SPREADSHEET_URL,
                WORKSHEET_DATA,
                row_data.name + 2  # +2 pela mesma razão acima
            )
            if deleted:
                st.success("Registro excluído!")
                st.cache_data.clear()
                del st.session_state['deleting_row']
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {str(e)}")

def show_main_app():
    """Conteúdo principal após login"""
    # Barra lateral
    st.sidebar.title(f"👤 {st.session_state['user']['Login']}")
    st.sidebar.write(f"Tipo: {st.session_state['user']['Tipo de Usuário']}")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
    
    # Verifica se é admin
    is_admin = st.session_state['user']['Tipo de Usuário'] == "Administrador"
    user_email = None if is_admin else st.session_state['user']['Email']
    
    # Título e filtros
    st.title("📅 Visualizador de Cronograma")
    if is_admin:
        st.success("🔧 Modo Administrador: Visualizando todos os registros")
    else:
        st.info(f"👤 Visualizando apenas seus registros")
    
    # Carrega dados filtrados
    df = load_data(user_email)
    
    if df is not None and not df.empty:
        # Mostra cada registro como um card
        for idx, row in df.iterrows():
            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**Referência:** `{row['Referência']}`")
                    st.markdown(f"**Descrição:** {row['Descrição Meta']}")
                    st.markdown(f"**Responsável:** {row['Responsável']}")
                    st.markdown(f"**Status:** {row.get('Status', 'N/A')}")
                
                with cols[1]:
                    show_row_actions(row)
        
        # Trata ações
        if 'editing_row' in st.session_state:
            handle_edit(pd.Series(st.session_state['editing_row']))
            
        if 'deleting_row' in st.session_state:
            handle_delete(pd.Series(st.session_state['deleting_row']))
            
        if 'viewing_row' in st.session_state:
            show_row_details(pd.Series(st.session_state['viewing_row']))
    
    elif df is not None and df.empty:
        st.warning("Nenhum registro encontrado!")
    else:
        st.error("Erro ao carregar dados. Verifique sua conexão.")

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
