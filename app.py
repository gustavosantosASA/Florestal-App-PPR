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
    if user and user.get('Senha') == hash_password(password):
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
    df = read_sheet_to_dataframe(
        SPREADSHEET_URL, 
        WORKSHEET_DATA,
        user_email
    )
    # Garante que o DataFrame tenha um índice único para edição/exclusão
    if df is not None and not df.empty:
        # Preserva o índice original para uso em operações de edição/exclusão
        df['_original_index'] = df.index
    return df

def get_filter_options(df, column, previous_filters=None):
    """
    Gera opções para os filtros dinâmicos incluindo 'Todos',
    considerando os filtros já aplicados
    """
    try:
        # Se houver filtros anteriores, aplica-os para filtrar o dataframe
        filtered_df = df.copy()
        if previous_filters:
            for col, val in previous_filters.items():
                if val != "Todos" and col in filtered_df.columns:
                    if col == 'Descrição Meta':
                        # Para Descrição Meta, remove a parte "..." se estiver presente
                        search_value = str(val).replace("...", "")
                        # Usa busca por substring (contém) em vez de igualdade exata
                        filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(search_value, case=False, na=False)]
                    else:
                        # Para outros campos, mantém a comparação de igualdade exata
                        filtered_df = filtered_df[filtered_df[col].astype(str) == str(val)]
        
        # Remove valores nulos e duplicados do dataframe filtrado
        unique_values = filtered_df[column].dropna().unique()
        
        # Tratamento especial para Descrição Meta - truncar textos longos
        if column == 'Descrição Meta':
            # Limita o número de opções para evitar listas muito grandes
            max_options = 15
            # Trunca descrições longas para exibição no dropdown
            options = ["Todos"] + [f"{str(x)[:50]}..." if len(str(x)) > 50 else str(x) 
                                  for x in unique_values[:max_options] 
                                  if x not in [None, "", " "]]
        else:
            # Para outras colunas, mantém o comportamento normal
            options = ["Todos"] + sorted([str(x) for x in unique_values if x not in [None, "", " "]])
        
        return options
    except KeyError:
        st.error(f"Coluna '{column}' não encontrada na planilha")
        return ["Todos"]
    except Exception as e:
        st.error(f"Erro ao gerar opções para {column}: {str(e)}")
        return ["Todos"]

def create_dynamic_filters(df, filter_columns):
    """
    Cria os controles de filtro dinâmico e retorna os valores selecionados
    Filtros são interligados e afetam as opções uns dos outros
    """
    filters = {}
    col_objects = st.columns(len(filter_columns))

    # Inicializando o estado dos filtros se não existir
    if 'filter_state' not in st.session_state:
        st.session_state['filter_state'] = {col: "Todos" for col in filter_columns}
    
    # Função para atualizar o estado quando um filtro é alterado
    def on_filter_change(column):
        # Atualiza o valor no estado da sessão
        st.session_state['filter_state'][column] = st.session_state[f"filter_{column}"]
        # Reseta os filtros posteriores para evitar seleções inválidas
        for i, col in enumerate(filter_columns):
            if filter_columns.index(column) < i:
                st.session_state['filter_state'][col] = "Todos"
                st.session_state[f"filter_{col}"] = "Todos"
    
    # Cria os filtros em ordem
    for i, column in enumerate(filter_columns):
        with col_objects[i]:
            try:
                # Obtém as opções considerando os filtros anteriores
                previous_filters = {
                    col: st.session_state['filter_state'][col] 
                    for col in filter_columns[:i]
                    if st.session_state['filter_state'][col] != "Todos"
                }
                
                options = get_filter_options(df, column, previous_filters)
                
                # Se o valor atual não está nas opções, reseta para "Todos"
                current_value = st.session_state['filter_state'][column]
                if current_value not in options:
                    current_value = "Todos"
                    st.session_state['filter_state'][column] = "Todos"
                
                # Cria o selectbox com as opções filtradas
                filters[column] = st.selectbox(
                    f"Filtrar por {column}",
                    options=options,
                    key=f"filter_{column}",
                    on_change=lambda col=column: on_filter_change(col),
                    index=options.index(current_value) if current_value in options else 0
                )
            except KeyError:
                st.error(f"Coluna '{column}' não encontrada")
                filters[column] = "Todos"
    
    return filters

def apply_dynamic_filters(df, filters):
    """Aplica múltiplos filtros ao DataFrame de forma segura"""
    try:
        filtered_df = df.copy()
        for column, value in filters.items():
            if value != "Todos" and column in filtered_df.columns:
                if column == 'Descrição Meta':
                    # Para Descrição Meta, remove a parte "..." se estiver presente
                    search_value = str(value).replace("...", "")
                    # Usa busca por substring (contém) em vez de igualdade exata
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(search_value, case=False, na=False)]
                else:
                    # Para outros campos, mantém a comparação de igualdade exata
                    filtered_df = filtered_df[filtered_df[column].astype(str) == str(value)]
        return filtered_df
    except KeyError as e:
        st.error(f"Erro: Coluna '{e.args[0]}' não existe na planilha")
        return df
    except Exception as e:
        st.error(f"Erro ao filtrar dados: {str(e)}")
        return df

