# ============================================================
# SISENG BOT — Bot Principal com Gemini IA
# ============================================================

import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config import TELEGRAM_TOKEN, IDS_AUTORIZADOS, CHAT_ID_NOTIFICACOES
from consultas import (
    buscar_cliente, formatar_cliente, historico_cliente,
    buscar_imovel, formatar_imovel,
    buscar_transacao, formatar_transacao,
    buscar_parceiro, formatar_parceiro,
    listar_parceiros_por_funcao,
    resumo_geral,
    resumo_periodo,
    resumo_por_corretor,
    resumo_por_funcao,
    FUNCOES_DISPONIVEIS
)
from monitor import verificar_atualizacoes
from claude_ai import interpretar_mensagem
from noticias import disparar_noticias


# ─── CONTROLE DE ACESSO ─────────────────────────────────────

def autorizado(update: Update) -> bool:
    return update.effective_user.id in IDS_AUTORIZADOS

async def acesso_negado(update: Update):
    await update.message.reply_text(
        "⛔ Acesso não autorizado.\n"
        "Entre em contato com o administrador do SisEng."
    )


# ─── TEMPORIZADOR asyncio ───────────────────────────────────

def fuso_brasilia():
    """Retorna hora atual no fuso de Brasília (UTC-4)."""
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=-4)))

async def loop_monitor(bot):
    """Monitor de planilha — roda a cada 5 minutos."""
    await asyncio.sleep(10)
    while True:
        try:
            await verificar_atualizacoes(bot, CHAT_ID_NOTIFICACOES)
        except Exception as e:
            print(f"⚠️ Erro no monitor: {e}")
        await asyncio.sleep(300)

async def loop_noticias(bot):
    """Monitor de notícias — dispara às 9h, 12h e 19h (Brasília)."""
    from datetime import datetime, timezone, timedelta

    HORARIOS = [9, 12, 19]
    ultimo_disparo = None

    # Inicializa o estado sem enviar
    await disparar_noticias(bot, "Inicializando...")

    while True:
        await asyncio.sleep(60)  # verifica a cada 1 minuto

        agora = datetime.now(timezone(timedelta(hours=-4)))
        hora_atual = agora.hour
        data_atual = agora.date()

        # Verifica se é um dos horários de disparo e ainda não disparou hoje nesse horário
        chave = (data_atual, hora_atual)

        if hora_atual in HORARIOS and chave != ultimo_disparo:
            periodo_label = {
                9:  "Notícias da manhã (desde 19h de ontem)",
                12: "Notícias do meio-dia (desde 9h)",
                19: "Notícias da tarde (desde 12h)"
            }.get(hora_atual, "Notícias recentes")

            print(f"📰 Disparando notícias das {hora_atual}h...")
            try:
                await disparar_noticias(bot, periodo_label)
                ultimo_disparo = chave
            except Exception as e:
                print(f"⚠️ Erro no disparo de notícias: {e}")


# ─── EXECUTOR DE COMANDOS (chamado pela IA) ─────────────────

