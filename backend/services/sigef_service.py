# @module services.sigef_service — Consulta automatica SIGEF/INCRA para laudos rurais
"""Servico de consulta ao SIGEF (Sistema de Gestao Fundiaria - INCRA) e SICAR (CAR).

Credenciais INCRA: FQNS / CFTMA 12-091-853-69

Endpoints utilizados:
  SIGEF: https://sigef.incra.gov.br/api/parcela/{uuid}
  SIGEF busca: https://sigef.incra.gov.br/api/parcela/?search=...
  SICAR: https://www.car.gov.br/publico/imoveis/index
  BrasilAPI municipios: https://brasilapi.com.br/api/ibge/municipios/v1/{uf}
"""
import asyncio
import httpx
import re
from datetime import datetime
from typing import Optional


SIGEF_BASE = "https://sigef.incra.gov.br/api"
SICAR_BASE = "https://www.car.gov.br"
BRASIL_API = "https://brasilapi.com.br/api"

REQUEST_TIMEOUT = 20.0

# ── Tabela de Modulos Fiscais — Municipios do Maranhao ───────────────────────
MODULOS_FISCAIS_MA = {
    # municipio_nome_lower: modulo_fiscal_ha
    "acailandia": 65,
    "afonso cunha": 30,
    "agua doce do maranhao": 40,
    "alcantara": 40,
    "aldeias altas": 30,
    "altamira do maranhao": 55,
    "alto alegre do maranhao": 40,
    "alto alegre do pindare": 55,
    "alto parnaiba": 65,
    "amapa do maranhao": 55,
    "amarante do maranhao": 65,
    "anajatuba": 30,
    "anapurus": 30,
    "apicum-acu": 30,
    "araguana": 55,
    "araioses": 30,
    "arame": 65,
    "arari": 40,
    "axixa": 40,
    "bacabal": 40,
    "bacabeira": 40,
    "bacuri": 30,
    "bacurituba": 30,
    "balsas": 65,
    "barao de grajau": 55,
    "barra do corda": 55,
    "barreirinhas": 30,
    "bequimao": 30,
    "bernardo do mearim": 40,
    "boa vista do gurupi": 55,
    "bom jardim": 55,
    "bom jesus das selvas": 55,
    "bom lugar": 40,
    "brejo": 30,
    "brejo de areia": 55,
    "buriti": 30,
    "buriti bravo": 30,
    "buritirana": 65,
    "cachoeira grande": 40,
    "cajapio": 40,
    "cajari": 30,
    "campestre do maranhao": 65,
    "candido mendes": 40,
    "cantanhede": 30,
    "capinzal do norte": 40,
    "carolina": 65,
    "carutapera": 40,
    "caxias": 30,
    "cedral": 30,
    "central do maranhao": 40,
    "centro do guilherme": 55,
    "centro novo do maranhao": 55,
    "chapadinha": 30,
    "cidelandia": 65,
    "codo": 30,
    "coelho neto": 30,
    "colinas": 55,
    "conceicao do lago-acu": 40,
    "coroata": 30,
    "cururupu": 30,
    "davinopolis": 65,
    "dom pedro": 40,
    "duque bacelar": 30,
    "esperantinopolis": 40,
    "estreito": 65,
    "feira nova do maranhao": 65,
    "fernando falcao": 55,
    "formosa da serra negra": 65,
    "fortaleza dos nogueiras": 65,
    "fortuna": 30,
    "godofredo viana": 40,
    "goncalves dias": 40,
    "governador archer": 40,
    "governador edison lobao": 65,
    "governador eugenio barros": 40,
    "governador luiz rocha": 40,
    "governador newton bello": 40,
    "governador nunes freire": 40,
    "graca aranha": 40,
    "grajau": 55,
    "guimaraes": 30,
    "humberto de campos": 30,
    "icatu": 30,
    "igarape do meio": 40,
    "igarape grande": 40,
    "imperatriz": 65,
    "itaipava do grajau": 55,
    "itapecuru mirim": 40,
    "itinga do maranhao": 55,
    "jatoba": 40,
    "jenipapo dos vieiras": 55,
    "joao lisboa": 65,
    "joselandia": 40,
    "junco do maranhao": 40,
    "lago da pedra": 55,
    "lago do junco": 40,
    "lago dos rodrigues": 40,
    "lago verde": 55,
    "lagoa do mato": 30,
    "lagoa grande do maranhao": 55,
    "lajeado novo": 65,
    "lima campos": 40,
    "loreto": 65,
    "luis domingues": 40,
    "magalhaes de almeida": 30,
    "maracanã": 30,
    "maracas": 40,
    "maraja do sena": 55,
    "maranhãozinho": 40,
    "mata roma": 30,
    "matinha": 40,
    "matoes": 30,
    "matoes do norte": 40,
    "milagres do maranhao": 30,
    "mirador": 55,
    "miranda do norte": 30,
    "mirinzal": 30,
    "moncao": 40,
    "montes altos": 65,
    "morros": 30,
    "nina rodrigues": 30,
    "nova colinas": 65,
    "nova iorque": 55,
    "nova olinda do maranhao": 40,
    "olho dagua das cunhas": 55,
    "olinda nova do maranhao": 40,
    "paco do lumiar": 30,
    "palmeirandia": 40,
    "paraibano": 30,
    "parnarama": 30,
    "passagem franca": 55,
    "pastos bons": 55,
    "paulino neves": 30,
    "paulo ramos": 55,
    "pedreiras": 40,
    "pedro do rosario": 40,
    "penalva": 30,
    "peri mirim": 30,
    "peritoro": 40,
    "pindare-mirim": 55,
    "pinheiro": 30,
    "pio xii": 55,
    "pirapemas": 30,
    "pocao de pedras": 40,
    "porto franco": 65,
    "porto rico do maranhao": 40,
    "presidente dutra": 40,
    "presidente juscelino": 30,
    "presidente medici": 55,
    "presidente sarney": 40,
    "presidente vargas": 30,
    "primeira cruz": 30,
    "raposa": 30,
    "riachao": 65,
    "ribamar fiquene": 65,
    "rosario": 40,
    "sambaiba": 65,
    "santa filomena do maranhao": 40,
    "santa helena": 40,
    "santa ines": 55,
    "santa luzia": 65,
    "santa luzia do parua": 55,
    "santa quiteria do maranhao": 30,
    "santa rita": 30,
    "santana do maranhao": 30,
    "santo amaro do maranhao": 30,
    "santo antonio dos lopes": 40,
    "sao benedito do rio preto": 30,
    "sao bento": 30,
    "sao bernardo": 30,
    "sao domingos do azeitao": 65,
    "sao domingos do maranhao": 40,
    "sao felix de balsas": 65,
    "sao francisco do brejao": 65,
    "sao francisco do maranhao": 30,
    "sao joao batista": 30,
    "sao joao do caru": 55,
    "sao joao do paraiso": 65,
    "sao joao do soter": 30,
    "sao joao dos patos": 55,
    "sao jose de ribamar": 30,
    "sao jose dos basilios": 40,
    "sao luis": 30,
    "sao luis gonzaga do maranhao": 40,
    "sao mateus do maranhao": 40,
    "sao pedro da agua branca": 65,
    "sao pedro dos crentes": 65,
    "sao raimundo das mangabeiras": 65,
    "sao raimundo do doca bezerra": 40,
    "sao roberto": 40,
    "sao vicente ferrer": 30,
    "satubinha": 55,
    "senador alexandre costa": 40,
    "senador la rocque": 65,
    "serrano do maranhao": 30,
    "sitio novo": 65,
    "sucupira do norte": 65,
    "sucupira do riachao": 65,
    "tasso fragoso": 65,
    "timbiras": 30,
    "timon": 30,
    "trizidela do vale": 40,
    "tufilandia": 40,
    "tuntum": 55,
    "turiacu": 40,
    "turilandia": 40,
    "tutoia": 30,
    "urbano santos": 30,
    "vargem grande": 30,
    "viana": 30,
    "vila nova dos martirios": 65,
    "vitoria do mearim": 40,
    "vitorino freire": 55,
    "ze doca": 55,
}

