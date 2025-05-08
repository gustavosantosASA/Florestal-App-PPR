import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def get_google_sheet_by_url(url):
    """Conecta ao Google Sheets usando a URL"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        # Usa as credenciais do st.secrets
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
        if sheet:
            worksheet = sheet.worksheet(worksheet_name)
            return worksheet
        return None
    except Exception as e:
        st.error(f"Erro ao acessar aba {worksheet_name}: {str(e)}")
        return None

def read_sheet_to_dataframe(url, worksheet_name):
    """Lê uma planilha e retorna um DataFrame"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        records = worksheet.get_all_records()
        return pd.DataFrame(records).fillna('')
    return None

def get_user_by_login(url, worksheet_name, login):
    """Busca um usuário pelo login"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        records = worksheet.get_all_records()
        for record in records:
            if str(record.get('Login', '')).lower() == login.lower():
                return record
    return None

def register_user(url, worksheet_name, user_data):
    """Registra um novo usuário"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        # Verifica se usuário já existe
        existing_user = get_user_by_login(url, worksheet_name, user_data['Login'])
        if existing_user:
            return False, "Usuário já existe"
        
        # Adiciona novo usuário
        new_row = [
            user_data['Login'],
            user_data['Email'],
            user_data['Senha'],
            user_data['Tipo de Usuário']
        ]
        worksheet.append_row(new_row)
        return True, "Usuário cadastrado com sucesso"
    return False, "Erro ao acessar a planilha"
