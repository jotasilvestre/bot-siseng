# ============================================================
# SISENG BOT — Configurações via variáveis de ambiente
# ============================================================

import os

# Token do bot do Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# IDs autorizados a usar o bot
IDS_AUTORIZADOS = [
    27414363,   # Jota Silvestre (dono)
    8973744431, # Usuário autorizado
]

# Chat ID que receberá as notificações automáticas do monitor
CHAT_ID_NOTIFICACOES = 27414363

# ID da planilha do Google Sheets
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "16GrygdaIuxU2M3vS53rZW2sjLDVt0fo9-e78Nl38mZA")

# Caminho para o arquivo de credenciais do Google
CREDENTIALS_FILE = "credentials.json"

# Chave da API do Claude (Anthropic)
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# Modelo Claude
CLAUDE_MODEL = "claude-haiku-4-5"
