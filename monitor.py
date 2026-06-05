# ============================================================
# SISENG BOT — Monitor de Atualizações (Temporizador 5 min)
# ============================================================

import json
import os
from datetime import datetime
from sheets import ler_aba

ESTADO_FILE = "estado_monitor.json"


# ─── ESTADO LOCAL ───────────────────────────────────────────

def carregar_estado():
    """Carrega o estado salvo do arquivo local."""
    if not os.path.exists(ESTADO_FILE):
        # Arquivo não existe = primeira execução
        return {"_primeira_execucao": True}
    try:
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"_primeira_execucao": True}

def salvar_estado(estado):
    """Salva o estado atual no arquivo local."""
    # Remove a flag de primeira execução antes de salvar
    estado.pop("_primeira_execucao", None)
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


# ─── DETECÇÃO DE NOVIDADES ──────────────────────────────────

def detectar_novos(aba, campo_id, estado, chave_estado, primeira_execucao):
    """
    Lê uma aba e retorna registros novos.
    Na primeira execução apenas salva o estado atual — sem notificar.
    """
    try:
        registros = ler_aba(aba)
    except Exception as e:
        print(f"⚠️ Erro ao ler aba {aba}: {e}")
        return [], estado

    ids_atuais = set(str(r.get(campo_id, "")).strip() for r in registros)

    if primeira_execucao:
        # Só salva o estado — não notifica nada
        estado[chave_estado] = list(ids_atuais)
        return [], estado

    ids_conhecidos = set(estado.get(chave_estado, []))
    novos_ids      = ids_atuais - ids_conhecidos
    novos          = [r for r in registros
                      if str(r.get(campo_id, "")).strip() in novos_ids]

    estado[chave_estado] = list(ids_atuais)
    return novos, estado

def detectar_mudancas_status(estado, primeira_execucao):
    """
    Detecta mudanças de status na aba Avaliacao.
    Na primeira execução apenas salva o mapa atual.
    """
    try:
        registros = ler_aba("Avaliacao")
    except Exception as e:
        print(f"⚠️ Erro ao ler aba Avaliacao: {e}")
        return [], estado

    mapa_atual = {
        str(r.get("IdAvaliacao", "")).strip(): str(r.get("Status", "")).strip()
        for r in registros
    }

    if primeira_execucao:
        estado["status_avaliacao"] = mapa_atual
        return [], estado

    mapa_anterior = estado.get("status_avaliacao", {})
    mudancas = []

    for id_av, status_atual in mapa_atual.items():
        status_anterior = mapa_anterior.get(id_av)
        if status_anterior is None:
            continue
        if status_atual != status_anterior:
            reg = next(
                (r for r in registros
                 if str(r.get("IdAvaliacao","")).strip() == id_av),
                {}
            )
            mudancas.append({
                "id":       id_av,
                "anterior": status_anterior,
                "atual":    status_atual,
                "registro": reg
            })

    estado["status_avaliacao"] = mapa_atual
    return mudancas, estado


# ─── FORMATAÇÃO DAS NOTIFICAÇÕES ────────────────────────────

def formatar_notif_cliente(r):
    nome    = str(r.get("Nome", "—")).strip()
    vinculo = str(r.get("TipoVinculo", "—")).strip()
    loja    = str(r.get("Loja", "—")).strip()
    id_c    = str(r.get("IdCliente", "—")).strip()
    return (
        f"🔔 *Novo Cliente Cadastrado*\n\n"
        f"👤 {nome}\n"
        f"🔗 Vínculo: {vinculo}\n"
        f"🏢 Loja: {loja}\n"
        f"🆔 ID: `{id_c}`\n\n"
        f"Use /cliente `{id_c}` para ver detalhes."
    )

def formatar_notif_transacao(r):
    tipo  = str(r.get("Tipo", "—")).strip()
    valor = r.get("ValorTransacao", "")
    loja  = str(r.get("Loja", "—")).strip()
    id_t  = str(r.get("IdTransacao", "—")).strip()
    data  = str(r.get("DataAssinatura", "—")).strip()
    try:
        valor_fmt = f"R$ {float(str(valor).replace(',','.')):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except Exception:
        valor_fmt = str(valor)
    return (
        f"🔔 *Nova Transação Registrada*\n\n"
        f"📝 Tipo: {tipo}\n"
        f"💰 Valor: {valor_fmt}\n"
        f"📅 Assinatura: {data}\n"
        f"🏢 Loja: {loja}\n"
        f"🆔 ID: `{id_t}`\n\n"
        f"Use /transacao `{id_t}` para ver detalhes."
    )

def formatar_notif_imovel(r):
    endereco = str(r.get("Endereco", "—")).strip()
    tipo     = str(r.get("TipoOferta", "—")).strip()
    id_i     = str(r.get("IdImovel", "—")).strip()
    return (
        f"🔔 *Novo Imóvel Cadastrado*\n\n"
        f"🏠 {endereco}\n"
        f"📦 Oferta: {tipo}\n"
        f"🆔 ID: `{id_i}`\n\n"
        f"Use /imovel `{id_i}` para ver detalhes."
    )

def formatar_notif_status_avaliacao(m):
    return (
        f"🔔 *Mudança de Status — Avaliação*\n\n"
        f"🆔 ID: `{m['id']}`\n"
        f"📊 Anterior: {m['anterior']}\n"
        f"✅ Atual: *{m['atual']}*"
    )


# ─── FUNÇÃO PRINCIPAL DO MONITOR ────────────────────────────

async def verificar_atualizacoes(bot, chat_id):
    agora = datetime.now().strftime("%H:%M:%S")

    estado = carregar_estado()
    primeira_execucao = estado.get("_primeira_execucao", False)

    if primeira_execucao:
        print(f"🔍 [{agora}] Primeira execução — salvando estado inicial...")
    else:
        print(f"🔍 [{agora}] Verificando atualizações na planilha...")

    notificacoes = []

    # 1. Novos clientes
    novos_clientes, estado = detectar_novos(
        "Cliente", "IdCliente", estado, "ids_clientes", primeira_execucao
    )
    for r in novos_clientes:
        notificacoes.append(formatar_notif_cliente(r))

    # 2. Novas transações
    novas_transacoes, estado = detectar_novos(
        "Transacao", "IdTransacao", estado, "ids_transacoes", primeira_execucao
    )
    for r in novas_transacoes:
        notificacoes.append(formatar_notif_transacao(r))

    # 3. Novos imóveis
    novos_imoveis, estado = detectar_novos(
        "Imovel", "IdImovel", estado, "ids_imoveis", primeira_execucao
    )
    for r in novos_imoveis:
        notificacoes.append(formatar_notif_imovel(r))

    # 4. Mudanças de status em avaliações
    mudancas, estado = detectar_mudancas_status(estado, primeira_execucao)
    for m in mudancas:
        notificacoes.append(formatar_notif_status_avaliacao(m))

    salvar_estado(estado)

    if primeira_execucao:
        print(f"✅ Estado inicial salvo. Monitoramento ativo a partir de agora!")
        return

    if notificacoes:
        print(f"✅ {len(notificacoes)} notificação(ões) encontrada(s).")
        for texto in notificacoes:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=texto,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"⚠️ Erro ao enviar notificação: {e}")
    else:
        print(f"✅ Nenhuma novidade encontrada.")
