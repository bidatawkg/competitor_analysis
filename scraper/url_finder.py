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

    # import requests

    # def verify_vpn_connection():
    #     try:
    #         ip_data = requests.get("https://ipapi.co/json/", timeout=10).json()
    #         country = ip_data.get("country")
    #         logging.info(f"🌍 Current IP country after VPN: {country}")
    #         return country
    #     except Exception as e:
    #         logging.error(f"VPN check failed: {e}")
    #         return None


    # async def check_url(self, session, url, brand_pattern: re.Pattern):
    #     """
    #     Verifica si una URL realmente pertenece a la marca.
    #     Más tolerante con redirecciones, tiempos lentos y falsos negativos.
    #     """
    #     headers = {
    #         "User-Agent": (
    #             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #             "AppleWebKit/537.36 (KHTML, like Gecko) "
    #             "Chrome/122.0.0.0 Safari/537.36"
    #         ),
    #         "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    #         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    #         "Accept-Encoding": "gzip, deflate, br",
    #         "Connection": "keep-alive",
    #     }

    #     try:
    #         async with session.get(
    #             url, timeout=25, allow_redirects=True, headers=headers, ssl=False
    #         ) as resp:
    #             # Validación de tipo y status
    #             if resp.status >= 400:
    #                 logger.debug(f"❌ {url} returned status {resp.status}")
    #                 return False

    #             ctype = resp.headers.get("Content-Type", "")
    #             if "text/html" not in ctype:
    #                 return False

    #             # Obtiene texto completo
    #             try:
    #                 text = await resp.text(errors="ignore")
    #             except Exception:
    #                 return False

    #             if len(text) < 150:  # 👈 reduce el umbral
    #                 logger.debug(f"⚠️ Skipping short response from {url}")
    #                 return False

    #             # Analiza HTML
    #             soup = BeautifulSoup(text, "html.parser")
    #             title = (soup.title.string or "") if soup.title else ""
    #             metas = " ".join(m.get("content", "") for m in soup.find_all("meta"))

    #             hay_marca = bool(
    #                 brand_pattern.search(title)
    #                 or brand_pattern.search(metas)
    #                 or brand_pattern.search(text)
    #             )

    #             if hay_marca:
    #                 # Log adicional para debug
    #                 final_url = str(resp.url)
    #                 logger.info(f"✅ Valid brand URL found: {final_url}")
    #                 return True
    #             else:
    #                 # Segunda oportunidad: si dominio coincide parcialmente
    #                 if re.search(brand_pattern, url):
    #                     logger.info(f"✅ Domain name matches brand for {url}")
    #                     return True

    #     except asyncio.TimeoutError:
    #         logger.debug(f"⏱️ Timeout checking {url}")
    #     except Exception as e:
    #         logger.debug(f"❌ Error checking {url}: {e}")

    #     return False


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

    logger = logging.getLogger(__name__)

    # ============================================================
    # ✅ Fallback URL generator — genera dominios más realistas
    # ============================================================
    def generate_fallback_urls(brand_name: str):
        """
        Genera posibles URLs para una marca cuando no hay resultados en buscadores.
        Amplía el rango de dominios (.com, .ae, .net, .io, .bet, .org, .co, .biz).
        """
        clean_name = brand_name.lower().replace(" ", "").replace("-", "")
        fallback_domains = [".ae", ".com", ".net", ".io", ".bet", ".org", ".co", ".biz"]

        urls = []
        for ext in fallback_domains:
            urls.append(f"https://{clean_name}{ext}")
            urls.append(f"https://www.{clean_name}{ext}")
            # También prueba con dominio secundario tipo "casino"
            urls.append(f"https://{clean_name}casino{ext}")
            urls.append(f"https://www.{clean_name}casino{ext}")

        # Elimina duplicados manteniendo el orden
        return list(dict.fromkeys(urls))


    # ============================================================
    # ✅ Robust URL checker — versión mejorada y tolerante
    # ============================================================
    async def check_url(self, session, url, brand_pattern: re.Pattern):
        """
        Verifica si una URL realmente pertenece a la marca.
        Más tolerante con redirecciones, tiempos lentos y falsos negativos.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        try:
            async with session.get(
                url, timeout=25, allow_redirects=True, headers=headers, ssl=False
            ) as resp:
                # Validación de tipo y status
                if resp.status >= 400:
                    logger.debug(f"❌ {url} returned status {resp.status}")
                    return False

                ctype = resp.headers.get("Content-Type", "")
                if "text/html" not in ctype:
                    logger.debug(f"⚠️ Non-HTML content at {url} ({ctype})")
                    return False

                # Obtiene texto completo
                try:
                    text = await resp.text(errors="ignore")
                except Exception:
                    logger.debug(f"⚠️ Could not read text from {url}")
                    return False

                # Umbral relajado
                if len(text) < 150:
                    logger.debug(f"⚠️ Short response from {url} ({len(text)} chars)")
                    return False

                # Analiza HTML
                soup = BeautifulSoup(text, "html.parser")
                title = (soup.title.string or "") if soup.title else ""
                metas = " ".join(m.get("content", "") for m in soup.find_all("meta"))

                hay_marca = bool(
                    brand_pattern.search(title)
                    or brand_pattern.search(metas)
                    or brand_pattern.search(text)
                )

                if hay_marca:
                    final_url = str(resp.url)
                    logger.info(f"✅ Valid brand URL found: {final_url}")
                    return True
                else:
                    # Segunda oportunidad: dominio con coincidencia directa
                    if re.search(brand_pattern, url):
                        logger.info(f"✅ Domain name matches brand for {url}")
                        return True

        except asyncio.TimeoutError:
            logger.debug(f"⏱️ Timeout checking {url}")
        except Exception as e:
            logger.debug(f"❌ Error checking {url}: {e}")

        return False


    # ============================================================
    # 🧪 Helper to validate multiple URLs in batch (optional)
    # ============================================================
    async def validate_urls_for_brand(self, brand_name, urls, brand_pattern):
        """
        Comprueba en paralelo qué URLs del fallback o buscador son válidas.
        """
        valid_urls = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.check_url(session, u, brand_pattern) for u in urls]
            results = await asyncio.gather(*tasks)
            for url, is_valid in zip(urls, results):
                if is_valid:
                    valid_urls.append(url)

        logger.info(f"🌐 {brand_name}: {len(valid_urls)} valid URLs found → {valid_urls}")
        return valid_urls



# import subprocess
# import time

# logger = logging.getLogger(__name__)

# NORDVPN_COUNTRIES = {
#     "AE": "United Arab Emirates",
#     "SA": "Saudi Arabia",
#     "KW": "Kuwait",
#     "QA": "Qatar",
#     "OM": "Oman",
#     "BH": "Bahrain",
#     "JO": "Jordan",
#     "NZ": "New Zealand",
# }

# import requests

# # Caché simple para no consultar IP en cada ejecución
_last_vpn_check = {"time": 0, "ip": None, "country": None, "country_code": None}

def verify_vpn_connection(force_check: bool = False):
    """
    Comprueba la IP actual y el país asociado tras conectar NordVPN.
    Usa ipwho.is (más estable que ipapi.co) y cachea los resultados 5 minutos.
    """
    global _last_vpn_check
    now = time.time()

    # Si el último chequeo fue hace menos de 5 min, usa el caché
    if not force_check and (now - _last_vpn_check["time"] < 300):
        cached_country = _last_vpn_check["country"]
        cached_code = _last_vpn_check["country_code"]
        if cached_country and cached_code:
            logger.info(f"🌍 [Cached VPN] {cached_country} [{cached_code}] ({_last_vpn_check['ip']})")
            return cached_code

    try:
        resp = requests.get("https://ipwho.is/", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            ip = data.get("ip")
            country = data.get("country")
            country_code = data.get("country_code")

            if ip and country:
                _last_vpn_check.update({
                    "time": now,
                    "ip": ip,
                    "country": country,
                    "country_code": country_code
                })
                logger.info(f"🌍 VPN IP check → {ip} ({country}) [{country_code}]")
                return country_code
            else:
                logger.warning("⚠️ VPN verification returned incomplete data.")
                return None
        else:
            logger.warning(f"⚠️ IP check returned status {resp.status_code}")
            return None

    except Exception as e:
        logger.error(f"VPN verification failed: {e}")
        return None


# import subprocess
# import time

# def get_vpn_config(country: str, max_retries: int = 3):
#     """
#     Conecta a NordVPN usando el CLI (más fiable que GUI).
#     Verifica la IP tras conectar y reintenta si no coincide con el país deseado.
#     """
#     try:
#         nord_country = NORDVPN_COUNTRIES.get(country.upper(), country)
#         logger.info(f"🔄 Connecting to NordVPN CLI for {nord_country}...")