# ==================================================
# FUNÇÕES DOS MODAIS
# ==================================================
def show_edit_modal(row):
    """Modal de edição"""
    with st.expander(f"📝 Editando: {row['Referência']}", expanded=True):
        with st.form(f"edit_form_{row.name}"):
            # Campos editáveis (ajuste conforme suas colunas)
            col1, col2 = st.columns(2)
            with col1:
                referencia = st.text_input("Referência", value=row.get('Referência', ''))
                descricao = st.text_area("Descrição Meta", value=row.get('Descrição Meta', ''), height=150)
            with col2:
                responsavel = st.text_input("Responsável", value=row.get('Responsável', ''))
                status = st.selectbox(
                    "Status", 
                    options=["Em andamento", "Concluído", "Pendente"],
                    index=["Em andamento", "Concluído", "Pendente"].index(row.get('Status', 'Pendente'))
                )
            
            # Determina o número da linha na planilha (índice original + 2 para o cabeçalho)
            sheet_row = row.get('_original_index', 0) + 2
            
            if st.form_submit_button("💾 Salvar Alterações"):
                try:
                    # Recupera todas as colunas da planilha para manter a estrutura
                    cols_to_update = {
                        'Referência': referencia,
                        'Descrição Meta': descricao,
                        'Responsável': responsavel,
                        'Status': status
                    }
                    
                    # Atualiza a planilha
                    updated = update_row_in_sheet(
                        SPREADSHEET_URL,
                        WORKSHEET_DATA,
                        sheet_row,
                        cols_to_update
                    )
                    
                    if updated:
                        st.success("Registro atualizado com sucesso!")
                        # Limpa o cache para forçar recarregamento dos dados
                        st.cache_data.clear()
                        # Remove o estado de edição
                        if 'editing_row' in st.session_state:
                            del st.session_state['editing_row']
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar o registro.")
                except Exception as e:
                    st.error(f"Erro ao atualizar: {str(e)}")
            
            if st.button("❌ Cancelar"):
                if 'editing_row' in st.session_state:
                    del st.session_state['editing_row']
                st.rerun()

def show_delete_modal(row):
    """Modal de exclusão"""
    with st.expander(f"🗑️ Excluir: {row['Referência']}", expanded=True):
        st.warning("Tem certeza que deseja excluir este registro?")
        
        # Exibe um resumo dos dados para confirmação
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Referência:** {row.get('Referência', 'N/A')}")
            st.markdown(f"**Descrição:** {row.get('Descrição Meta', 'N/A')}")
        with col2:
            st.markdown(f"**Responsável:** {row.get('Responsável', 'N/A')}")
            st.markdown(f"**Status:** {row.get('Status', 'N/A')}")
        
        # Determina o número da linha na planilha
        sheet_row = row.get('_original_index', 0) + 2
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary"):
                try:
                    deleted = delete_row_in_sheet(
                        SPREADSHEET_URL,
                        WORKSHEET_DATA,
                        sheet_row
                    )
                    if deleted:
                        st.success("Registro excluído com sucesso!")
                        # Limpa o cache para forçar recarregamento dos dados
                        st.cache_data.clear()
                        if 'deleting_row' in st.session_state:
                            del st.session_state['deleting_row']
                        st.rerun()
                    else:
                        st.error("Erro ao excluir o registro.")
                except Exception as e:
                    st.error(f"Erro ao excluir: {str(e)}")
        
        with col2:
            if st.button("❌ Cancelar"):
                if 'deleting_row' in st.session_state:
                    del st.session_state['deleting_row']
                st.rerun()

def show_details_modal(row):
    """Modal de detalhes"""
    with st.expander(f"🔍 Detalhes: {row['Referência']}", expanded=True):
        # Exibe todos os dados disponíveis de forma formatada
        for col, val in row.items():
            # Ignora colunas internas e metadados
            if col != '_original_index':
                st.markdown(f"**{col}:** {val}")
        
        if st.button("⬅️ Voltar"):
            if 'viewing_row' in st.session_state:
                del st.session_state['viewing_row']
            st.rerun()