# ── Modulo Fiscal padrao por estado (quando municipio nao encontrado) ─────────
MODULOS_FISCAIS_DEFAULT = {
    "AC": 70, "AL": 30, "AM": 70, "AP": 70, "BA": 65,
    "CE": 30, "DF": 30, "ES": 24, "GO": 65, "MA": 55,
    "MG": 30, "MS": 65, "MT": 65, "PA": 70, "PB": 30,
    "PE": 30, "PI": 30, "PR": 20, "RJ": 20, "RN": 30,
    "RO": 70, "RR": 70, "RS": 18, "SC": 18, "SE": 30,
    "SP": 20, "TO": 65,
}


def _normalizar_municipio(nome: str) -> str:
    """Remove acentos e normaliza para busca."""
    import unicodedata
    return unicodedata.normalize("NFD", nome.lower()).encode("ascii", "ignore").decode("ascii").strip()


def _validar_ccir(ccir: str) -> bool:
    """Valida CCIR: deve ter exatamente 15 digitos numericos (sem mascara)."""
    digits = re.sub(r"\D", "", ccir or "")
    return len(digits) == 15


def _formatar_ccir(ccir: str) -> str:
    """Formata CCIR com mascara XXX.XXX.XXX-X (os primeiros 10 digitos)."""
    digits = re.sub(r"\D", "", ccir or "")
    if len(digits) >= 10:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9]}"
    return ccir


