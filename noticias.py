# ============================================================
# SISENG BOT — Módulo de Notícias via RSS (com fallback)
# ============================================================

import httpx
import xml.etree.ElementTree as ET
import re
from config import IDS_AUTORIZADOS

# Usa o RSS2JSON como proxy — converte RSS em JSON sem bloqueio de IP
RSS_URLS = [
    "https://api.rss2json.com/v1/api.json?rss_url=https://publicidadeimobiliaria.com/feed/",
    "https://api.rss2json.com/v1/api.json?rss_url=https://publicidadeimobiliaria.com/?feed=rss2",
]

_ids_enviados = set()
_inicializado = False


async def buscar_noticias():
    """Busca notícias via RSS2JSON (proxy gratuito)."""
    for url in RSS_URLS:
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url)

            if response.status_code != 200:
                print(f"📰 RSS2JSON erro: {response.status_code}")
                continue

            data = response.json()
            status = data.get("status", "")
            print(f"📰 RSS2JSON status: {status}")

            if status != "ok":
                print(f"📰 RSS2JSON falhou: {data.get('message','')}")
                continue

            items = data.get("items", [])
            noticias = []

            for item in items:
                titulo = item.get("title", "").strip()
                link   = item.get("link",  "").strip()
                data_pub = item.get("pubDate", "")[:10]
                desc   = item.get("description", "")
                categoria = item.get("categories", [""])[0] if item.get("categories") else ""

                if not titulo or not link:
                    continue

                desc_limpa = re.sub(r'<[^>]+>', '', desc)[:200].strip()
                slug = link.strip("/").split("/")[-1] or link

                noticias.append({
                    "id":        slug,
                    "titulo":    titulo,
                    "link":      link,
                    "data":      data_pub,
                    "categoria": categoria,
                    "resumo":    desc_limpa
                })

            print(f"📰 ✅ {len(noticias)} notícias encontradas!")
            return noticias

        except Exception as e:
            print(f"📰 ⚠️ Erro: {e}")
            continue

    print("📰 ❌ Nenhuma fonte funcionou.")
    return []


def formatar_noticia(n, index, total):
    cat  = f"🏷️ _{n['categoria']}_\n" if n.get("categoria") else ""
    data = f"📅 {n['data']}\n"        if n.get("data")      else ""
    res  = f"\n_{n['resumo']}..._"    if n.get("resumo")    else ""
    return (
        f"📰 *{index}/{total}*\n"
        f"{cat}*{n['titulo']}*\n"
        f"{data}{res}\n\n"
        f"🔗 {n['link']}"
    )


async def disparar_noticias(bot, periodo_label=""):
    global _inicializado, _ids_enviados

    noticias = await buscar_noticias()

    if not noticias:
        return

    if not _inicializado:
        _ids_enviados = {n["id"] for n in noticias}
        _inicializado = True
        print(f"📰 Estado inicial: {len(_ids_enviados)} notícias salvas.")
        return

    novas = [n for n in noticias if n["id"] not in _ids_enviados]

    if not novas:
        print("📰 Sem notícias novas.")
        return

    print(f"📰 {len(novas)} nova(s)!")
    for n in novas:
        _ids_enviados.add(n["id"])

    for chat_id in IDS_AUTORIZADOS:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"🏠 *Notícias Imobiliárias*\n_{periodo_label}_ — {len(novas)} nova(s)",
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
            print(f"⚠️ Erro envio {chat_id}: {e}")
