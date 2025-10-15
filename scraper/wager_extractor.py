# competitor_analysis/scraper/wager_extractor.py
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging

# Palabras clave multi-idioma (amplía según mercados objetivo)
WAGER_KEYWORDS = [
    r'\bwager(?:ing)?\b', r'\bplaythrough\b', r'\brollover\b', r'\bturnover\b',
    r'\brequisito(?:s)? de apuesta\b', r'\bapuesta requerida\b', r'\brequerimiento de apuesta\b',
    r'\bwymaganie obrotu\b', r'\bobrot\b', r'\bvoorwaarden\b',
]

# Patrones numéricos típicos
NUM_PATTERNS = [
    r'(?P<mult>\d{1,3})\s*[x×]\b(?:\s*(?:the )?(?P<scope>bonus|deposit|deposit\+bonus|total))?',
    r'(?P<mult>\d{1,3})\s*(?:times|veces|vezes|razy)\b(?:\s*(?:on|sobre)?\s*(?P<scope>bonus|deposit|deposit\+bonus|total))?',
    r'(?P<percent>\d{1,3})\s*%\s*(?:of|de|do)\s*(?P<scope2>bonus|deposit|stake|wager)',
    r'(?:must|should|will)?\s*(?:be )?(?:wagered|rolled over|playthrough)\s*(?:the\s*)?(?:bonus|deposit)?\s*(?:by\s*)?(?P<mult2>\d{1,3})',
    r"(\d{1,3}x)",
    r"(\d{1,3})\s*(?:times|x)\s*(?:wager|playthrough|rollover|apuesta|veces)",
    r"wager(?:ed|ing)?(?: requirement)?[:\-]?\s*(\d{1,3})",
    r"roll[\- ]?over[:\-]?\s*(\d{1,3}x?)",
    r"(\d{1,3})\s*(?:veces|fois|mal)",
]

# Unimos keyword + número
COMBINED_PATTERNS = []
for kw in WAGER_KEYWORDS:
    for np in NUM_PATTERNS:
        COMBINED_PATTERNS.append(r'(?:(?:' + kw + r').{0,120}?' + np + r')')
        COMBINED_PATTERNS.append(r'(?:' + np + r'.{0,120}?' + kw + r')')

FALLBACK_PATTERN = r'(' + r'|'.join(WAGER_KEYWORDS) + r').{0,120}?(\d{1,3}\s*[x×]|\d{1,3}\s*%|\d{1,3}\s*(?:times|veces|razy))'

def _normalize_scope(raw_scope: Optional[str], raw_scope2: Optional[str]) -> str:
    s = ((raw_scope or '') + ' ' + (raw_scope2 or '')).lower()
    if 'deposit+bonus' in s or '+' in s or 'and' in s:
        return 'deposit+bonus'
    if 'deposit' in s:
        return 'deposit'
    if 'bonus' in s:
        return 'bonus'
    return 'unknown'

def extract_wagering_from_text(text: str) -> Dict[str, Any]:
    """
    Devuelve: {multiplier:int|None, percent:int|None, scope:str|None, raw_text:str, confidence:float, reason:str}
    """
    if not text:
        return {"multiplier": None, "percent": None, "scope": None, "raw_text": "", "confidence": 0.0, "reason": "no_text"}
    txt = ' '.join(text.replace('\u2013','-').replace('\u2014','-').split())

    logger = logging.getLogger(__name__)
    logger.debug(f"[DEBUG WAGER TEXT] Extractor received text snippet: {txt[:500]}")


    for pat in COMBINED_PATTERNS:
        m = re.search(pat, txt, re.I)
        if m:
            mult = m.groupdict().get('mult') or m.groupdict().get('mult2')
            percent = m.groupdict().get('percent')
            scope = _normalize_scope(m.groupdict().get('scope'), m.groupdict().get('scope2'))
            if mult:
                return {"multiplier": int(mult), "percent": None, "scope": scope or 'bonus', "raw_text": m.group(0), "confidence": 0.95, "reason": "direct_combined_regex"}
            if percent:
                return {"multiplier": None, "percent": int(percent), "scope": scope or 'bonus', "raw_text": m.group(0), "confidence": 0.9, "reason": "percent_match"}

    m2 = re.search(FALLBACK_PATTERN, txt, re.I)
    if m2:
        snippet = m2.group(0)
        mnum = re.search(r'(\d{1,3})\s*[x×]?', snippet)
        if mnum:
            return {"multiplier": int(mnum.group(1)), "percent": None, "scope": "unknown", "raw_text": snippet, "confidence": 0.7, "reason": "keyword_near_number"}

    m3 = re.search(r'(\d{1,3})\s*[x×]\b', txt)
    if m3:
        return {"multiplier": int(m3.group(1)), "percent": None, "scope": "unknown", "raw_text": m3.group(0), "confidence": 0.5, "reason": "generic_x_pattern"}

    return {"multiplier": None, "percent": None, "scope": None, "raw_text": "", "confidence": 0.0, "reason": "not_found"}

# Buscar enlaces de T&C/Terms dentro de un HTML (promo card o página completa)
TC_LINK_KEYWORDS = [
    'terms', 'bonus terms', 'bonus rules', 'bonus policy',
    'bonus conditions', 'playthrough', 'requirements', 'requirement',
    'rollover', 'policy', 'rules', 'condiciones', 'reglas',
    'apuesta', 'wager', ' wagering', 'roll-over'
]



def find_candidate_tc_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for a in soup.find_all('a', href=True):
        t = (a.get_text() or "").lower()
        h = a['href'].lower()
        if any(kw in t or kw in h for kw in TC_LINK_KEYWORDS):
            out.append(urljoin(base_url, a['href']))
    # dedupe
    seen, res = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            res.append(u)
    return res

def to_display_string(res: Dict[str, Any]) -> str:
    """Convierte la extracción normalizada a una cadena legible para tu campo `wagering`."""
    if not res or res.get("confidence", 0) <= 0:
        return ""
    if res.get("multiplier"):
        scope = res.get("scope") or "bonus"
        return f"{res['multiplier']}x ({scope})"
    if res.get("percent"):
        scope = res.get("scope") or "bonus"
        return f"{res['percent']}% ({scope})"
    return ""