def _parse_area_ha(valor) -> Optional[float]:
    """Converte valor de area para hectares."""
    try:
        if valor is None:
            return None
        v = str(valor).replace(",", ".").strip()
        return round(float(v), 4)
    except Exception:
        return None


async def buscar_por_sigef_codigo(codigo: str) -> Optional[dict]:
    """Consulta parcela certificada pelo UUID/codigo SIGEF.
    
    GET https://sigef.incra.gov.br/api/parcela/{codigo}/
    """
    if not codigo:
        return None
    codigo = codigo.strip()
    url = f"{SIGEF_BASE}/parcela/{codigo}/"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url, headers={
                "Accept": "application/json",
                "User-Agent": "AvalieImob/1.0 (avaliacao-imovel-rural; FQNS/CFTMA 12-091-853-69)",
            })
            if r.status_code == 200:
                data = r.json()
                return _normalizar_parcela_sigef(data)
            return None
    except Exception:
        return None


async def buscar_por_ccir(ccir: str) -> Optional[dict]:
    """Tenta localizar parcela pelo numero CCIR via API SIGEF.
    
    GET https://sigef.incra.gov.br/api/parcela/?ccir={ccir}
    """
    if not ccir:
        return None
    digits = re.sub(r"\D", "", ccir)
    if len(digits) < 10:
        return None
    url = f"{SIGEF_BASE}/parcela/"
    params = {"ccir": digits, "format": "json"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url, params=params, headers={
                "Accept": "application/json",
                "User-Agent": "AvalieImob/1.0 (avaliacao-imovel-rural; FQNS/CFTMA 12-091-853-69)",
            })
            if r.status_code == 200:
                data = r.json()
                # Pode retornar lista ou objeto com 'results'
                if isinstance(data, list) and data:
                    return _normalizar_parcela_sigef(data[0])
                if isinstance(data, dict):
                    results = data.get("results") or data.get("features") or []
                    if results:
                        return _normalizar_parcela_sigef(results[0])
                    # Objeto direto
                    if data.get("codigo") or data.get("id"):
                        return _normalizar_parcela_sigef(data)
            return None
    except Exception:
        return None


def _normalizar_parcela_sigef(raw: dict) -> dict:
    """Normaliza resposta da API SIGEF para estrutura padrao."""
    if not isinstance(raw, dict):
        return {}
    
    # Tenta extrair de estrutura GeoJSON feature ou objeto direto
    props = raw.get("properties") or raw
    
    area_ha = _parse_area_ha(props.get("area_ha") or props.get("area") or props.get("area_total_ha"))
    perimetro = _parse_area_ha(props.get("perimetro") or props.get("perimetro_m"))
    vertices = props.get("vertices") or props.get("num_vertices")
    
    situacao_raw = str(props.get("situacao") or props.get("status") or "").lower()
    situacao_map = {
        "certificada": "certificado",
        "certificado": "certificado",
        "em_certificacao": "em_certificacao",
        "em certificacao": "em_certificacao",
        "nao_certificada": "nao_certificado",
        "nao_certificado": "nao_certificado",
        "georreferenciada": "certificado",
    }
    situacao = situacao_map.get(situacao_raw, situacao_raw or "nao_certificado")
    
    data_cert = props.get("data_certificacao") or props.get("data_aprovacao") or ""
    if data_cert:
        try:
            dt = datetime.fromisoformat(str(data_cert).replace("Z", "+00:00"))
            data_cert = dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    
    municipio = props.get("municipio") or props.get("municipio_nome") or ""
    uf = props.get("uf") or props.get("estado") or ""
    
    # Extrai UF do municipio se vier junto
    if "/" in str(municipio):
        parts = str(municipio).split("/")
        municipio = parts[0].strip()
        uf = parts[-1].strip() if len(parts) > 1 else uf
    
    codigo = props.get("codigo") or props.get("id") or props.get("uuid") or ""
    denominacao = props.get("denominacao") or props.get("nome") or props.get("denominacao_imovel") or ""
    datum = props.get("datum") or "SIRGAS 2000"
    
    # GeoJSON do poligono
    poligono = None
    if raw.get("geometry"):
        import json
        try:
            poligono = json.dumps(raw["geometry"])
        except Exception:
            pass

    return {
        "codigo": str(codigo),
        "denominacao": str(denominacao),
        "situacao": situacao,
        "data_certificacao": str(data_cert),
        "area_ha": area_ha,
        "perimetro_m": perimetro,
        "vertices": int(vertices) if vertices else None,
        "datum": datum,
        "municipio": str(municipio),
        "uf": str(uf).upper(),
        "poligono": poligono,
        "raw": raw,
    }


