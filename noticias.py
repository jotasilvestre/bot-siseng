# ============================================================
# SISENG BOT — Módulo de Notícias via RSS direto
# ============================================================

import httpx
import xml.etree.ElementTree as ET
import re
from config import IDS_AUTORIZADOS

_ids_enviados = set()
_inicializado = False

RSS_FEED = "https://publicidadeimobiliaria.com/feed/"

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Feedly/1.0 (+http://www.feedly.com/fetcher.html)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    },
    {
        "User-Agent": "python-httpx/0.27.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    },
]


async def buscar_noticias():
    """Tenta diferentes User-Agents para buscar o RSS."""
    for headers in HEADERS_LIST:
        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers=headers
            ) as client:
                response = await client.get(RSS_FEED)

            texto = response.text.strip()
            ct = response.headers.get("content-type", "")
            print(f"📰 Status: {response.status_code} | CT: {ct[:40]} | UA: {headers['User-Agent'][:30]}")

            if response.status_code != 200:
                continue

            # Verifica se é XML
            if "<rss" not in texto and "<?xml" not in texto:
                print(f"📰 Não é XML, pulando...")
                continue

            root = ET.fromstring(texto)
            channel = root.find("channel")
            if not channel:
                continue

            noticias = []
            for item in channel.findall("item"):
                titulo   = item.findtext("title", "").strip()
                link     = item.findtext("link", "").strip()
                data_pub = item.findtext("pubDate", "")[:16]
                desc     = item.findtext("description", "")
                cat_el   = item.find("category")
                categoria = cat_el.text.strip() if cat_el is not None and cat_el.text else ""
                desc_limpa = re.sub(r'<[^>]+>', '', desc)[:200].strip()
                slug = link.strip("/").split("/")[-1] or link

                if titulo and link:
                    noticias.append({
                        "id": slug, "titulo": titulo, "link": link,
                        "data": data_pub, "categoria": categoria, "resumo": desc_limpa
                    })

            print(f"📰 ✅ {len(noticias)} notícias!")
            return noticias

        except Exception as e:
            print(f"📰 ⚠️ Erro: {e}")
            continue

    # Fallback: busca via scraping simples da página principal
    print("📰 Tentando scraping da página principal...")
    try:
        from bs4 import BeautifulSoup
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://google.com"
        }) as client:
            r = await client.get("https://publicidadeimobiliaria.com/")

        soup = BeautifulSoup(r.text, "html.parser")
        noticias = []
        vistos = set()

        for tag in ["h2", "h3"]:
            for el in soup.find_all(tag):
                a = el.find("a", href=True)
                if not a:
                    continue
                titulo = a.get_text(strip=True)
                link   = a["href"]
                if not titulo or "publicidadeimobiliaria.com" not in link:
                    continue
                slug = link.strip("/").split("/")[-1]
                if slug in vistos or not slug:
                    continue
                vistos.add(slug)
                noticias.append({
                    "id": slug, "titulo": titulo, "link": link,
                    "data": "", "categoria": "", "resumo": ""
                })

        print(f"📰 Scraping: {len(noticias)} notícias")
        return noticias
    except Exception as e:
        print(f"📰 Scraping falhou: {e}")
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


IMAGEM_NOTICIAS = "https://raw.githubusercontent.com/jotasilvestre/bot-siseng/main/banner-noticias.jpg"

async def disparar_noticias(bot, periodo_label=""):
    global _inicializado, _ids_enviados

    noticias = await buscar_noticias()
    if not noticias:
        return

    if not _inicializado:
        _ids_enviados = {n["id"] for n in noticias}
        _inicializado = True
        print(f"📰 Estado inicial: {len(_ids_enviados)} notícias.")
        return

    novas = [n for n in noticias if n["id"] not in _ids_enviados]
    if not novas:
        print("📰 Sem novidades.")
        return

    for n in novas:
        _ids_enviados.add(n["id"])

    for chat_id in IDS_AUTORIZADOS:
        try:
            total_novas = len(novas)
            caption = f"\U0001f3e0 *Noticias do Mercado Imobiliario*\n_{periodo_label}_ — {total_novas} nova(s)"
            await bot.send_photo(
                chat_id=chat_id,
                photo=IMAGEM_NOTICIAS,
                caption=caption,
                parse_mode="Markdown"
            )
            for i, n in enumerate(novas, 1):
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatar_noticia(n, i, total_novas),
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
        except Exception as e:
            print(f"aviso {chat_id}: {e}")