#         for attempt in range(1, max_retries + 1):
#             try:
#                 # Desconecta primero por si ya hay sesión activa
#                 subprocess.run(["nordvpn", "disconnect"], capture_output=True, text=True)

#                 # Conecta al país
#                 cmd = ["nordvpn", "connect", nord_country]
#                 result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

#                 if result.returncode != 0:
#                     logger.warning(f"⚠️ CLI connect command failed: {result.stderr.strip()}")
#                 else:
#                     logger.info(f"✅ CLI output: {result.stdout.strip()}")

#             except FileNotFoundError:
#                 logger.error(
#                     "❌ NordVPN CLI not found. Please ensure NordVPN is installed and added to PATH."
#                 )
#                 return False

#             # Espera más tiempo en cada intento
#             wait_time = 10 + (attempt - 1) * 5
#             logger.info(f"⏳ Waiting {wait_time}s for VPN connection to stabilize...")
#             time.sleep(wait_time)

#             detected_country = verify_vpn_connection(force_check=True)
#             if detected_country and detected_country.upper() == country.upper():
#                 logger.info(f"✅ Connected successfully to {nord_country} via CLI (VPN active)")
#                 return True
#             else:
#                 logger.warning(
#                     f"⚠️ Attempt {attempt}: VPN still not in {country} "
#                     f"(current: {detected_country or 'unknown'}). Retrying..."
#                 )

