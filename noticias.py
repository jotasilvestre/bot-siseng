# ============================================================
# SISENG BOT — Módulo de Notícias via RSS
# ============================================================

import httpx
import xml.etree.ElementTree as ET
from config import IDS_AUTORIZADOS

RSS_URL = "https://publicidadeimobiliaria.com/feed/"

# Estado em memória
_ids_enviados = set()
_inicializado = False


# ─── RSS ────────────────────────────────────────────────────

async def buscar_noticias():
    """Busca notícias via RSS do publicidadeimobiliaria.com"""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(RSS_URL, headers={
                "User-Agent": "Mozilla/5.0 SisEngBot/1.0"
            })

        if response.status_code != 200:
            print(f"⚠️ RSS erro HTTP {response.status_code}")
            return []

        root = ET.fromstring(response.text)
        channel = root.find("channel")
        if not channel:
            print("⚠️ RSS: channel não encontrado")
            return []

        noticias = []
        for item in channel.findall("item"):
            titulo = item.findtext("title", "").strip()
            link   = item.findtext("link",  "").strip()
            data   = item.findtext("pubDate", "").strip()
            desc   = item.findtext("description", "").strip()

            if not titulo or not link:
                continue

            # Remove tags HTML da descrição
            import re
            desc_limpa = re.sub(r'<[^>]+>', '', desc)[:200].strip()

            # Categoria
            categoria = ""
            cat_el = item.find("category")
            if cat_el is not None and cat_el.text:
                categoria = cat_el.text.strip()

            # ID único baseado no slug
            slug = link.strip("/").split("/")[-1] or link

            noticias.append({
                "id":        slug,
                "titulo":    titulo,
                "link":      link,
                "data":      data[:16],
                "categoria": categoria,
                "resumo":    desc_limpa
            })

        print(f"📰 RSS: {len(noticias)} notícias encontradas")
        return noticias

    except Exception as e:
        print(f"⚠️ Erro ao buscar RSS: {e}")
        return []


# ─── FORMATAÇÃO ─────────────────────────────────────────────

def formatar_noticia(n, index, total):
    cat  = f"🏷️ _{n['categoria']}_\n" if n.get("categoria") else ""
    data = f"📅 {n['data']}\n"        if n.get("data")      else ""
    res  = f"\n_{n['resumo']}..._"    if n.get("resumo")    else ""
    return (
        f"📰 *{index}/{total}*\n"
        f"{cat}"
        f"*{n['titulo']}*\n"
        f"{data}"
        f"{res}\n\n"
        f"🔗 {n['link']}"
    )


# ─── ENVIO ──────────────────────────────────────────────────

async def disparar_noticias(bot, periodo_label=""):
    global _inicializado, _ids_enviados

    noticias = await buscar_noticias()

    if not noticias:
        print("📰 Nenhuma notícia encontrada no RSS.")
        return

    if not _inicializado:
        _ids_enviados = {n["id"] for n in noticias}
        _inicializado = True
        print(f"📰 Estado inicial salvo: {len(_ids_enviados)} notícias conhecidas.")
        return

    novas = [n for n in noticias if n["id"] not in _ids_enviados]

    if not novas:
        print("📰 Nenhuma notícia nova.")
        return

    print(f"📰 {len(novas)} notícia(s) nova(s)!")

    for n in novas:
        _ids_enviados.add(n["id"])

    for chat_id in IDS_AUTORIZADOS:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🏠 *Notícias do Mercado Imobiliário*\n"
                    f"_{periodo_label}_ — {len(novas)} nova(s)"
                ),
                parse_mode="Markdown"
            )
            for i, n in enumerate(novas, 1):
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatar_noticia(n, i, len(novas)),
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
        except Exception as e:
            print(f"⚠️ Erro ao enviar para {chat_id}: {e}")
