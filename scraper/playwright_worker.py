import sys
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Configura logging del worker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]  # logs -> stderr
)

def scrape_with_playwright(competitor_name, url, country, search_terms):
    promotions = []
    try:
        logging.info(f"[Worker] Starting Playwright scrape: {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="Asia/Riyadh"
            )
            page = context.new_page()
            page.goto(url, timeout=30000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Estrategia básica: busca coincidencias de términos en el texto
            text = soup.get_text(separator=" ", strip=True).lower()
            for term in search_terms:
                if term.lower() in text:
                    snippet = text[text.find(term.lower()): text.find(term.lower()) + 150]
                    promotions.append({
                        "competitor": competitor_name,
                        "country": country,
                        "title": f"Found '{term}' on page",
                        "description": snippet,
                        "bonus_amount": "",
                        "bonus_type": "Other",
                        "conditions": "",
                        "valid_until": "",
                        "url": url,
                        "scraped_at": datetime.now().isoformat(),
                        "hash_id": str(hash(snippet + url))
                    })

            page.close()
            context.close()
            browser.close()

        logging.info(f"[Worker] Extracted {len(promotions)} promotions from {url}")
    except Exception as e:
        logging.error(f"[Worker] Error scraping {url}: {e}", exc_info=True)

    return promotions


if __name__ == "__main__":
    if len(sys.argv) < 5:
        logging.error("Usage: python playwright_worker.py <competitor_name> <url> <country> <search_terms>")
        sys.exit(1)

    competitor_name = sys.argv[1]
    url = sys.argv[2]
    country = sys.argv[3]
    search_terms = sys.argv[4].split(",")

    results = scrape_with_playwright(competitor_name, url, country, search_terms)

    # Siempre imprime JSON válido a stdout (aunque esté vacío)
    print(json.dumps(results, ensure_ascii=False))
