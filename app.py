import streamlit as st
import pandas as pd
import hashlib
from utils.google_sheets import (
    read_sheet_to_dataframe,
    get_user_by_login,
    register_user
)

# Verificação inicial
if 'GOOGLE_CREDENTIALS' not in st.secrets:
    st.error("Credenciais do Google não configuradas!")
    st.stop()

# Configurações
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", "https://docs.google.com/spreadsheets/d/1VZpV97NIhd16jAyzMpVE_8VhSs-bSqi4DXmySsx2Kc4/edit")
WORKSHEET_DATA = "Cronograma"
WORKSHEET_USERS = "Usuários"

# Configuração da página
st.set_page_config(
    page_title="Sistema de Cronograma", 
    layout="wide",
    page_icon="🔒"
)

# ==================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ==================================================
def hash_password(password):
    """Cria hash SHA-256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(login, password):
    """Verifica se usuário existe e a senha está correta"""
    user = get_user_by_login(SPREADSHEET_URL, WORKSHEET_USERS, login)
    if user and user['Senha'] == hash_password(password):
        return True, user
    return False, None

def show_login_form():
    """Formulário de login"""
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
    
    # Link para cadastro
    if st.button("📝 Criar nova conta"):
        st.session_state['show_register'] = True
        st.rerun()

def show_register_form():
    """Formulário de cadastro"""
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
                    'Senha': hash_password(password),  # Armazena o hash
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
# FUNÇÕES PRINCIPAIS DO SISTEMA
# ==================================================
@st.cache_data(ttl=300)
def load_data_filtered(user_email=None):
    """Carrega os dados do cronograma com filtro por e-mail"""
    df = read_sheet_to_dataframe(SPREADSHEET_URL, WORKSHEET_DATA)
    
    if df is not None and user_email:
        # Verifica se a coluna 'E-mail' existe
        if 'E-mail' in df.columns:
            # Filtra mantendo a caixa original mas comparando em lowercase
            df = df[df['E-mail'].str.lower() == user_email.lower()]
        else:
            st.warning("Coluna 'E-mail' não encontrada na planilha. Mostrando todos os dados.")
    
    return df

def show_main_app():
    """Conteúdo principal após login"""
    # Barra superior com informações do usuário
    st.sidebar.title(f"👋 Olá, {st.session_state['user']['Login']}!")
    st.sidebar.write(f"E-mail: {st.session_state['user']['Email']}")
    st.sidebar.write(f"Tipo: {st.session_state['user']['Tipo de Usuário']}")
    
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # Título da página
    st.title("📅 Visualizador de Cronograma")

    if 'user' not in st.session_state or 'Email' not in st.session_state['user']:
        st.error("Erro: Informações do usuário não encontradas. Faça login novamente.")
        st.session_state.clear()
        st.stop()
    
    # Carrega dados filtrados pelo e-mail do usuário
    df = load_data_filtered(st.session_state['user']['Email'])
    
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
            selections['Referência'] = st.selectbox(
                "Referência",
                options=get_filter_options('Referência', df),
                index=0
            )
            
            temp_df = df[df['Referência'] == selections['Referência']] if selections['Referência'] != "Todos" else df
            selections['Setor'] = st.selectbox(
                "Setor",
                options=get_filter_options('Setor', temp_df),
                index=0
            )

        with col2:
            if selections['Setor'] != "Todos":
                temp_df = temp_df[temp_df['Setor'] == selections['Setor']]
            
            selections['Responsável'] = st.selectbox(
                "Responsável",
                options=get_filter_options('Responsável', temp_df),
                index=0
            )
            
            if selections['Responsável'] != "Todos":
                temp_df = temp_df[temp_df['Responsável'] == selections['Responsável']]
            
            selections['Descrição Meta'] = st.selectbox(
                "Descrição Meta",
                options=get_filter_options('Descrição Meta', temp_df),
                index=0
            )

        with col3:
            if selections['Descrição Meta'] != "Todos":
                temp_df = temp_df[temp_df['Descrição Meta'] == selections['Descrição Meta']]
            
            selections['Responsável Área'] = st.selectbox(
                "Responsável Área",
                options=get_filter_options('Responsável Área', temp_df),
                index=0
            )
            
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
        st.subheader(f"📊 Total de registros: {len(filtered_df)}")
        
        # Tabela com dados
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
        
        if filtered_df.empty:
            st.warning("Nenhum registro encontrado com os filtros selecionados!")

    elif df is not None and df.empty:
        st.warning("A planilha está vazia!")
    else:
        st.error("❌ Erro ao carregar dados. Verifique sua conexão.")

# ==================================================
# PONTO DE ENTRADA DA APLICAÇÃO
# ==================================================
def main():
    # Inicializa estado da sessão
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_register' not in st.session_state:
        st.session_state['show_register'] = False
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    
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
