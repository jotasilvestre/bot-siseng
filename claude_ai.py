# ============================================================
# SISENG BOT — Módulo Claude IA (Anthropic)
# ============================================================

import httpx
from config import CLAUDE_API_KEY, CLAUDE_MODEL

SYSTEM_PROMPT = """Você é o assistente inteligente do SisEng, sistema de gestão da imobiliária 
JV Serviços de Engenharia, Consultoria e Negócios Imobiliários Ltda, parceira RE/MAX, 
localizada em Porto Velho e Jaru, Rondônia, Brasil.

Você pode responder de duas formas:

1. CONVERSA — quando o usuário cumprimentar, agradecer, perguntar algo geral sobre 
   mercado imobiliário, taxas de juros, financiamento, FGTS, Minha Casa Minha Vida, 
   Lei do Inquilinato, CRECI, COFECI, mercado de Rondônia, dicas para corretores, etc.
   Responda de forma natural, simpática e profissional em português brasileiro.

2. COMANDO — quando o usuário pedir informações do sistema SisEng, retorne EXATAMENTE 
   um dos comandos abaixo (sem nenhum texto extra, só o comando):
   - /cliente [nome ou ID]
   - /historico [ID]
   - /imovel [endereço ou ID]
   - /transacao [ID ou nome]
   - /parceiro [nome ou ID]
   - /parceiros [função]
   - /resumo

Exemplos de intenção → comando:
- "me mostra o João Silva" → /cliente João Silva
- "quero ver o cliente Fabrício" → /cliente Fabrício  
- "me mostra o fabricio" → /cliente fabricio
- "qual o status da avaliação do Pedro?" → /cliente Pedro
- "me traz os corretores" → /parceiros Corretor
- "quais corretores temos?" → /parceiros Corretor
- "lista os parceiros administrativos" → /parceiros Administrativo
- "equipe interna" → /parceiros internos
- "ver transação ab12cd34" → /transacao ab12cd34
- "mostra o resumo do sistema" → /resumo
- "tem imóvel na Rua das Flores?" → /imovel Rua das Flores
- "jornada do cliente e6c1183f" → /historico e6c1183f

Para saudações e conversa geral:
- "oi", "olá", "bom dia", "boa tarde", "boa noite" → responda com saudação simpática
- "obrigado", "valeu", "thanks" → agradeça de volta
- "tudo bem?", "como vai?" → responda naturalmente

Para perguntas sobre mercado imobiliário, responda com seu conhecimento:
- Taxas Selic, IPCA, financiamento CEF, BB, Bradesco, Itaú
- Minha Casa Minha Vida, FGTS, crédito imobiliário
- Legislação: Lei do Inquilinato (Lei 8.245/91), CRECI-RO, COFECI
- Mercado imobiliário de Porto Velho e Rondônia
- Dicas operacionais para corretores

IMPORTANTE: 
- Nunca invente dados do sistema — só retorne o comando para buscar
- Se não tiver certeza se é um comando ou conversa, prefira responder conversacionalmente
- Seja sempre objetivo, profissional e simpático
- Responda sempre em português brasileiro"""


async def interpretar_mensagem(texto_usuario: str, nome_usuario: str = "") -> str:
    """
    Envia a mensagem do usuário para o Claude e retorna:
    - Um comando (/cliente João) para ser executado pelo bot
    - Ou uma resposta conversacional direta
    """
    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    contexto = f"O usuário se chama {nome_usuario}. " if nome_usuario else ""

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 256,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"{contexto}Mensagem: {texto_usuario}"
            }
        ]
    }

    try:
        print(f"🤖 Claude recebendo: '{texto_usuario}'")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=headers)

        print(f"🤖 Claude status: {response.status_code}")

        if response.status_code != 200:
            print(f"🤖 Claude erro: {response.text[:300]}")
            return "⚠️ Serviço de IA indisponível. Use /ajuda para ver os comandos."

        data = response.json()
        resposta = data.get("content", [{}])[0].get("text", "").strip()

        print(f"🤖 Claude resposta: '{resposta[:100]}'")

        if not resposta:
            return "⚠️ Não entendi. Use /ajuda para ver os comandos disponíveis."

        return resposta

    except Exception as e:
        print(f"🤖 Claude exceção: {e}")
        return "⚠️ Serviço de IA indisponível. Use /ajuda para ver os comandos."
