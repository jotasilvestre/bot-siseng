# ============================================================
# SISENG BOT — Consultas
# ============================================================

from sheets import ler_aba
import re


# ─── HELPERS ────────────────────────────────────────────────

def ou_traco(valor):
    return str(valor).strip() if str(valor).strip() else "—"

def formatar_moeda(valor):
    try:
        n = float(str(valor).replace(',', '.'))
        return f"R$ {n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(valor) if valor else "—"

def formatar_cpf(valor):
    if not valor:
        return "—"
    # Remove tudo que não é dígito
    digits = re.sub(r'\D', '', str(valor))
    # Sheets pode armazenar como número (sem zero à esquerda)
    # Preenche com zeros à esquerda até 11 dígitos
    digits = digits.zfill(11)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return str(valor).strip() or "—"

def formatar_cnpj(valor):
    if not valor:
        return "—"
    digits = re.sub(r'\D', '', str(valor))
    # Preenche com zeros à esquerda até 14 dígitos
    digits = digits.zfill(14)
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return str(valor).strip() or "—"

def formatar_telefone(valor):
    if not valor:
        return "—"
    digits = re.sub(r'\D', '', str(valor))
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return str(valor).strip() or "—"

def eh_id(termo):
    return bool(re.match(r'^[a-f0-9]{8}$', termo.lower().strip()))

def normalizar(texto):
    """Remove acentos e coloca em minúsculo para comparação."""
    import unicodedata
    texto = str(texto or '').lower().strip()
    return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('ascii')