def buscar_modulo_fiscal(municipio: str, uf: str = "MA") -> float:
    """Retorna modulo fiscal em hectares para o municipio/estado.
    
    Ordem de busca:
    1. Tabela hardcoded MODULOS_FISCAIS_MA (MA)
    2. MODULOS_FISCAIS_DEFAULT por estado
    3. Fallback: 65 ha (media nacional)
    """
    if municipio:
        chave = _normalizar_municipio(municipio)
        if chave in MODULOS_FISCAIS_MA:
            return float(MODULOS_FISCAIS_MA[chave])
        # Busca parcial
        for k, v in MODULOS_FISCAIS_MA.items():
            if chave in k or k in chave:
                return float(v)
    
    uf_upper = (uf or "MA").upper().strip()
    if uf_upper in MODULOS_FISCAIS_DEFAULT:
        return float(MODULOS_FISCAIS_DEFAULT[uf_upper])
    
    return 65.0  # fallback nacional


async def consulta_completa_rural(
    ccir: Optional[str] = None,
    sigef_codigo: Optional[str] = None,
    estado: Optional[str] = None,
) -> dict:
    """Orquestra consulta completa: SIGEF + modulo fiscal em paralelo.
    
    Retorna dict com dados normalizados ou erros parciais.
    Nunca lanca excecao — sempre retorna algo utilizavel.
    """
    resultado = {
        "sigef": None,
        "modulo_fiscal_ha": None,
        "numero_modulos_fiscais": None,
        "erros": [],
        "fonte": "manual",
        "data_consulta": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    # Tarefa SIGEF
    sigef_task = None
    if sigef_codigo and sigef_codigo.strip():
        sigef_task = buscar_por_sigef_codigo(sigef_codigo.strip())
    elif ccir and _validar_ccir(ccir):
        sigef_task = buscar_por_ccir(ccir)
    elif ccir:
        resultado["erros"].append("CCIR invalido: deve ter 15 digitos numericos")

    # Executa em paralelo com timeout global
    if sigef_task:
        try:
            sigef_result = await asyncio.wait_for(sigef_task, timeout=20.0)
            resultado["sigef"] = sigef_result
            resultado["fonte"] = "sigef_api"
        except asyncio.TimeoutError:
            resultado["erros"].append("Timeout ao consultar SIGEF (>20s)")
        except Exception as e:
            resultado["erros"].append(f"Erro SIGEF: {str(e)[:100]}")

    # Calcula modulo fiscal com dados obtidos
    municipio = ""
    uf = estado or "MA"
    if resultado["sigef"]:
        municipio = resultado["sigef"].get("municipio", "")
        uf = resultado["sigef"].get("uf", "") or estado or "MA"
    
    resultado["modulo_fiscal_ha"] = buscar_modulo_fiscal(municipio, uf)
    
    # Calcula numero de modulos fiscais
    area_ha = None
    if resultado["sigef"]:
        area_ha = resultado["sigef"].get("area_ha")
    if area_ha and resultado["modulo_fiscal_ha"]:
        resultado["numero_modulos_fiscais"] = round(area_ha / resultado["modulo_fiscal_ha"], 2)

    return resultado