#         logger.error(f"❌ Could not establish VPN in {country} after {max_retries} attempts.")
#         return False

#     except Exception as e:
#         logger.error(f"Error in VPN CLI connection: {e}")
#         return False



import subprocess
import time
import os
import logging
import requests

logger = logging.getLogger(__name__)

VPN_CONFIG_PATH = r"C:\Users\krilo\Documents\TRABAJO\NUEVOS COMPETIDORES\FINAL\competitor_analysis\VPN"  # donde guardas tus .ovpn
VPN_PROCESS = None

def connect_cyberghost(country: str, max_retries: int = 3):
    """
    Conecta a CyberGhost usando OpenVPN y un archivo .ovpn específico del país.
    """
    global VPN_PROCESS

    ovpn_file = os.path.join(VPN_CONFIG_PATH, f"{country.upper()}.ovpn")
    if not os.path.exists(ovpn_file):
        logger.error(f"❌ No se encontró el archivo .ovpn para {country}: {ovpn_file}")
        return False

    # Cierra conexiones previas
    disconnect_cyberghost()

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔄 Conectando a CyberGhost (OpenVPN) para {country} (intento {attempt})...")

            # Lanza el proceso OpenVPN como servicio
            VPN_PROCESS = subprocess.Popen(
                ["openvpn", "--config", ovpn_file, "--auth-nocache", "--log", "openvpn.log"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # Espera a que se conecte
            wait_time = 15 + (attempt - 1) * 5
            logger.info(f"⏳ Esperando {wait_time}s para estabilizar conexión...")
            time.sleep(wait_time)

            detected_country = verify_vpn_connection(force_check=True)
            if detected_country and detected_country.upper() == country.upper():
                logger.info(f"✅ VPN conectada correctamente a {country}")
                return True
            else:
                logger.warning(f"⚠️ VPN aún no está en {country} (actual: {detected_country or 'desconocido'}). Reintentando...")
                disconnect_cyberghost()

        except Exception as e:
            logger.error(f"Error conectando VPN: {e}")

    logger.error(f"❌ No se pudo establecer VPN en {country} después de {max_retries} intentos.")
    return False


def disconnect_cyberghost():
    """
    Cierra cualquier conexión activa de OpenVPN.
    """
    global VPN_PROCESS
    try:
        subprocess.run(["taskkill", "/IM", "openvpn.exe", "/F"], capture_output=True)
        VPN_PROCESS = None
        logger.info("🔌 Desconectado de CyberGhost (OpenVPN).")
    except Exception as e:
        logger.error(f"Error al desconectar VPN: {e}")