def similaridade(a, b):
    """Calcula similaridade entre dois textos normalizados."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()

def busca_inteligente(termo, registros, campo, campo_id=''):
    """
    Busca registros pelo campo usando:
    1. Correspondência exata (sem acento)    ex: Fabrício == Fabricio
    2. Correspondência parcial               ex: João → João Silva
    3. Similaridade >= 0.75                  ex: Jozé → José
    Retorna lista ordenada por relevância.
    """
    termo_norm = normalizar(termo)
    exatos   = []
    parciais = []
    similares = []

    for r in registros:
        valor_norm = normalizar(r.get(campo, ''))

        if termo_norm == valor_norm:
            exatos.append((1.0, r))
        elif termo_norm in valor_norm or valor_norm in termo_norm:
            parciais.append((0.9, r))
        else:
            # Compara termo com cada palavra do nome e com o nome completo
            palavras = valor_norm.split()
            melhor = max((similaridade(termo_norm, p) for p in palavras), default=0)
            sim_total = similaridade(termo_norm, valor_norm)
            score = max(melhor, sim_total)
            if score >= 0.75:
                similares.append((score, r))

    similares.sort(key=lambda x: x[0], reverse=True)
    resultado = [r for _, r in exatos + parciais + similares]

    # Remove duplicatas mantendo ordem
    vistos = set()
    final = []
    for r in resultado:
        chave = str(r.get(campo_id, id(r)))
        if chave not in vistos:
            vistos.add(chave)
            final.append(r)

    return final


# ─── MAPAS DE LOOKUP ────────────────────────────────────────

def carregar_mapa_cidades():
    return {str(r.get("IdCidade","")).strip(): str(r.get("Cidade","")).strip()
            for r in ler_aba("Cidade")}

def carregar_mapa_estados():
    return {str(r.get("IdEstado","")).strip(): str(r.get("Nome","")).strip()
            for r in ler_aba("Estado")}

def carregar_mapa_clientes():
    return {str(r.get("IdCliente","")).strip(): str(r.get("Nome","")).strip()
            for r in ler_aba("Cliente")}

def carregar_mapa_bancos():
    """Retorna dict {IdBanco: 'NomeBanco'}"""
    return {str(r.get("IdBanco","")).strip(): str(r.get("Banco","")).strip()
            for r in ler_aba("Banco")}

def carregar_mapa_parceiros():
    """Retorna dict {IdParceiro: 'NomeParceiro'}"""
    return {str(r.get("IdParceiro","")).strip(): str(r.get("Nome","")).strip()
            for r in ler_aba("Parceiro")}


# ─── CLIENTES ───────────────────────────────────────────────

def buscar_cliente(termo):
    registros = ler_aba("Cliente")
    if eh_id(termo):
        return [r for r in registros
                if str(r.get("IdCliente","")).lower().strip() == termo.lower().strip()]
    return busca_inteligente(termo, registros, "Nome", "IdCliente")


def formatar_cliente(r):
    mapa_cidades  = carregar_mapa_cidades()
    mapa_estados  = carregar_mapa_estados()
    mapa_parceiros = carregar_mapa_parceiros()

    nome         = ou_traco(r.get("Nome"))
    tipo_vinculo = ou_traco(r.get("TipoVinculo"))
    tipo_cliente = ou_traco(r.get("TipoCliente"))
    email        = ou_traco(r.get("Email"))
    estado_civil = ou_traco(r.get("EstadoCivil"))
    endereco     = ou_traco(r.get("Endereco"))
    loja         = ou_traco(r.get("Loja"))
    status       = ou_traco(r.get("StatusCadastro"))
    id_cliente   = ou_traco(r.get("IdCliente"))

    # CPF / CNPJ
    cpf  = formatar_cpf(r.get("Cpf") or r.get("CpfFormatado"))
    cnpj = formatar_cnpj(r.get("Cnpj") or r.get("CnpjFormatado"))
    doc_linha = f"🪪 CNPJ: {cnpj}" if tipo_cliente == "Pessoa Jurídica" else f"🪪 CPF: {cpf}"

    # Telefone
    telefone = formatar_telefone(r.get("TelefoneFormatado") or r.get("Telefone"))

    # Cidade e Estado
    id_cidade = str(r.get("Cidade","")).strip()
    id_estado = str(r.get("Estado","")).strip()
    cidade = mapa_cidades.get(id_cidade, id_cidade) if id_cidade else "—"
    estado = mapa_estados.get(id_estado, id_estado) if id_estado else "—"

    # Parceiro que trouxe o cliente
    id_parceiro = str(r.get("Parceiro","")).strip()
    parceiro = mapa_parceiros.get(id_parceiro, "—") if id_parceiro else "—"

    return (
        f"👤 *{nome}*\n"
        f"🆔 ID: `{id_cliente}`\n"
        f"🔗 Vínculo: {tipo_vinculo}\n"
        f"👥 Tipo: {tipo_cliente}\n"
        f"{doc_linha}\n"
        f"📞 Telefone: {telefone}\n"
        f"📧 E-mail: {email}\n"
        f"💍 Estado Civil: {estado_civil}\n"
        f"📍 {endereco} — {cidade}/{estado}\n"
        f"🏢 Loja: {loja}\n"
        f"🤝 Captado por: {parceiro}\n"
        f"📋 Status: {status}\n\n"
        f"📌 Use /historico `{id_cliente}` para ver a jornada completa."
    )

def historico_cliente(id_cliente):
    id_cliente = id_cliente.strip()
    mapa_bancos = carregar_mapa_bancos()

    clientes = ler_aba("Cliente")
    cliente = next(
        (r for r in clientes if str(r.get("IdCliente","")).strip() == id_cliente), None
    )
    if not cliente:
        return f"❌ Cliente com ID `{id_cliente}` não encontrado."

    nome = ou_traco(cliente.get("Nome"))
    linhas = [f"📂 *Jornada do cliente: {nome}*\n"]

    # Avaliações — resolve banco
    avaliacoes = [r for r in ler_aba("Avaliacao")
                  if str(r.get("Cliente","")).strip() == id_cliente]
    linhas.append(f"🏦 *Avaliações de crédito:* {len(avaliacoes)}")
    for a in avaliacoes[:3]:
        id_banco = str(a.get("Banco","")).strip()
        nome_banco = mapa_bancos.get(id_banco, id_banco) if id_banco else "—"
        linhas.append(
            f"  • {ou_traco(a.get('TipoAvaliacao'))} | "
            f"Banco: {nome_banco} | "
            f"Status: {ou_traco(a.get('Status'))}"
        )

    # Andamentos
    andamentos = [r for r in ler_aba("Andamento")
                  if str(r.get("ClienteVendedor","")).strip() == id_cliente]
    linhas.append(f"\n📊 *Andamentos de processo:* {len(andamentos)}")
    for a in andamentos[:3]:
        linhas.append(
            f"  • Avaliação: {ou_traco(a.get('Avaliacao'))} | "
            f"Status: {ou_traco(a.get('StatusAndamento'))}"
        )

    # Transações
    transacoes  = ler_aba("Transacao")
    trans_cli   = [r for r in transacoes if str(r.get("Cliente","")).strip()  == id_cliente]
    trans_cli1  = [r for r in transacoes if str(r.get("Cliente1","")).strip() == id_cliente]

    linhas.append(f"\n📝 *Transações como proprietário/vendedor:* {len(trans_cli)}")
    for t in trans_cli[:3]:
        linhas.append(
            f"  • {ou_traco(t.get('Tipo'))} | "
            f"Valor: {formatar_moeda(t.get('ValorTransacao'))} | "
            f"Loja: {ou_traco(t.get('Loja'))}"
        )

    linhas.append(f"\n📝 *Transações como locatário/comprador:* {len(trans_cli1)}")
    for t in trans_cli1[:3]:
        linhas.append(
            f"  • {ou_traco(t.get('Tipo'))} | "
            f"Valor: {formatar_moeda(t.get('ValorTransacao'))} | "
            f"Loja: {ou_traco(t.get('Loja'))}"
        )

    # Imóveis
    imoveis = [r for r in ler_aba("Imovel")
               if str(r.get("ClienteVendedor","")).strip() == id_cliente]
    linhas.append(f"\n🏠 *Imóveis vinculados:* {len(imoveis)}")
    for i in imoveis[:3]:
        linhas.append(
            f"  • {ou_traco(i.get('Endereco'))} | "
            f"Tipo: {ou_traco(i.get('TipoOferta'))}"
        )

    # AdmImóveis
    admimoveis = [r for r in ler_aba("AdmImovel")
                  if str(r.get("Cliente","")).strip() == id_cliente]
    linhas.append(f"\n🏢 *Imóveis sob administração:* {len(admimoveis)}")
    for a in admimoveis[:3]:
        linhas.append(f"  • Imóvel ID: {ou_traco(a.get('Imovel'))}")

    return "\n".join(linhas)


# ─── IMÓVEIS ────────────────────────────────────────────────

def buscar_imovel(termo):
    registros = ler_aba("Imovel")
    if eh_id(termo):
        return [r for r in registros
                if str(r.get("IdImovel","")).lower().strip() == termo.lower().strip()]
    return busca_inteligente(termo, registros, "Endereco", "IdImovel")


def formatar_imovel(r):
    mapa_cidades = carregar_mapa_cidades()
    id_cidade = str(r.get("Cidade","")).strip()
    cidade = mapa_cidades.get(id_cidade, id_cidade) if id_cidade else "—"

    return (
        f"🏠 *{ou_traco(r.get('Endereco'))}*\n"
        f"🆔 ID: `{ou_traco(r.get('IdImovel'))}`\n"
        f"📦 Tipo: {ou_traco(r.get('TipoImovel'))} | Oferta: {ou_traco(r.get('TipoOferta'))}\n"
        f"📍 Cidade: {cidade}\n"
        f"📄 Matrícula: {ou_traco(r.get('Matricula'))}\n"
        f"🔢 Inscrição: {ou_traco(r.get('Inscricao'))}"
    )


# ─── TRANSAÇÕES ─────────────────────────────────────────────

def buscar_transacao(termo):
    registros = ler_aba("Transacao")
    termo_lower = termo.lower().strip()

    if eh_id(termo):
        return [r for r in registros
                if str(r.get("IdTransacao","")).lower().strip() == termo_lower]

    mapa = carregar_mapa_clientes()
    encontrados = []
    for r in registros:
        nome_cli  = mapa.get(str(r.get("Cliente","")).strip(), "")
        nome_cli1 = mapa.get(str(r.get("Cliente1","")).strip(), "")
        if termo_lower in nome_cli.lower() or termo_lower in nome_cli1.lower():
            r["_NomeCliente"]  = nome_cli
            r["_NomeCliente1"] = nome_cli1
            encontrados.append(r)

    return encontrados

def formatar_transacao(r):
    mapa = carregar_mapa_clientes()
    nome_cli  = r.get("_NomeCliente")  or mapa.get(str(r.get("Cliente","")).strip(),  ou_traco(r.get("Cliente")))
    nome_cli1 = r.get("_NomeCliente1") or mapa.get(str(r.get("Cliente1","")).strip(), ou_traco(r.get("Cliente1")))

    return (
        f"📝 *Transação {ou_traco(r.get('IdTransacao'))}*\n"
        f"🔖 Tipo: {ou_traco(r.get('Tipo'))}\n"
        f"👤 Proprietário/Vendedor: {nome_cli}\n"
        f"👤 Locatário/Comprador: {nome_cli1}\n"
        f"📊 Status: {ou_traco(r.get('Status') or r.get('StatusTransacao'))}\n"
        f"💰 Valor: {formatar_moeda(r.get('ValorTransacao'))}\n"
        f"📅 Assinatura: {ou_traco(r.get('DataAssinatura'))}\n"
        f"🏢 Loja: {ou_traco(r.get('Loja'))}"
    )


# ─── PARCEIROS ──────────────────────────────────────────────

# Funções internas da imobiliária (primeiros 3 do enum)
FUNCOES_INTERNAS = ["Administrativo", "Corretor", "Corretor Estagiário"]

# Todas as funções disponíveis
FUNCOES_DISPONIVEIS = [
    "Administrativo",
    "Corretor",
    "Corretor Estagiário",
    "Parceiro Externa",
    "Corretor Externo",
    "Imobiliária Externa",
    "Prestador de Serviço",
    "Desligado"
]

def buscar_parceiro(termo):
    registros = ler_aba("Parceiro")
    if eh_id(termo):
        return [r for r in registros
                if str(r.get("IdParceiro","")).lower().strip() == termo.lower().strip()]
    return busca_inteligente(termo, registros, "Nome", "IdParceiro")


def listar_parceiros_por_funcao(funcao):
    """
    Lista parceiros filtrando por Funcao.
    Se funcao='internos', retorna Administrativo + Corretor + Corretor Estagiário.
    """
    registros = ler_aba("Parceiro")
    funcao_lower = funcao.lower().strip()

    if funcao_lower == "internos":
        return [r for r in registros
                if str(r.get("Funcao","")).strip() in FUNCOES_INTERNAS]

    # Busca flexível pelo nome da função
    return [r for r in registros
            if funcao_lower in str(r.get("Funcao","")).lower()]

def formatar_parceiro(r):
    mapa_bancos = carregar_mapa_bancos()

    telefone = formatar_telefone(r.get("TelefoneFormatado") or r.get("Telefone"))
    cpf      = formatar_cpf(r.get("CPF") or r.get("Cpf"))
    funcao   = ou_traco(r.get("Funcao"))
    status   = ou_traco(r.get("StatusFuncao"))
    creci    = ou_traco(r.get("Creci") or r.get("CRECI"))

    # Banco → resolve ID para nome
    id_banco = str(r.get("Banco","")).strip()
    nome_banco = mapa_bancos.get(id_banco, id_banco) if id_banco else "—"
    agencia  = ou_traco(r.get("Agencia"))
    conta    = ou_traco(r.get("Conta"))
    tipo_pix = ou_traco(r.get("TipoPix"))
    pix      = ou_traco(r.get("Pix"))

    return (
        f"🤝 *{ou_traco(r.get('Nome'))}*\n"
        f"🆔 ID: `{ou_traco(r.get('IdParceiro'))}`\n"
        f"🏷️ Função: {funcao} | Status: {status}\n"
        f"🪪 CRECI: {creci}\n"
        f"📋 CPF: {cpf}\n"
        f"📞 {telefone}\n"
        f"📧 {ou_traco(r.get('Email'))}\n"
        f"🏢 Loja: {ou_traco(r.get('Loja'))}\n"
        f"🏦 Banco: {nome_banco} | Ag: {agencia} | Conta: {conta}\n"
        f"💠 Pix ({tipo_pix}): {pix}"
    )


# ─── RESUMO GERAL ───────────────────────────────────────────

def resumo_geral():
    clientes   = ler_aba("Cliente")
    imoveis    = ler_aba("Imovel")
    transacoes = ler_aba("Transacao")
    parceiros  = ler_aba("Parceiro")

    internos   = [p for p in parceiros if str(p.get("Funcao","")).strip() in FUNCOES_INTERNAS]
    locacoes   = [t for t in transacoes if str(t.get("Tipo","")).strip() == "Locação"]
    vendas     = [t for t in transacoes if str(t.get("Tipo","")).strip() == "Compra e Venda"]

    pv_loc = [t for t in locacoes if str(t.get("Loja","")).strip() == "Porto Velho"]
    ja_loc = [t for t in locacoes if str(t.get("Loja","")).strip() == "Jaru"]
    pv_vnd = [t for t in vendas   if str(t.get("Loja","")).strip() == "Porto Velho"]
    ja_vnd = [t for t in vendas   if str(t.get("Loja","")).strip() == "Jaru"]

    return (
        f"📊 *Resumo SISENG*\n\n"
        f"👥 Clientes cadastrados: {len(clientes)}\n"
        f"🏠 Imóveis em carteira: {len(imoveis)}\n"
        f"🤝 Equipe interna: {len(internos)} | Total cadastrado: {len(parceiros)}\n\n"
        f"📝 *Transações totais: {len(transacoes)}*\n\n"
        f"🔑 Locações: {len(locacoes)}\n"
        f"  ↳ Porto Velho: {len(pv_loc)}\n"
        f"  ↳ Jaru: {len(ja_loc)}\n\n"
        f"🏡 Compra e Venda: {len(vendas)}\n"
        f"  ↳ Porto Velho: {len(pv_vnd)}\n"
        f"  ↳ Jaru: {len(ja_vnd)}"
    )
