import os
import json
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd


def get_google_sheet_by_url(url):
    """Conecta ao Google Sheets usando a URL e retorna a planilha"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials/service_account.json', scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open_by_url(url)
        return sheet
    except Exception as e:
        print(f"Erro ao acessar a planilha: {e}")
        return None

def get_worksheet(url, worksheet_name):
    """Obtém uma aba específica da planilha"""
    sheet = get_google_sheet_by_url(url)
    if sheet:
        try:
            worksheet = sheet.worksheet(worksheet_name)
            return worksheet
        except:
            print(f"Aba '{worksheet_name}' não encontrada")
            return None
    return None


def read_sheet_to_dataframe(url, worksheet_name):
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        # Modificação importante: usar st.secrets em vez de os.environ
        creds_dict = dict(st.secrets["GOOGLE_CREDENTIALS"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(url)
        worksheet = sheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        return pd.DataFrame(records).fillna('')
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {str(e)}")
        return None

def write_dataframe_to_sheet(url, worksheet_name, dataframe):
    """Escreve um DataFrame em uma planilha"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        # Limpa a planilha existente
        worksheet.clear()
        
        # Adiciona cabeçalhos
        headers = dataframe.columns.tolist()
        worksheet.append_row(headers)
        
        # Adiciona dados
        for _, row in dataframe.iterrows():
            worksheet.append_row(row.tolist())
        return True
    return False

def append_row_to_sheet(url, worksheet_name, row_data):
    """Adiciona uma nova linha à planilha"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        worksheet.append_row(row_data)
        return True
    return False

def update_row_in_sheet(url, worksheet_name, row_index, new_values):
    """Atualiza uma linha específica na planilha"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        for col, value in enumerate(new_values, start=1):
            worksheet.update_cell(row_index, col, value)
        return True
    return False

# Adicione estas funções ao seu arquivo google_sheets.py

def get_user_by_login(url, worksheet_name, login):
    """Busca um usuário pelo login"""
    worksheet = get_worksheet(url, worksheet_name)
    if worksheet:
        records = worksheet.get_all_records()
        for record in records:
            if record['Login'].lower() == login.lower():
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
            user_data['Senha'],  # Na prática, você deve armazenar hash da senha
            user_data['Tipo de Usuário']
        ]
        worksheet.append_row(new_row)
        return True, "Usuário cadastrado com sucesso"
    return False, "Erro ao acessar a planilha"
