# ============================================================
# SISENG BOT — Módulo de Notícias Imobiliárias
# ============================================================

import httpx
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from config import IDS_AUTORIZADOS

URL_SITE = "https://publicidadeimobiliaria.com/"

# Estado em memória dos IDs já enviados
_ids_enviados = set()
_inicializado = False


# ─── SCRAPING ───────────────────────────────────────────────

async def buscar_noticias():
    """Busca notícias do site publicidadeimobiliaria.com"""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(URL_SITE, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

        if response.status_code != 200:
            print(f"⚠️ Notícias: erro HTTP {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        noticias = []

        # Tenta diferentes seletores comuns de blogs/portais
        artigos = (
            soup.select("article") or
            soup.select(".post") or
            soup.select(".entry") or
            soup.select(".item-list") or
            soup.select("div.post-item")
        )

        for artigo in artigos[:20]:
            # Título
            titulo_el = (
                artigo.select_one("h1 a") or
                artigo.select_one("h2 a") or
                artigo.select_one("h3 a") or
                artigo.select_one(".entry-title a") or
                artigo.select_one(".post-title a")
            )
            if not titulo_el:
                continue

            titulo = titulo_el.get_text(strip=True)
            link   = titulo_el.get("href", "")

            if not titulo or not link:
                continue

            # Garante URL absoluta
            if link.startswith("/"):
                link = "https://publicidadeimobiliaria.com" + link

            # ID único da notícia baseado no link
            id_noticia = link.strip().rstrip("/").split("/")[-1]

            # Resumo
            resumo_el = (
                artigo.select_one(".entry-content p") or
                artigo.select_one(".post-excerpt") or
                artigo.select_one("p")
            )
            resumo = resumo_el.get_text(strip=True)[:200] if resumo_el else ""

            noticias.append({
                "id":      id_noticia,
                "titulo":  titulo,
                "link":    link,
                "resumo":  resumo
            })

        print(f"📰 Notícias encontradas: {len(noticias)}")
        return noticias

    except Exception as e:
        print(f"⚠️ Erro ao buscar notícias: {e}")
        return []


# ─── FORMATAÇÃO ─────────────────────────────────────────────

def formatar_noticia(n, index, total):
    resumo = f"\n_{n['resumo']}..._" if n.get("resumo") else ""
    return (
        f"📰 *Notícia {index}/{total}*\n\n"
        f"*{n['titulo']}*"
        f"{resumo}\n\n"
        f"🔗 [Leia mais]({n['link']})"
    )


# ─── ENVIO ──────────────────────────────────────────────────

async def disparar_noticias(bot, periodo_label=""):
    """
    Busca notícias, filtra as já enviadas e dispara para todos os IDs autorizados.
    Na primeira execução apenas salva o estado sem enviar.
    """
    global _inicializado, _ids_enviados

    noticias = await buscar_noticias()

    if not noticias:
        print("📰 Nenhuma notícia encontrada.")
        return

    # Primeira execução — só salva IDs, não envia
    if not _inicializado:
        _ids_enviados = {n["id"] for n in noticias}
        _inicializado = True
        print(f"📰 Estado inicial salvo: {len(_ids_enviados)} notícias conhecidas.")
        return

    # Filtra apenas notícias novas
    novas = [n for n in noticias if n["id"] not in _ids_enviados]

    if not novas:
        print(f"📰 Nenhuma notícia nova no período.")
        return

    print(f"📰 {len(novas)} notícia(s) nova(s) para enviar!")

    # Atualiza estado
    for n in novas:
        _ids_enviados.add(n["id"])

    # Envia para todos os IDs autorizados
    for chat_id in IDS_AUTORIZADOS:
        try:
            header = (
                f"🏠 *Notícias do Mercado Imobiliário*\n"
                f"_{periodo_label}_\n"
                f"{'─' * 30}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=header,
                parse_mode="Markdown"
            )

            for i, n in enumerate(novas, 1):
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatar_noticia(n, i, len(novas)),
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )

        except Exception as e:
            print(f"⚠️ Erro ao enviar notícias para {chat_id}: {e}")