# ==================================================
# FUNÇÃO PRINCIPAL DO SISTEMA
# ==================================================
def show_main_app():
    """Conteúdo principal após login"""
    # Verificação de segurança
    if 'user' not in st.session_state:
        st.error("Sessão inválida. Redirecionando para login...")
        st.session_state.clear()
        st.rerun()
    
    user = st.session_state['user']
    is_admin = user.get('Tipo de Usuário') == "Administrador"
    user_email = None if is_admin else user.get('Email')
    
    # Barra superior com informações do usuário
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📅 Sistema de Cronograma")
    with col2:
        st.write(f"👤 **Usuário:** {user.get('Login')}")
        st.write(f"🔑 **Tipo:** {user.get('Tipo de Usuário')}")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()
    
    # Carrega dados
    df = load_data(user_email)
    
    if df is None:
        st.error("Erro ao carregar dados. Verifique sua conexão.")
        return
    
    if df.empty:
        st.warning("Nenhum dado encontrado na planilha.")
        return
    
    # Define colunas para filtros (substituindo Status por Descrição Meta)
    filter_columns = ['Referência', 'Setor', 'Responsável', 'Descrição Meta']
    
    # Seção de filtros
    st.header("Filtros Avançados", divider="rainbow")
    filters = create_dynamic_filters(df, filter_columns)
    
    # Aplica filtros
    filtered_df = apply_dynamic_filters(df, filters)
    
    # Exibe resultados
    st.header("Resultados", divider="rainbow")
    st.subheader(f"📊 Total de registros: {len(filtered_df)}")
    
    # Adicionar novo registro
    if st.button("➕ Adicionar Novo Registro"):
        st.session_state['adding_row'] = True
    
    # Modal para adicionar novo registro
    if st.session_state.get('adding_row', False):
        with st.expander("➕ Novo Registro", expanded=True):
            with st.form("add_form"):
                col1, col2 = st.columns(2)
                with col1:
                    referencia = st.text_input("Referência*")
                    descricao = st.text_area("Descrição Meta*", height=150)
                with col2:
                    responsavel = st.text_input("Responsável*")
                    status = st.selectbox(
                        "Status*", 
                        options=["Pendente", "Em andamento", "Concluído"],
                        index=0
                    )
                    
                if st.form_submit_button("💾 Salvar"):
                    if not all([referencia, descricao, responsavel]):
                        st.error("Preencha todos os campos obrigatórios!")
                    else:
                        try:
                            # Adiciona o novo registro como última linha
                            new_row = {
                                'Referência': referencia,
                                'Descrição Meta': descricao,
                                'Responsável': responsavel,
                                'Status': status,
                                'E-mail': user.get('Email', '')  # Associa o email do usuário
                            }
                            
                            # Cria uma função no módulo utils/google_sheets.py para adicionar linha
                            # Por enquanto, usamos update_row_in_sheet com índice -1 para adicionar na última linha
                            added = update_row_in_sheet(
                                SPREADSHEET_URL,
                                WORKSHEET_DATA,
                                -1,  # -1 indica para adicionar como última linha
                                new_row
                            )
                            
                            if added:
                                st.success("Registro adicionado com sucesso!")
                                st.cache_data.clear()
                                del st.session_state['adding_row']
                                st.rerun()
                            else:
                                st.error("Erro ao adicionar registro.")
                        except Exception as e:
                            st.error(f"Erro ao adicionar: {str(e)}")
                
                if st.button("❌ Cancelar"):
                    del st.session_state['adding_row']
                    st.rerun()
    
    # Exibe os resultados filtrados em cards
    if not filtered_df.empty:
        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                # Layout do card
                cols = st.columns([4, 1])
                
                # Coluna esquerda: Dados
                with cols[0]:
                    st.markdown(f"**Referência:** `{row.get('Referência', 'N/A')}`")
                    st.markdown(f"**Descrição:** {row.get('Descrição Meta', 'N/A')}")
                    st.markdown(f"**Responsável:** {row.get('Responsável', 'N/A')}")
                    st.markdown(f"**Status:** {row.get('Status', 'N/A')}")
                
                # Coluna direita: Botões de ação
                with cols[1]:
                    if st.button("📝 Editar", key=f"edit_{idx}"):
                        st.session_state['editing_row'] = row.to_dict()
                    
                    if st.button("🗑️ Excluir", key=f"delete_{idx}"):
                        st.session_state['deleting_row'] = row.to_dict()
                    
                    if st.button("🔍 Detalhes", key=f"details_{idx}"):
                        st.session_state['viewing_row'] = row.to_dict()
    else:
        st.warning("Nenhum registro corresponde aos filtros selecionados.")
    
    # Processa modais de ação
    if 'editing_row' in st.session_state:
        show_edit_modal(pd.Series(st.session_state['editing_row']))
    
    if 'deleting_row' in st.session_state:
        show_delete_modal(pd.Series(st.session_state['deleting_row']))
    
    if 'viewing_row' in st.session_state:
        show_details_modal(pd.Series(st.session_state['viewing_row']))

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
    if 'adding_row' not in st.session_state:
        st.session_state['adding_row'] = False
    
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
