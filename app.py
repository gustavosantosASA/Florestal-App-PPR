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
    """Carrega os dados do cronograma com filtro opcional por e-mail"""
    return read_sheet_to_dataframe(
        SPREADSHEET_URL, 
        WORKSHEET_DATA,
        user_email
    )

def get_filter_options(df, column):
    """Gera opções para os filtros dinâmicos incluindo 'Todos'"""
    try:
        # Remove valores nulos e duplicados, converte para string e ordena
        unique_values = df[column].dropna().unique()
        options = ["Todos"] + sorted([str(x) for x in unique_values if x not in [None, "", " "]])
        return options
    except KeyError:
        st.error(f"Coluna '{column}' não encontrada na planilha")
        return ["Todos"]
    except Exception as e:
        st.error(f"Erro ao gerar opções para {column}: {str(e)}")
        return ["Todos"]


def show_main_app():
    """Conteúdo principal após login"""
    # Verificação de segurança
    if 'user' not in st.session_state:
        st.error("Sessão inválida. Redirecionando para login...")
        st.session_state.clear()
        st.rerun()
    
    user = st.session_state['user']
    is_admin = user['Tipo de Usuário'] == "Administrador"
    user_email = None if is_admin else user['Email']
    
    # Carrega dados
    df = load_data(user_email)
    
    if df is None or df.empty:
        st.warning("Nenhum dado encontrado")
        return
    
    # Define colunas para filtros (ajuste conforme sua planilha)
    filter_columns = ['Referência', 'Setor', 'Responsável', 'Status']
    
    # Seção de filtros
    st.header("Filtros Avançados", divider="rainbow")
    filters = create_dynamic_filters(df, filter_columns)
    
    # Aplica filtros
    filtered_df = apply_dynamic_filters(df, filters)
    
    # Exibe resultados
    st.header("Resultados", divider="rainbow")
    st.subheader(f"📊 Total de registros: {len(filtered_df)}")
    
    if not filtered_df.empty:
        for _, row in filtered_df.iterrows():
            with st.container(border=True):
                # Seu código de exibição por card
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**Referência:** `{row['Referência']}`")
                    st.markdown(f"**Descrição:** {row['Descrição Meta']}")
                with cols[1]:
                    if st.button("Editar", key=f"edit_{row.name}"):
                        handle_edit(row)
    else:
        st.warning("Nenhum registro corresponde aos filtros selecionados")
        
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

def apply_dynamic_filters(df, filters):
    """Aplica múltiplos filtros ao DataFrame de forma segura"""
    try:
        filtered_df = df.copy()
        for column, value in filters.items():
            if value != "Todos":
                # Converte ambos os valores para string para comparação segura
                filtered_df = filtered_df[filtered_df[column].astype(str) == str(value)]
        return filtered_df
    except KeyError as e:
        st.error(f"Erro: Coluna '{e.args[0]}' não existe na planilha")
        return df
    except Exception as e:
        st.error(f"Erro ao filtrar dados: {str(e)}")
        return df

def create_dynamic_filters(df, filter_columns):
    """Cria os controles de filtro dinâmico e retorna os valores selecionados"""
    filters = {}
    cols = st.columns(len(filter_columns))
    
    for i, column in enumerate(filter_columns):
        with cols[i]:
            try:
                options = ["Todos"] + sorted(df[column].dropna().unique().tolist())
                filters[column] = st.selectbox(
                    f"Filtrar por {column}",
                    options=options,
                    key=f"filter_{column}"
                )
            except KeyError:
                st.error(f"Coluna '{column}' não encontrada")
                filters[column] = "Todos"
    
    return filters


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