async def executar_comando_ia(comando: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recebe um comando retornado pelo Gemini e executa a ação correspondente.
    Ex: "/cliente João Silva" → busca cliente
    """
    partes = comando.strip().split(" ", 1)
    cmd    = partes[0].lower()
    args   = partes[1].strip() if len(partes) > 1 else ""

    if cmd == "/cliente":
        if not args:
            await update.message.reply_text("ℹ️ Qual o nome ou ID do cliente?")
            return
        await update.message.reply_text(f"🔍 Buscando: *{args}*...", parse_mode="Markdown")
        resultados = buscar_cliente(args)
        if not resultados:
            await update.message.reply_text("❌ Nenhum cliente encontrado.")
            return
        for r in resultados[:5]:
            await update.message.reply_text(formatar_cliente(r), parse_mode="Markdown")
        if len(resultados) > 5:
            await update.message.reply_text(f"📋 {len(resultados)} encontrados. Mostrando os 5 primeiros.")

    elif cmd == "/historico":
        if not args:
            await update.message.reply_text("ℹ️ Informe o ID do cliente.")
            return
        await update.message.reply_text(f"🔍 Buscando jornada de `{args}`...", parse_mode="Markdown")
        await update.message.reply_text(historico_cliente(args), parse_mode="Markdown")

    elif cmd == "/imovel":
        if not args:
            await update.message.reply_text("ℹ️ Qual o endereço ou ID do imóvel?")
            return
        await update.message.reply_text(f"🔍 Buscando: *{args}*...", parse_mode="Markdown")
        resultados = buscar_imovel(args)
        if not resultados:
            await update.message.reply_text("❌ Nenhum imóvel encontrado.")
            return
        for r in resultados[:5]:
            await update.message.reply_text(formatar_imovel(r), parse_mode="Markdown")

    elif cmd == "/transacao":
        if not args:
            await update.message.reply_text("ℹ️ Informe o ID ou nome da transação.")
            return
        await update.message.reply_text(f"🔍 Buscando: *{args}*...", parse_mode="Markdown")
        resultados = buscar_transacao(args)
        if not resultados:
            await update.message.reply_text("❌ Nenhuma transação encontrada.")
            return
        for r in resultados[:5]:
            await update.message.reply_text(formatar_transacao(r), parse_mode="Markdown")

    elif cmd == "/parceiro":
        if not args:
            await update.message.reply_text("ℹ️ Qual o nome ou ID do parceiro?")
            return
        resultados = buscar_parceiro(args)
        if not resultados:
            await update.message.reply_text("❌ Nenhum parceiro encontrado.")
            return
        for r in resultados[:5]:
            await update.message.reply_text(formatar_parceiro(r), parse_mode="Markdown")

    elif cmd == "/parceiros":
        funcao = args if args else "internos"
        resultados = listar_parceiros_por_funcao(funcao)
        if not resultados:
            await update.message.reply_text(f"❌ Nenhum parceiro com função *{funcao}*.", parse_mode="Markdown")
            return
        await update.message.reply_text(f"🤝 *{len(resultados)} parceiro(s) — {funcao}:*", parse_mode="Markdown")
        for r in resultados:
            await update.message.reply_text(formatar_parceiro(r), parse_mode="Markdown")

    elif cmd == "/resumo":
        await update.message.reply_text("📊 Carregando resumo...")
        await update.message.reply_text(resumo_geral(), parse_mode="Markdown")

    else:
        # Não é um comando — é uma resposta conversacional do Gemini
        await update.message.reply_text(comando)


# ─── COMANDOS DIRETOS ───────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        await acesso_negado(update)
        return
    nome = update.effective_user.first_name
    await update.message.reply_text(
        f"Olá, {nome}! 👋\n\n"
        f"Sou o assistente inteligente do *SisEng*.\n\n"
        f"Pode me falar naturalmente, como:\n"
        f"_\"Me mostra o cliente João\"_\n"
        f"_\"Quais imóveis temos em Porto Velho?\"_\n"
        f"_\"Me traz os corretores\"_\n\n"
        f"📌 *Ou use os comandos diretos:*\n\n"
        f"/cliente — busca um cliente\n"
        f"/historico — jornada completa do cliente\n"
        f"/imovel — busca um imóvel\n"
        f"/transacao — consulta uma transação\n"
        f"/parceiro — busca um parceiro\n"
        f"/parceiros — lista por função\n"
        f"/resumo — resumo geral\n"
        f"/ajuda — mostra esta mensagem",
        parse_mode="Markdown"
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def cmd_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text("ℹ️ Use: `/cliente João Silva`", parse_mode="Markdown"); return
    termo = " ".join(context.args)
    await update.message.reply_text(f"🔍 Buscando: *{termo}*...", parse_mode="Markdown")
    resultados = buscar_cliente(termo)
    if not resultados:
        await update.message.reply_text("❌ Nenhum cliente encontrado."); return
    for r in resultados[:5]:
        await update.message.reply_text(formatar_cliente(r), parse_mode="Markdown")
    if len(resultados) > 5:
        await update.message.reply_text(f"📋 {len(resultados)} encontrados. Mostrando os 5 primeiros.")

async def cmd_historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Use:\n`/historico João Silva` — busca pelo nome\n`/historico João mes` — este mês",
            parse_mode="Markdown"); return
    periodos = ["hoje", "semana", "mes", "ano"]
    if len(context.args) > 1 and context.args[-1].lower() in periodos:
        periodo = context.args[-1].lower()
        termo = " ".join(context.args[:-1])
    else:
        periodo = None
        termo = " ".join(context.args)
    await update.message.reply_text(f"🔍 Buscando cliente: *{termo}*...", parse_mode="Markdown")
    resultados = buscar_cliente(termo)
    if not resultados:
        await update.message.reply_text("❌ Nenhum cliente encontrado."); return
    if len(resultados) > 1:
        nomes = "\n".join([f"  • *{r.get('Nome','—')}* — `{r.get('IdCliente','')}`" for r in resultados[:5]])
        await update.message.reply_text(
            f"📋 Encontrei {len(resultados)} clientes. Use o ID para ser específico:\n{nomes}",
            parse_mode="Markdown"); return
    id_cliente = str(resultados[0].get("IdCliente","")).strip()
    await update.message.reply_text(historico_cliente(id_cliente, periodo), parse_mode="Markdown")

async def cmd_imovel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text("ℹ️ Use: `/imovel Rua das Flores`", parse_mode="Markdown"); return
    termo = " ".join(context.args)
    await update.message.reply_text(f"🔍 Buscando: *{termo}*...", parse_mode="Markdown")
    resultados = buscar_imovel(termo)
    if not resultados:
        await update.message.reply_text("❌ Nenhum imóvel encontrado."); return
    for r in resultados[:5]:
        await update.message.reply_text(formatar_imovel(r), parse_mode="Markdown")
    if len(resultados) > 5:
        await update.message.reply_text(f"📋 {len(resultados)} encontrados. Mostrando os 5 primeiros.")

async def cmd_transacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text("ℹ️ Use: `/transacao João`", parse_mode="Markdown"); return
    termo = " ".join(context.args)
    await update.message.reply_text(f"🔍 Buscando: *{termo}*...", parse_mode="Markdown")
    resultados = buscar_transacao(termo)
    if not resultados:
        await update.message.reply_text("❌ Nenhuma transação encontrada."); return
    for r in resultados[:5]:
        await update.message.reply_text(formatar_transacao(r), parse_mode="Markdown")
    if len(resultados) > 5:
        await update.message.reply_text(f"📋 {len(resultados)} encontradas. Mostrando as 5 primeiras.")

async def cmd_parceiro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text("ℹ️ Use: `/parceiro João`", parse_mode="Markdown"); return
    termo = " ".join(context.args)
    resultados = buscar_parceiro(termo)
    if not resultados:
        await update.message.reply_text("❌ Nenhum parceiro encontrado."); return
    for r in resultados[:5]:
        await update.message.reply_text(formatar_parceiro(r), parse_mode="Markdown")

async def cmd_parceiros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        funcoes_fmt = "\n".join([f"  • `{f}`" for f in FUNCOES_DISPONIVEIS])
        await update.message.reply_text(
            f"ℹ️ Informe a função:\n`/parceiros Corretor`\n`/parceiros internos`\n\n*Funções:*\n{funcoes_fmt}",
            parse_mode="Markdown"); return
    funcao = " ".join(context.args)
    resultados = listar_parceiros_por_funcao(funcao)
    if not resultados:
        await update.message.reply_text(f"❌ Nenhum parceiro com função *{funcao}*.", parse_mode="Markdown"); return
    await update.message.reply_text(f"🤝 *{len(resultados)} parceiro(s) — {funcao}:*", parse_mode="Markdown")
    for r in resultados:
        await update.message.reply_text(formatar_parceiro(r), parse_mode="Markdown")

async def cmd_resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    periodo = context.args[0].lower() if context.args else None
    periodos_validos = ["hoje", "semana", "mes", "ano"]
    if periodo and periodo not in periodos_validos:
        await update.message.reply_text(
            "ℹ️ Períodos disponíveis:\n"
            "`/resumo` — geral\n"
            "`/resumo hoje` — hoje\n"
            "`/resumo semana` — esta semana\n"
            "`/resumo mes` — este mês\n"
            "`/resumo ano` — este ano",
            parse_mode="Markdown"
        )
        return
    await update.message.reply_text("📊 Carregando resumo...")
    await update.message.reply_text(resumo_periodo(periodo), parse_mode="Markdown")



async def cmd_corretor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Use assim:\n"
            "`/corretor João` — todos os tempos\n"
            "`/corretor João mes` — este mês\n"
            "`/corretor João hoje` — hoje",
            parse_mode="Markdown"
        )
        return
    periodos = ["hoje", "semana", "mes", "ano"]
    if len(context.args) > 1 and context.args[-1].lower() in periodos:
        periodo = context.args[-1].lower()
        termo = " ".join(context.args[:-1])
    else:
        periodo = None
        termo = " ".join(context.args)
    await update.message.reply_text(f"📊 Carregando resumo do corretor *{termo}*...", parse_mode="Markdown")
    await update.message.reply_text(resumo_por_corretor(termo, periodo), parse_mode="Markdown")

async def cmd_funcao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await acesso_negado(update); return
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Use assim:\n"
            "`/funcao Corretor` — todos os tempos\n"
            "`/funcao Corretor mes` — este mês\n"
            "`/funcao internos` — equipe interna",
            parse_mode="Markdown"
        )
        return
    periodos = ["hoje", "semana", "mes", "ano"]
    if len(context.args) > 1 and context.args[-1].lower() in periodos:
        periodo = context.args[-1].lower()
        funcao = " ".join(context.args[:-1])
    else:
        periodo = None
        funcao = " ".join(context.args)
    await update.message.reply_text(f"📊 Carregando resumo por função *{funcao}*...", parse_mode="Markdown")
    await update.message.reply_text(resumo_por_funcao(funcao, periodo), parse_mode="Markdown")
# ─── MENSAGEM DE TEXTO LIVRE (GEMINI) ───────────────────────

async def mensagem_livre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        await acesso_negado(update)
        return

    texto = update.message.text.strip()
    nome  = update.effective_user.first_name or ""

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    resposta = await interpretar_mensagem(texto, nome)

    if resposta.startswith("⚠️"):
        await update.message.reply_text(
            f"{resposta}\n\n📌 *Comandos disponíveis:*\n"
            f"/cliente, /imovel, /transacao, /parceiro, /resumo",
            parse_mode="Markdown"
        )
        return

    if resposta.startswith("/"):
        await executar_comando_ia(resposta, update, context)
    else:
        await update.message.reply_text(resposta, parse_mode="Markdown")


# ─── TESTE DE NOTÍCIAS ──────────────────────────────────────

async def cmd_testenoticias(update, context):
    if not autorizado(update): await acesso_negado(update); return
    await update.message.reply_text("📰 Buscando notícias do site...")
    try:
        from noticias import buscar_noticias, formatar_noticia
        noticias = await buscar_noticias()
        if not noticias:
            await update.message.reply_text("❌ Nenhuma notícia encontrada.")
            return
        from noticias import IMAGEM_NOTICIAS
        total = len(noticias)
        caption = f"Noticias do Mercado Imobiliario - Teste - {total} encontrada(s)"
        try:
            with open(IMAGEM_NOTICIAS, "rb") as img:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=img,
                    caption=caption
                )
        except Exception:
            await update.message.reply_text(caption)
        for i, n in enumerate(noticias[:3], 1):
            await update.message.reply_text(
                formatar_noticia(n, i, total),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")


# ─── INICIALIZAÇÃO ──────────────────────────────────────────

async def main():
    print("🚀 SisEng Bot iniciando com Gemini IA...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("ajuda",     ajuda))
    app.add_handler(CommandHandler("cliente",   cmd_cliente))
    app.add_handler(CommandHandler("historico", cmd_historico))
    app.add_handler(CommandHandler("imovel",    cmd_imovel))
    app.add_handler(CommandHandler("transacao", cmd_transacao))
    app.add_handler(CommandHandler("parceiro",  cmd_parceiro))
    app.add_handler(CommandHandler("parceiros", cmd_parceiros))
    app.add_handler(CommandHandler("resumo",    cmd_resumo))
    app.add_handler(CommandHandler("corretor",  cmd_corretor))
    app.add_handler(CommandHandler("funcao",    cmd_funcao))
    app.add_handler(CommandHandler("testenoticias", cmd_testenoticias))

    # Todas as mensagens de texto vão para o Gemini
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_livre))

    await app.initialize()
    await app.start()

    # Limpa webhook e conflitos pendentes antes de iniciar polling
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.updater.start_polling(drop_pending_updates=True)

    print("✅ Bot rodando com Gemini IA + monitor ativo!")
    print(f"📡 Notificações → chat: {CHAT_ID_NOTIFICACOES}")

    try:
        await asyncio.gather(
            loop_monitor(app.bot),
            loop_noticias(app.bot)
        )
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
