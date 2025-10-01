#!/usr/bin/env python3
"""
Competitor Analysis Scraper for YYY Casino
Scrapes competitor casino websites for bonuses, promotions, and offers
"""

import csv
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import re
from urllib.parse import urljoin, urlparse
import time
import random
import concurrent.futures
import subprocess, json, sys


# from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from bs4 import BeautifulSoup
import aiohttp
from pathlib import Path

from .url_finder import URLFinder, get_vpn_config

import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# from dotenv import load_dotenv  # Optional dependency
# load_dotenv()  # Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CompetitorInfo:
    """Data class for competitor information"""
    name: str
    country: str
    url: str
    search_terms: List[str]

@dataclass
class PromotionData:
    """Data class for promotion/bonus data"""
    competitor: str
    country: str
    title: str
    description: str
    bonus_amount: str
    bonus_type: str
    conditions: str
    valid_until: str
    url: str
    scraped_at: str
    hash_id: str

class CompetitorScraper:
    """Main scraper class for competitor analysis"""
    
    def __init__(self, use_proxy: bool = True, headless: bool = True):
        self.use_proxy = use_proxy
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
         # Initialize URL Finder
        self.url_finder = URLFinder()  # Add this line
        
        # UAE proxy servers (free proxies for testing - replace with premium VPN service)
        # self.uae_proxies = [
            # {"server": "http://185.38.111.1:8080"},
            # {"server": "http://188.166.125.206:41124"},
            # {"server": "http://134.195.101.34:8080"}
        # ]
        
        # Competitors configuration
        self.competitors = {
            "AE": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "SA": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "betfinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1x bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "KW": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "QA": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "OM": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "BH": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "JO": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "betfinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "1x bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ],
            "NZ": [
                {"name": "Jackpot City", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Wildz", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "Spincasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "luckynuggetcasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "skycitycasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "leovegas", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "betvictor", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "christchurchcasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},                
                {"name": "highroller", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]},
                {"name": "casumo", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]}
            ]
        }

    async def setup_browser(self, proxy: Optional[Dict] = None) -> None:
        logger.info("setup_browser skipped (Playwright runs in executor)")

        
        
    # async def setup_browser(self, proxy: Optional[Dict] = None) -> None:
    #     """Setup browser with proxy configuration"""
    #     try:
    #         playwright = await async_playwright().start()
            
    #         browser_args = {
    #             'headless': self.headless,
    #             'args': [
    #                 '--no-sandbox',
    #                 '--disable-blink-features=AutomationControlled',
    #                 '--disable-web-security',
    #                 '--disable-features=VizDisplayCompositor',
    #                 '--disable-dev-shm-usage',
    #                 '--disable-gpu',
    #                 '--disable-software-rasterizer'
    #             ]
    #         }
            
    #         if proxy and self.use_proxy:
    #             browser_args['proxy'] = proxy
    #             logger.info(f"Using proxy: {proxy['server']}")
                
    #         self.browser = await playwright.chromium.launch(**browser_args)
            
    #         # Create context with stealth settings
    #         context_args = {
    #             'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    #             'viewport': {'width': 1920, 'height': 1080},
    #             'locale': 'en-US',
    #             'timezone_id': 'Asia/Dubai',
    #             'ignore_https_errors': True
    #         }
            
    #         self.context = await self.browser.new_context(**context_args)
            
    #         # Add stealth scripts
    #         await self.context.add_init_script("""
    #             Object.defineProperty(navigator, 'webdriver', {
    #                 get: () => undefined,
    #             });
                
    #             Object.defineProperty(navigator, 'plugins', {
    #                 get: () => [1, 2, 3, 4, 5],
    #             });
                
    #             Object.defineProperty(navigator, 'languages', {
    #                 get: () => ['en-US', 'en'],
    #             });
    #         """)
            
    #         logger.info("Browser setup completed successfully")
            
    #     except Exception as e:
    #         logger.error(f"Browser setup failed: {e}")
    #         raise
        
    async def close_browser(self) -> None:
        """Close browser and context"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
            
    async def find_competitor_urls(self, competitor: Dict) -> List[str]:
        """Find actual URLs for competitor using AI"""
        try:
            # Use AI to find URLs
            url_result = await self.url_finder.find_competitor_urls(
                competitor["name"], 
                self.current_country
            )
            
            # Combine main and promotion URLs
            all_urls = url_result['main_urls'] + url_result['promotion_urls']
            
            if all_urls:
                logger.info(f"Found {len(all_urls)} URLs for {competitor['name']}")
                for url in all_urls:
                    print(url)                    
                return all_urls
            else:
                logger.warning(f"No URLs found for {competitor['name']}")
                return []
                
        except Exception as e:
            logger.error(f"Error finding URLs for {competitor['name']}: {e}")
            return []

        
    async def scrape_promotions(self, competitor: CompetitorInfo, urls: List[str]) -> List[PromotionData]:
        """Scrape promotions from competitor URLs"""
        promotions = []
        
        for url in urls:
            try:
                page = await self.context.new_page()
                
                # Navigate to page
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Handle cookie banners and popups
                await self.handle_popups(page)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract promotions using multiple strategies
                page_promotions = await self.extract_promotions_from_page(
                    soup, competitor, url
                )
                
                promotions.extend(page_promotions)
                logger.info(f"Extracted {len(page_promotions)} promotions from {url}")
                
                await page.close()
                await asyncio.sleep(random.uniform(2, 5))  # Random delay
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
                
        return promotions
        
    async def handle_popups(self, page: Page) -> None:
        """Handle common popups and cookie banners"""
        popup_selectors = [
            '[data-testid="cookie-banner"] button',
            '.cookie-banner button',
            '.cookie-consent button',
            '[class*="cookie"] button[class*="accept"]',
            '[class*="popup"] button[class*="close"]',
            '.modal button[class*="close"]',
            '[aria-label*="close"]',
            '[aria-label*="dismiss"]'
        ]
        
        for selector in popup_selectors:
            try:
                await page.click(selector, timeout=2000)
                await page.wait_for_timeout(1000)
                logger.debug(f"Closed popup with selector: {selector}")
            except:
                continue
                
    async def extract_promotions_from_page(self, soup: BeautifulSoup, competitor: CompetitorInfo, url: str) -> List[PromotionData]:
        """Extract promotion data from page content"""
        promotions = []
        current_time = datetime.now().isoformat()
        
        # Common selectors for promotions
        promotion_selectors = [
            '.promotion', '.bonus', '.offer', '.promo',
            '[class*="promotion"]', '[class*="bonus"]', '[class*="offer"]',
            '.card', '.tile', '.item', '[class*="card"]'
        ]
        
        promotion_elements = []
        for selector in promotion_selectors:
            elements = soup.select(selector)
            promotion_elements.extend(elements)
            
        # Remove duplicates
        seen_texts = set()
        unique_elements = []
        for elem in promotion_elements:
            text = elem.get_text(strip=True)[:100]  # First 100 chars as identifier
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_elements.append(elem)
                
        logger.info(f"Found {len(unique_elements)} potential promotion elements")
        
        for element in unique_elements:
            try:
                promotion = self.parse_promotion_element(element, competitor, url, current_time)
                if promotion:
                    promotions.append(promotion)
            except Exception as e:
                logger.debug(f"Error parsing promotion element: {e}")
                continue
                
        # If no structured promotions found, try text extraction
        if not promotions:
            promotions = self.extract_promotions_from_text(soup, competitor, url, current_time)
            
        return promotions

    # def scrape_competitor_promotions_sync(self, competitor_name: str, url: str, country: str) -> List[PromotionData]:
    #     """Scrape synchronously using sync_playwright (works better on Windows)"""
    #     promotions = []
    #     try:
    #         with sync_playwright() as p:
    #             proxy_config = None
    #             vpn_config = get_vpn_config(country)
    #             if vpn_config and vpn_config.get("proxies"):
    #                 proxy = vpn_config["proxies"][0]
    #                 proxy_config = {
    #                     "server": proxy["server"],
    #                     "username": proxy.get("username"),
    #                     "password": proxy.get("password")
    #                 }

    #             browser = p.chromium.launch(headless=True, proxy=proxy_config)
    #             context = browser.new_context(
    #                 user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #                         "AppleWebKit/537.36 (KHTML, like Gecko) "
    #                         "Chrome/120.0.0.0 Safari/537.36",
    #                 viewport={"width": 1920, "height": 1080},
    #                 locale="en-US",
    #                 timezone_id="Asia/Riyadh"
    #             )
    #             page = context.new_page()
    #             page.goto(url, timeout=30000)

    #             html = page.content()
    #             soup = BeautifulSoup(html, "html.parser")

    #             # Reusa tu lógica existente de extracción
    #             competitor_stub = CompetitorInfo(
    #                 name=competitor_name, country=country, url=url,
    #                 search_terms=["bonus", "promotion", "welcome", "free", "deposit"]
    #             )
    #             promotions = self.extract_promotions_from_text(
    #                 soup, competitor_stub, url, datetime.now().isoformat()
    #             )

    #             browser.close()
    #     except Exception as e:
    #         logger.error(f"Sync scraping failed for {url}: {e}")
    #     return promotions


    def parse_promotion_element(self, element, competitor: CompetitorInfo, url: str, current_time: str) -> Optional[PromotionData]:
        """Parse individual promotion element"""
        try:
            # Extract text content
            text = element.get_text(separator=' ', strip=True)
            
            # Skip if too short or irrelevant
            if len(text) < 20 or not any(term in text.lower() for term in competitor.search_terms):
                return None
                
            # Extract title (usually in headings or first line)
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            title = title_elem.get_text(strip=True) if title_elem else text.split('.')[0][:100]
            
            # Extract bonus amount using regex
            bonus_amount = self.extract_bonus_amount(text)
            
            # Extract bonus type
            bonus_type = self.extract_bonus_type(text)
            
            # Extract conditions
            conditions = self.extract_conditions(text)
            
            # Extract validity
            valid_until = self.extract_validity(text)
            
            # Create hash for deduplication
            hash_content = f"{competitor['name']}_{title}_{bonus_amount}_{bonus_type}"
            hash_id = str(hash(hash_content))
            
            return PromotionData(
                competitor=competitor['name'],
                country=competitor.country,
                title=title,
                description=text[:500],  # Limit description length
                bonus_amount=bonus_amount,
                bonus_type=bonus_type,
                conditions=conditions,
                valid_until=valid_until,
                url=url,
                scraped_at=current_time,
                hash_id=hash_id
            )
            
        except Exception as e:
            logger.debug(f"Error parsing promotion element: {e}")
            return None
            
    def extract_bonus_amount(self, text: str) -> str:
        """Extract bonus amount from text"""
        # Patterns for bonus amounts
        patterns = [
            r'(\$\d+(?:,\d{3})*(?:\.\d{2})?)',  # $100, $1,000.00
            r'(€\d+(?:,\d{3})*(?:\.\d{2})?)',   # €100
            r'(\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|AED))',  # 100 USD
            r'(\d+%)',  # 100%
            r'(\d+\s*free\s*spins?)',  # 50 free spins
            r'(up\s+to\s+\$?\d+(?:,\d{3})*)',  # up to $1000
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return ""
        
    def extract_bonus_type(self, text: str) -> str:
        """Extract bonus type from text"""
        text_lower = text.lower()
        
        if 'welcome' in text_lower:
            return 'Welcome Bonus'
        elif 'deposit' in text_lower:
            return 'Deposit Bonus'
        elif 'free spin' in text_lower:
            return 'Free Spins'
        elif 'cashback' in text_lower:
            return 'Cashback'
        elif 'reload' in text_lower:
            return 'Reload Bonus'
        elif 'tournament' in text_lower:
            return 'Tournament'
        elif 'no deposit' in text_lower:
            return 'No Deposit Bonus'
        else:
            return 'Other'
            
    def extract_conditions(self, text: str) -> str:
        """Extract bonus conditions from text"""
        condition_keywords = [
            'wagering', 'playthrough', 'rollover', 'minimum deposit',
            'max bet', 'game restrictions', 'time limit', 'terms apply'
        ]
        
        conditions = []
        text_lower = text.lower()
        
        for keyword in condition_keywords:
            if keyword in text_lower:
                # Try to extract sentence containing the keyword
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        conditions.append(sentence.strip())
                        break
                        
        return '; '.join(conditions[:3])  # Limit to 3 conditions
        
    def extract_validity(self, text: str) -> str:
        """Extract validity period from text"""
        # Patterns for dates and validity
        patterns = [
            r'valid\s+until\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'expires?\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{1,2}\s+days?)',
            r'limited\s+time',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
                
        return ""
        
    def extract_promotions_from_text(self, soup: BeautifulSoup, competitor: CompetitorInfo, url: str, current_time: str) -> List[PromotionData]:
        """Extract promotions from general page text when structured data not found"""
        print("AQUÍ ESTÁ ENTRANDO EN EL fROM TEXT *********************")
        promotions = []
        
        # Get all text content
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Split into paragraphs and sentences
        paragraphs = text_content.split('\n')
        
        for paragraph in paragraphs:
            if len(paragraph) < 50:  # Skip short paragraphs
                continue
                
            # Check if paragraph contains promotion keywords
            if any(term in paragraph.lower() for term in competitor.search_terms):
                # Extract bonus amount
                bonus_amount = self.extract_bonus_amount(paragraph)
                
                if bonus_amount:  # Only create promotion if we found a bonus amount
                    title = paragraph.split('.')[0][:100]  # First sentence as title
                    
                    hash_content = f"{competitor['name']}_{title}_{bonus_amount}"
                    hash_id = str(hash(hash_content))
                    
                    promotion = PromotionData(
                        competitor=competitor['name'],
                        country=competitor.country,
                        title=title,
                        description=paragraph[:500],
                        bonus_amount=bonus_amount,
                        bonus_type=self.extract_bonus_type(paragraph),
                        conditions=self.extract_conditions(paragraph),
                        valid_until=self.extract_validity(paragraph),
                        url=url,
                        scraped_at=current_time,
                        hash_id=hash_id
                    )
                    
                    promotions.append(promotion)
                    
        return promotions[:10]  # Limit to 10 promotions per page
    
    # async def scrape_competitor_promotions(self, competitor_name: str, url: str, country: str) -> List[PromotionData]:
    #     """Scrape promotions from a specific competitor URL"""
    #     print("AQUÍ ESTÁ ENTRANDO EN EL SCRAPE_COMPETITOR_PROMOTIONS *********************")
    #     promotions = []
        
    #     try:
    #         async with async_playwright() as p:
    #             # Configure browser with VPN if available
    #             browser_args = ['--no-sandbox', '--disable-dev-shm-usage']
                
    #             # Add proxy configuration if available
    #             vpn_config = get_vpn_config(country)
    #             print("ESTO ES LO QUE TIENE VPN CONFIG *************************")
    #             print(vpn_config)
    #             proxy_config = None
    #             if vpn_config and vpn_config.get('proxies'):
    #                 print("ENTRA EN EL IF *************************")
    #                 proxy = vpn_config['proxies'][0]  # Use first proxy
    #                 proxy_config = {
    #                     'server': proxy['server'],
    #                     'username': proxy.get('username'),
    #                     'password': proxy.get('password')
    #                 }
                
    #             browser = await p.chromium.launch(
    #                 headless=True,
    #                 args=browser_args,
    #                 proxy=proxy_config
    #             )
                
    #             context = await browser.new_context(
    #                 user_agent=random.choice(self.user_agents),
    #                 viewport={'width': 1920, 'height': 1080},
    #                 locale='en-US',
    #                 timezone_id=self._get_timezone_for_country(country)
    #             )
                
    #             page = await context.new_page()
                
    #             try:
    #                 # Navigate to URL
    #                 await page.goto(url, wait_until='networkidle', timeout=30000)
    #                 await asyncio.sleep(random.uniform(2, 4))
                    
    #                 # Handle popups and cookies
    #                 await self._handle_popups(page)
                    
    #                 # Extract promotions
    #                 promotions_data = await self._extract_promotions_from_page(page, competitor_name, country)
    #                 promotions.extend(promotions_data)
                    
    #             except Exception as e:
    #                 logger.error(f"Error scraping {url}: {e}")
                    
    #             finally:
    #                 await browser.close()
                    
    #     except Exception as e:
    #         logger.error(f"Error setting up browser for {url}: {e}")
            
    #     return promotions

    async def scrape_competitor_promotions(self, competitor_name: str, url: str, country: str) -> List[PromotionData]:
        try:
            worker_path = Path(__file__).parent / "playwright_worker.py"

            # 🔹 En Windows usamos subprocess.run en lugar de asyncio
            if sys.platform.startswith("win"):
                proc = subprocess.run(
                    [sys.executable, str(worker_path), competitor_name, url, country,
                    ",".join(["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"])],
                    capture_output=True,
                    text=True
                )
                if proc.stdout:
                    logger.info(f"Worker raw stdout for {url}:\n{proc.stdout.strip()}")
                    try:
                        data = json.loads(proc.stdout.strip())
                        return [PromotionData(**p) for p in data]
                    except Exception as e:
                        logger.error(f"JSON parse failed for {url}: {e}\nOutput was:\n{proc.stdout}")
                if proc.stderr:
                    logger.error(f"Worker stderr for {url}:\n{proc.stderr}")
                return []

            # 🔹 En Linux/macOS mantenemos asyncio
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(worker_path),
                competitor_name, url, country,
                ",".join(["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament"]),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if stdout:
                raw_out = stdout.decode().strip()
                logger.info(f"Worker raw stdout for {url}:\n{raw_out}")
                try:
                    data = json.loads(raw_out)
                    return [PromotionData(**p) for p in data]
                except Exception as e:
                    logger.error(f"JSON parse failed for {url}: {e}\nOutput was:\n{raw_out}")

            if stderr:
                logger.error(f"Worker stderr for {url}:\n{stderr.decode()}")

            return []
        except Exception as e:
            logger.error(f"Subprocess wrapper crashed for {url}: {e}", exc_info=True)
            return []


        
        
    async def scrape_all_competitors(self, country: str) -> List[PromotionData]:
        """Scrape all competitors for a country with fallback options"""
        logger.info(f"AQUÍ ESTÁ ENTRANDO EN EL SCRAPE_ALL_COMPETITORS *********************")
        self.current_country = country
        all_promotions = []
        
        if country not in self.competitors:
            logger.error(f"Country {country} not configured")
            return []
            
        competitors = self.competitors[country]
        logger.info(f"Starting to scrape {len(competitors)} competitors in {country}")
        
        try:
            # Try async browser setup first            
            # proxy = random.choice(self.uae_proxies) if self.use_proxy else None
            # logger.info(f"se pone a usar lo de los proxies parece ..... proxies de uae cosa rara: {proxy}")
            # await self.setup_browser(proxy)

            # Try async browser setup first using VPN config
            vpn_config = get_vpn_config(country)
            proxy = None
            if vpn_config and vpn_config.get("proxies"):
                proxy = vpn_config["proxies"][0]  # Usamos el primer proxy disponible
                logger.info(f"Using proxy for {country}: {proxy}")
            else:
                logger.info(f"No proxy configured for {country}, running without proxy")

            await self.setup_browser(proxy)

            
            for competitor in competitors:
                try:
                    print("entra en el bucle de competitors")
                    print(competitor)
                    logger.info(f"Scraping {competitor['name']}...")
                    
                    # Find URLs for this competitor
                    urls = await self.find_competitor_urls(competitor)
                    
                    if not urls:
                        logger.warning(f"No URLs found for {competitor['name']}, skipping...")
                        continue
                        
                    # Scrape each URL
                    for url in urls:
                        try:
                            logger.info(f"Scraping URL: {url}")
                            promotions = await self.scrape_competitor_promotions(competitor['name'], url, country)
                            all_promotions.extend(promotions)
                            
                            await asyncio.sleep(random.uniform(2, 5))
                            
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error scraping competitor {competitor['name']}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Async scraping failed, using fallback: {e}")
            # Fallback to simple requests-based scraping
            all_promotions = await self.fallback_scraping(competitors, country)
                    
        finally:
            # Always close browser
            await self.close_browser()
                
        logger.info(f"Total promotions scraped: {len(all_promotions)}")
        return all_promotions
    
    async def fallback_scraping(self, competitors: List[Dict], country: str) -> List[PromotionData]:
        """Fallback scraping using requests"""
        import aiohttp
        
        all_promotions = []
        
        async with aiohttp.ClientSession() as session:
            for competitor in competitors:
                try:
                    urls = await self.find_competitor_urls(competitor)
                    
                    for url in urls:
                        try:
                            async with session.get(url, timeout=10) as response:
                                if response.status == 200:
                                    content = await response.text()
                                    soup = BeautifulSoup(content, 'html.parser')
                                    
                                    # Simple text-based extraction
                                    text_content = soup.get_text()
                                    sentences = text_content.split('.')
                                    
                                    for sentence in sentences:
                                        if any(term in sentence.lower() for term in competitor['search_terms']) and len(sentence) > 30:
                                            promotion = PromotionData(
                                                competitor=competitor['name'],
                                                country=country,
                                                title=sentence[:100],
                                                description=sentence[:500],
                                                bonus_amount=self.extract_bonus_amount(sentence),
                                                bonus_type=self.extract_bonus_type(sentence),
                                                conditions='',
                                                valid_until='',
                                                url=url,
                                                scraped_at=datetime.now().isoformat(),
                                                hash_id=str(hash(sentence[:100]))
                                            )
                                            all_promotions.append(promotion)
                                            break  # Only take one promotion per page for fallback
                                            
                        except Exception as e:
                            logger.debug(f"Fallback failed for {url}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Fallback failed for {competitor['name']}: {e}")
                    continue
                    
        return all_promotions


def run_playwright_task(competitor_name, url, country, search_terms):
    """Run Playwright synchronously in a separate process"""
    from playwright.sync_api import sync_playwright
    promotions = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="Asia/Riyadh"
            )
            page = context.new_page()
            page.goto(url, timeout=30000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            competitor_stub = CompetitorInfo(
                name=competitor_name,
                country=country,
                url=url,
                search_terms=search_terms
            )
            promotions = CompetitorScraper.extract_promotions_from_text(
                CompetitorScraper, soup, competitor_stub, url, datetime.now().isoformat()
            )

            page.close()
            context.close()
            browser.close()
    except Exception as e:
        logger.error(f"Playwright sync scraping failed for {url}: {e}")
    return promotions


async def main():
    """Main function to run the scraper"""
    scraper = CompetitorScraper(use_proxy=False, headless=True)  # Disable proxy for testing
    print("AQUÍ ESTÁ ENTRANDO EN EL MAIN *********************")
    
    # Carpeta de salida relativa al script
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)  # crea la carpeta si no existe
    
    try:
        # Scrape UAE competitors
        promotions = await scraper.scrape_all_competitors("UAE")
        
        # Save to JSON
        output_file = output_dir / f"promotions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(p) for p in promotions], f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(promotions)} promotions to {output_file}")
        
        # Print summary
        print(f"\n=== SCRAPING SUMMARY ===")
        print(f"Total promotions found: {len(promotions)}")
        
        for competitor in set(p.competitor for p in promotions):
            count = len([p for p in promotions if p.competitor == competitor])
            print(f"{competitor}: {count} promotions")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        
# if __name__ == "__main__":
#     asyncio.run(main())
