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

def read_sheet_to_dataframe(url, worksheet_name):
    """Lê dados da planilha para um DataFrame"""
    worksheet = get_worksheet(url, worksheet_name)
    return pd.DataFrame(worksheet.get_all_records()).fillna('') if worksheet else None

def get_user_by_login(url, worksheet_name, login):
    """Busca usuário pelo login"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        for record in worksheet.get_all_records():
            if str(record.get('Login', '')).lower() == login.lower():
                return record
    return None

def register_user(url, worksheet_name, user_data):
    """Cadastra novo usuário"""
    worksheet = get_worksheet(url, worksheet_name)
    if not worksheet:
        return False, "Planilha não encontrada"
    
    if get_user_by_login(url, worksheet_name, user_data['Login']):
        return False, "Usuário já existe"
    
    worksheet.append_row([
        user_data['Login'],
        user_data['Email'],
        user_data['Senha'],
        user_data['Tipo de Usuário']
    ])
    return True, "Usuário cadastrado com sucesso"
