# ============================================================
# SISENG BOT — Conexão com Google Sheets + Cache em memória
# ============================================================

import gspread
import time
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_ID, CREDENTIALS_FILE

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Cache em memória: {nome_aba: (timestamp, dados)}
_cache = {}
CACHE_TTL = 300  # 5 minutos em segundos

def conectar():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    return cliente.open_by_key(SPREADSHEET_ID)

def ler_aba(nome_aba):
    """
    Retorna todos os registros de uma aba como lista de dicionários.
    Usa cache em memória por 5 minutos para evitar leituras repetidas.
    """
    agora = time.time()

    # Verifica cache
    if nome_aba in _cache:
        timestamp, dados = _cache[nome_aba]
        if agora - timestamp < CACHE_TTL:
            return dados

    # Busca dados frescos
    try:
        planilha = conectar()
        aba = planilha.worksheet(nome_aba)
        dados = aba.get_all_records()
        _cache[nome_aba] = (agora, dados)
        print(f"📊 Aba '{nome_aba}' carregada: {len(dados)} registros")
        return dados
    except Exception as e:
        print(f"⚠️ Erro ao ler aba '{nome_aba}': {e}")
        # Se der erro mas tiver cache antigo, usa ele
        if nome_aba in _cache:
            _, dados = _cache[nome_aba]
            return dados
        return []

def limpar_cache(nome_aba=None):
    """Limpa o cache de uma aba ou de todas."""
    if nome_aba:
        _cache.pop(nome_aba, None)
    else:
        _cache.clear()
