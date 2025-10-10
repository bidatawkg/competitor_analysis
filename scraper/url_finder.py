import asyncio
import aiohttp
import logging
import re
import html
from urllib.parse import urlparse, parse_qs, unquote, quote_plus  # extiende lo que ya tienes
from bs4 import BeautifulSoup

logger = logging.getLogger("scraper.url_finder")

DUCKDUCKGO_SEARCH = "https://duckduckgo.com/html/?q="

# 🌍 TLDs más usados por región
COUNTRY_TLDS = {
    "AE": [".ae", ".com", ".net", ".casino", ".bet"],
    "QA": [".qa", ".com", ".net", ".casino", ".bet"],
    "OM": [".om", ".com", ".net", ".casino", ".bet"],
    "BH": [".bh", ".com", ".net", ".casino", ".bet"],
    "KW": [".kw", ".com", ".net", ".casino", ".bet"],
    "SA": [".sa", ".com", ".net", ".casino", ".bet"],
    "JO": [".jo", ".com", ".net", ".casino", ".bet"],
    "NZ": [".nz", ".com", ".net", ".casino", ".bet"],
}


class URLFinder:
    """Busca URLs oficiales o de promociones para un competidor."""

    async def search_duckduckgo(self, session, competitor: str, country: str):
        """Busca el dominio oficial del casino usando DuckDuckGo (HTML endpoint)."""
        # Si la marca ya contiene "casino", no lo añadimos; si no, lo añadimos para acotar.
        q_brand = competitor if "casino" in competitor.lower() else f"{competitor} casino"
        # No confíes en 'OR' de DDG; mejor filtramos por TLD tras parsear resultados.
        q = quote_plus(q_brand)
        url = DUCKDUCKGO_SEARCH + q

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-QA,en;q=0.9,ar-QA;q=0.8",
        }

        try:
            async with session.get(url, timeout=15, headers=headers) as resp:
                if resp.status != 200:
                    return []
                html_text = await resp.text()
                soup = BeautifulSoup(html_text, "html.parser")

                # Permite enlaces directos y redirecciones /l/?uddg=
                raw_urls = []
                for a in soup.select("a.result__a"):
                    href = a.get("href", "")
                    if href.startswith("/l/"):
                        q = parse_qs(urlparse(href).query)
                        uddg = q.get("uddg", [None])[0]
                        if uddg:
                            raw_urls.append(unquote(uddg))
                    elif href.startswith("http"):
                        raw_urls.append(href)

                # Normaliza a dominios y filtra basura/redes sociales
                ban = ("facebook.", "twitter.", "x.com", "instagram.", "youtube.", "linkedin.", "tiktok.")
                allowed_tlds = {".com", ".net", ".casino", ".bet", f".{country.lower()}"}
                domains = []
                for u in raw_urls:
                    p = urlparse(u)
                    if not p.scheme.startswith("http"):
                        continue
                    netloc = p.netloc.lower()
                    if any(b in netloc for b in ban):
                        continue
                    # Filtra por TLD permitidos
                    if not any(netloc.endswith(t) for t in allowed_tlds):
                        continue
                    domains.append(f"{p.scheme}://{netloc}")

                return list(dict.fromkeys(domains))  # únicos y en orden
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed for {competitor}: {e}")
            return []

    def generate_heuristics(self, competitor: str, country: str):
        """Fallback: genera URLs razonables sin mutilar la marca."""
        tokens = re.findall(r"[a-z0-9]+", competitor.lower())
        name_compact = "".join(tokens)                   # justcasino
        name_hyphen = "-".join(tokens)                   # just-casino

        # Si "casino" era palabra separada (p. ej. "Just Casino"), añade variante sin esa palabra
        if "casino" in tokens:
            name_sin_casino = "".join(t for t in tokens if t != "casino")  # just
            bases = [name_compact, name_hyphen, name_sin_casino]
        else:
            bases = [name_compact, name_hyphen]

        tlds = COUNTRY_TLDS.get(country.upper(), [".com", ".net", ".casino", ".bet"])
        urls = []
        for base in dict.fromkeys(bases):  # únicos, conserva orden
            for tld in tlds:
                urls.append(f"https://{base}{tld}")
                urls.append(f"https://www.{base}{tld}")
        return urls

    def build_brand_pattern(self, competitor: str) -> re.Pattern:
        # tokens alfanuméricos del nombre de marca
        tokens = re.findall(r'[a-z0-9]+', competitor.lower())
        if not tokens:
            return re.compile(r"$^")  # nada coincide
        # permite espacios, guiones o guiones bajos entre tokens
        pattern = r"\b" + r"[\s\-_]*".join(tokens) + r"\b"
        return re.compile(pattern, re.I)

    # async def check_url(self, session, url, brand_pattern: re.Pattern):
    #     """Verifica si una URL pertenece realmente a la marca"""
    #     headers = {
    #         "User-Agent": (
    #             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #             "AppleWebKit/537.36 (KHTML, like Gecko) "
    #             "Chrome/120.0.0.0 Safari/537.36"
    #         ),
    #         "Accept-Language": "en-QA,en;q=0.9,ar-QA;q=0.8",
    #     }

    #     try:
    #         async with session.get(
    #             url, timeout=8, allow_redirects=True, headers=headers
    #         ) as resp:
    #             headers_obj = getattr(resp, "headers", {})
    #             if not hasattr(headers_obj, "get"):
    #                 return False  # seguridad ante casos raros

    #             ctype = headers_obj.get("Content-Type", "")
    #             if resp.status < 400 and "text/html" in ctype:
    #                 text = await resp.text(errors="ignore")
    #                 if len(text) < 300:
    #                     return False
    #                 if re.search(r"(404|forbidden|access\s+denied|not\s+found)", text, re.I):
    #                     return False

    #                 soup = BeautifulSoup(text, "html.parser")
    #                 title = (soup.title.string or "") if soup.title else ""
    #                 metas = " ".join(m.get("content", "") for m in soup.find_all("meta"))

    #                 # Busca la marca en title, meta o texto
    #                 hay_marca = bool(
    #                     brand_pattern.search(title)
    #                     or brand_pattern.search(metas)
    #                     or brand_pattern.search(text)
    #                 )
    #                 return hay_marca
    #     except Exception as e:
    #         logger.debug(f"Error checking {url}: {e}")
    #     return False

    async def check_url(self, session, url, brand_pattern: re.Pattern):
        """Verifica si una URL realmente pertenece a la marca."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        }

        try:
            async with session.get(
                url, timeout=15, allow_redirects=True, headers=headers
            ) as resp:
                headers_obj = getattr(resp, "headers", {})
                if not hasattr(headers_obj, "get"):
                    return False

                ctype = headers_obj.get("Content-Type", "")
                if resp.status < 400 and "text/html" in ctype:
                    text = await resp.text(errors="ignore")
                    if len(text) < 300:
                        return False
                    if re.search(r"(404|forbidden|access\s+denied|not\s+found)", text, re.I):
                        return False

                    soup = BeautifulSoup(text, "html.parser")
                    title = (soup.title.string or "") if soup.title else ""
                    metas = " ".join(m.get("content", "") for m in soup.find_all("meta"))

                    hay_marca = bool(
                        brand_pattern.search(title)
                        or brand_pattern.search(metas)
                        or brand_pattern.search(text)
                    )
                    return hay_marca
        except Exception as e:
            logger.debug(f"Error checking {url}: {e}")
        return False



    async def validate_urls(self, urls, brand_pattern: re.Pattern):
        """Filtra solo las URLs cuya página parezca ser de la marca."""
        valid = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.check_url(session, u, brand_pattern) for u in urls[:20]]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            for u, ok in zip(urls[:20], results):
                if ok:
                    valid.append(u)
        return valid

    async def find_competitor_urls(self, competitor: str, country: str):
        logger.info(f"Searching URLs for {competitor} ({country})")
        brand_pattern = self.build_brand_pattern(competitor)

        async with aiohttp.ClientSession() as session:
            found_domains = await self.search_duckduckgo(session, competitor, country)

        if not found_domains:
            logger.warning(f"No real search results for {competitor}, using fallback")
            found_domains = self.generate_heuristics(competitor, country)

        # prepara candidatos con paths típicos
        base_candidates = found_domains[:5]  # un poco más amplio
        urls = []
        for d in base_candidates:
            d = d.rstrip("/")
            urls.append(d)
            for path in ["/promotions", "/offers", "/bonuses", "/welcome-bonus"]:
                urls.append(d + path)

        valid = await self.validate_urls(urls, brand_pattern)

        # Deriva los main válidos de los válidos (dominios base)
        valid_main = sorted({u.split("/", 3)[0] + "//" + urlparse(u).netloc for u in valid})

        logger.info(f"✅ Found {len(valid)} valid URLs for {competitor}")
        return {
            "main_urls": valid_main or base_candidates,  # si nada pasa el filtro, devuelve candidatos para depurar
            "promotion_urls": [u for u in valid if any(u.startswith(m) for m in valid_main)] or [],
        }


import subprocess
import time
import logging

logger = logging.getLogger(__name__)

NORDVPN_COUNTRIES = {
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "KW": "Kuwait",
    "QA": "Qatar",
    "OM": "Oman",
    "BH": "Bahrain",
    "JO": "Jordan",
    "NZ": "New Zealand",
}

def get_vpn_config(country: str):
    """Connect to NordVPN (Windows app version)"""
    try:
        nord_country = NORDVPN_COUNTRIES.get(country.upper(), country)
        logger.info(f"🔄 Connecting to NordVPN GUI for {nord_country}...")

        # Launch connection via Windows PowerShell (requires app installed)
        cmd = f'powershell.exe -Command "Start-Process \\"nordvpn://{nord_country}\\""'
        subprocess.run(cmd, shell=True)
        time.sleep(8)  # wait for connection

        logger.info(f"✅ Attempted VPN connection to {nord_country} (check NordVPN app)")
        return True

    except Exception as e:
        logger.error(f"Error connecting to NordVPN app: {e}")
        return False

    subprocess.run('powershell.exe -Command "Start-Process nordvpn://disconnect"', shell=True)

