import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def get_google_sheet_by_url(url):
    """Conecta ao Google Sheets usando as credenciais do Streamlit secrets"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        creds_dict = dict(st.secrets["GOOGLE_CREDENTIALS"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_url(url)
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {str(e)}")
        return None

def get_worksheet(url, worksheet_name):
    """Obtém uma aba específica da planilha"""
    try:
        sheet = get_google_sheet_by_url(url)
        return sheet.worksheet(worksheet_name) if sheet else None
    except Exception as e:
        st.error(f"Erro ao acessar aba {worksheet_name}: {str(e)}")
        return None

def read_sheet_to_dataframe(url, worksheet_name, user_email=None):
    """Lê uma planilha e retorna um DataFrame, opcionalmente filtrado por e-mail"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        try:
            # Obter todos os registros
            records = worksheet.get_all_records()
            df = pd.DataFrame(records).fillna('')
            
            # Filtrar pelo e-mail se fornecido
            if user_email and 'E-mail' in df.columns:
                df = df[df['E-mail'].str.lower() == user_email.lower()]
            
            return df
        except Exception as e:
            st.error(f"Erro ao processar dados: {str(e)}")
            return pd.DataFrame()
    return None

def get_user_by_login(url, worksheet_name, login):
    """Busca usuário pelo login"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        try:
            for record in worksheet.get_all_records():
                if record and 'Login' in record and str(record.get('Login', '')).lower() == login.lower():
                    return record
        except Exception as e:
            st.error(f"Erro ao buscar usuário: {str(e)}")
    return None

def register_user(url, worksheet_name, user_data):
    """Cadastra novo usuário"""
    worksheet = get_worksheet(url, worksheet_name)
    if not worksheet:
        return False, "Planilha não encontrada"
    
    try:
        # Verifica se o usuário já existe
        if get_user_by_login(url, worksheet_name, user_data['Login']):
            return False, "Usuário já existe"
        
        # Obtém os cabeçalhos da planilha
        headers = worksheet.row_values(1)
        
        # Prepara os dados de acordo com os cabeçalhos
        row_data = []
        for header in headers:
            row_data.append(user_data.get(header, ''))
        
        # Adiciona o novo usuário
        worksheet.append_row(row_data)
        return True, "Usuário cadastrado com sucesso"
    except Exception as e:
        return False, f"Erro ao cadastrar usuário: {str(e)}"

def update_row_in_sheet(url, worksheet_name, row_num, updated_values):
    """
    Atualiza ou adiciona uma linha específica
    
    Args:
        url: URL da planilha
        worksheet_name: Nome da aba
        row_num: Número da linha a atualizar (2+ para linhas existentes, -1 para adicionar nova)
        updated_values: Dicionário com valores a atualizar ou dict/list para nova linha
    """
    worksheet = get_worksheet(url, worksheet_name)
    if not worksheet:
        return False
    
    try:
        # Obtém os cabeçalhos da planilha
        headers = worksheet.row_values(1)
        
        if row_num == -1:
            # Adicionar nova linha
            row_data = []
            
            # Se os dados são um dicionário, organizamos pelos cabeçalhos
            if isinstance(updated_values, dict):
                for header in headers:
                    row_data.append(updated_values.get(header, ''))
            # Se é uma lista, usamos diretamente
            elif isinstance(updated_values, list):
                row_data = updated_values
            
            worksheet.append_row(row_data)
            return True
        else:
            # Atualizar linha existente
            if isinstance(updated_values, dict):
                # Para cada cabeçalho, atualiza o valor correspondente
                for i, header in enumerate(headers, start=1):
                    if header in updated_values:
                        worksheet.update_cell(row_num, i, updated_values[header])
            elif isinstance(updated_values, list):
                # Atualiza cada coluna com os valores da lista
                for i, value in enumerate(updated_values, start=1):
                    worksheet.update_cell(row_num, i, value)
            
            return True
    except Exception as e:
        st.error(f"Erro ao atualizar/adicionar linha: {str(e)}")
        return False

def delete_row_in_sheet(url, worksheet_name, row_num):
    """Remove uma linha específica"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        try:
            worksheet.delete_rows(row_num)
            return True
        except Exception as e:
            st.error(f"Erro ao excluir linha: {str(e)}")
    return False

def apply_filters(df, filters):
    """Aplica múltiplos filtros ao DataFrame"""
    try:
        filtered_df = df.copy()
        for col, value in filters.items():
            if value != "Todos" and col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[col].astype(str) == str(value)]
        return filtered_df
    except KeyError as e:
        st.error(f"Coluna '{e.args[0]}' não encontrada para filtro")
        return df
    except Exception as e:
        st.error(f"Erro ao aplicar filtros: {str(e)}")
        return df

def validate_dataframe(df):
    """Verifica se o DataFrame é válido para filtragem"""
    if df is None:
        st.error("Dados não carregados corretamente")
        return False
    if df.empty:
        st.warning("A planilha está vazia")
        return False
    return True
