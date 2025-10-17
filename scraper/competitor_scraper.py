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

from .url_finder import URLFinder, connect_cyberghost

import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    stream=sys.stdout,
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# NUEVO: extractor avanzado de wagering
from .wager_extractor import (
    extract_wagering_from_text,
    find_candidate_tc_links,
    to_display_string,
)


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
    wagering: str = ""

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
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            # "AE": [
            #     {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            # ],
            "SA": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "betfinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1x bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            # "SA": [
            #     {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            # ],
            "KW": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            "QA": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            "OM": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            "BH": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "BetFinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1xBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            "JO": [
                {"name": "Rabona", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "888 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "betfinal", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "LuckyDreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "1x bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Casinia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rooster bet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "BetObet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "EmirBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "JustCasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            "NZ": [
                {"name": "Jackpot City", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Wildz", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Spincasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "luckynuggetcasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "skycitycasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "leovegas", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "betvictor", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "christchurchcasino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},                
                {"name": "highroller", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "casumo", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            # "DE": [
            #     {"name": "Locowin", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "Vulkan Vegas", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "Neon54", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "GG.BET", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "ExciteWin", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "Playzilla", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "Ice Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "Casombie", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "Vegadream", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
            #     {"name": "N1 Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            # ],
            "DE": [
                {"name": "NV Casino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Tipico", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Bet365", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Vulcan Vegas", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Merkur", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Lotto24", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Bwin", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Betano", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Wunderino", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Lowen Play", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],
            "AT": [
                {"name": "Win2day", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Admiral", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Bet365", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Bwin", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Tipp3", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Interwetten", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Mr Green", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Cashpoint", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Bet-at-home", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Lottoland", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ],

            "CH": [
                {"name": "Spins of Glory", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Lucky Dreams", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Caspero", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Azurslot", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Dazard", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "SlotsVader", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Rockwin", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "FeliceBet", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "SlotsMafia", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]},
                {"name": "Crowngold", "search_terms": ["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]}
            ]

        }

        # URLs adicionales fijas por país y casino
        self.manual_urls = {
            "DE": {
                "NV Casino": ["https://nv.casino/de", "https://kelleycarter.com/fan-engagement/nv-casino-official-loyalty-program-benefits-and-rewards/"],
                "Tipico": ["https://games.tipico.de/de", "https://sports.tipico.de/en", "https://www.tipico.de/de", "https://sports.tipico.de", "https://sportshandle.com/tipico-sportsbook-cashback-program/", ""],
                "Bet365": ["https://www.bet365.de/#/HO/","https://www.bet365.de/hub/de-de/open-account-offer?affiliate=365_01434640&gad_source=1&gad_campaignid=19720958129&gbraid=0AAAAADOVbuMngrxBrm2Y0lIKeSWKLDvHu&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qVGmrC6mbA0DUJ6yJ5X3OMG40VjmwyZ_ckhL1yVk2MPtAyfmBMnNjxoCX1gQAvD_BwE"],
                "Vulcan Vegas": ["https://vulkanvegas.com/de/category/allgamess","https://vulkanvegas.com/en/loyalty-program", "https://vulkanvegas.com/en/bonuses"],
                "Merkur": ["https://merkur.com/", "https://www.merkurbets.de/de/page/neukundenpaket-slots", "https://www.merkurbets.de/de/page/neukundenbonus?utm_source=google&utm_medium=search&utm_campaign=MERKUR-BETS_%5BDE_Brand_MERKUR-BETS%5D&gad_source=1&gad_campaignid=21163655685&gbraid=0AAAAABTT_92Ynk8QXf3gu4YQdvaIVeGm0&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qVzXjPvtMAxDNc54rF2NPoRy4UHpFQNYZg09dfJnRU6CNFY6--drORoC-3AQAvD_BwE"],
                "Lotto24": ["https://www.lotto24.de/", "https://games.lotto24.de/games/fruits"],
                "Bwin": ["https://www.bwin.de/de/sports?productId=SPORTSBOOK&rurl=https:%2F%2Fsports.bwin.de%2Fde%2Fsports&wm=5193158&tdpeh=19560_14049767752_130930494691_665955561599_kwd-2846598995_e_c&utm_source=search_google&utm_campaign=14049767752&utm_content=665955561599&utm_medium=e&utm_term=bwin&sb=1&gad_source=1&gad_campaignid=14049767752&gbraid=0AAAAADxF3XuZHpUf_fu-oNGcirsf3dpgA&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qQgvjFW3OR0Y-WToB54P8KFiwr3cA_CbOplYPv_R5gRYFXk1eKb20xoCRO0QAvD_BwE", "https://www.bwin.de/de/engage/lan/sports/dach/generic?wm=5193158&tdpeh=19560_14049767752_130930494691_665955561599_kwd-2846598995_e_c&utm_source=search_google&utm_campaign=14049767752&utm_content=665955561599&utm_medium=e&utm_term=bwin&sb=1&gad_source=1&gad_campaignid=14049767752&gbraid=0AAAAADxF3XuZHpUf_fu-oNGcirsf3dpgA&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qQgvjFW3OR0Y-WToB54P8KFiwr3cA_CbOplYPv_R5gRYFXk1eKb20xoCRO0QAvD_BwE", "https://www.bwin.de/de/slots", "https://worldpokerdeals.com/blog/up-to-40-rakeback-in-the-new-bwin-poker-vip-program-rewards", "https://www.bwin.de/de/engage/lan/sports/dach/generic?wm=5193154&tdpeh=19727_14049767473_137228591994_666030521678_kwd-2806259116_e_c&utm_source=search_google&utm_campaign=14049767473&utm_content=666030521678&utm_medium=e&utm_term=bwin%20bonus%20code&sb=1&gad_source=1&gad_campaignid=14049767473&gbraid=0AAAAADxF3XuIJwAbH7SWtkIs738FPUG95&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qc90hghyR9YTwKu0DwR9hpD_o5ht99-GZp0h_nPLHBUDsx3fmutNDRoCQGUQAvD_BwE"],
                "Betano": ["https://www.betano.de/", "https://www.betano.de/slots/", "https://www.betano.de/promotions/", "https://promos.betano.de/slots-bonus-400-merkur-spiele/index.html?btag=a_1318b_2675c_GSN_COMP_CAS_Wunderino&cq_plac=&cq_net=g&cq_pos=&cq_med=&cq_plt=gp&cq_src=google_ads&cq_cmp=19594070076&cq_con=143324282617&cq_term=wunderino%20bonus&gad_source=1&gad_campaignid=19594070076&gbraid=0AAAAAC1-GiMloSW5x9RoChz2Dih7o5Knq&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qQBeYGwd58qGRZC1vndfGQDvQMy8pD8_GhR1IPIhzgnMuuHftU-oqhoCVI0QAvD_BwE"],
                "Wunderino": ["https://www.wunderino.de/de/", "https://www.wunderino.de/de/loyalty/"],
                "Lowen Play": ["https://www.loewen-play.de/", "https://www.loewen-play.de/bonus"],
                # Puedes añadir más si quieres
            },
            "AT": {
                "Win2day": ["https://www.win2day.at/","https://www.win2day.at/promotions-gewinnspiele", "https://www.win2day.at/clubinfo","https://www.win2day.at/promotions-gewinnspiele/casino-promotions"],
                "Admiral": ["https://www.admiral.at/de/promos", "https://www.admiral.at/de/promos?_gl=1*hqhz14*_gcl_aw*R0NMLjE3NjA3MzY3NzMuQ2p3S0NBancwc2ZIQmhCNkVpd0FRdHY1cWExZ0ZUa3VCWnBqQjVFdnE5LTZiYkRLbkZnY3JVWEtZOE00WGVvYTM4S0YzTTd0eWVtd3J4b0NpYlVRQXZEX0J3RQ..*_gcl_au*MTQ2NjYxNzc0OC4xNzYwNzM2Nzcz*_ga*ODkwMjA2OTM2LjE3NjA3MzY3NzM.*_ga_8DHS9YG79Y*czE3NjA3MzY3NzMkbzEkZzEkdDE3NjA3MzY3NzMkajYwJGwwJGg5MTEzMTMyMDQ.", "https://www.admiral.at/en/help-and-contact/bonus-and-rewards/200-euro-newcomer-bonus", ],
                "Bet365": ["https://casino.bet365.com/home", "https://casino.bet365.com/home/de","https://extra.bet365.com/promotions/en"],
                "Bwin": ["https://www.bwin.com/de-at/engage/lan/pm/casino/cas_100b?wm=5360478&tdpeh=10732_19156034100_158302036775_751999043439_kwd-101165957_e_c&utm_source=search_google&utm_campaign=19156034100&utm_content=751999043439&utm_medium=e&utm_term=bet365%20casino&sb=1&gad_source=1&gad_campaignid=19156034100&gbraid=0AAAAADxF3XtEqvmsf3lC9nO3NT08kXmtf&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qQIMbKI8mOwrDV59WDrtwGIDdliOgWcWwFpvED7Y6bSk6y6PIJg_RRoC-IcQAvD_BwE", "https://www.bwin.com/de-at/engage/pub/s/p/games/190000/195/195051_1?wm=4616953&tdpeh=27392_10648535166_132749387759_582833191333_kwd-331291900932_p_c&utm_source=search_google&utm_campaign=10648535166&utm_content=582833191333&utm_medium=p&utm_term=bwin%20online%20casino&sb=1&gad_source=1&gad_campaignid=10648535166&gbraid=0AAAAADxF3XvcwiQdbVmqhrWeR6BGYd9N2&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qUNtLQ3CCjbfNAulypFcu_QcF17NWV9hE0UKdWAlpXauJ4L5-rWMqBoCOxQQAvD_BwE", "https://www.bwin.com/de-at/engage/pub/s/p/sports/we/loyalty_card"],
                "Tipp3": ["https://www.tipp3.at/sportwetten/", "https://www.tipp3.at/sportwetten/ersteinzahlungsbonus", "https://www.tipp3.at/sportwetten/meine-erste-wette"],
                "Interwetten": ["https://www.interwetten.com/de/content/sportsbook/promotions/interwettenboost?UseKeys=true&participate=1&utm_source=deeplink&gclsrc=aw.ds&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qemWUNZ7EZ6N4VlXpW_Gn3JOJb-SRRc7pPiG0kRbusd-QBLFkjcNlxoCCgUQAvD_BwE", "https://www.interwetten.com/de/neukundenbonus?utm_source=deeplink&gclsrc=aw.ds&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qX4bMimbyb9QjqRFW-tHdWdw0UpwaoNV2GV0D364uAZgoY1PyPgWZRoC9uQQAvD_BwE", "https://www.interwetten.de/de/slots", "https://www.interwetten.com/en/content/casino/promotions/reload-bonus"],
                "Mr Green": ["https://www.mrgreen.com/promotions/", "https://www.mrgreen.com/", ""],
                "Cashpoint": ["https://cashpointcasino.at/bonuscode", "https://cashpoint.co.at/en/", "https://cashpointcasino.at"],
                "Bet-at-home": ["https://www.bet-at-home.de/slots", "https://www.bet-at-home.com/de/promotions?btag=59007522-CjwKCAjw0sfHBhB6EiwAQtv5qVVacNmoRpZG9lHVil0-EgZiw9iFIkqZa87jyegz-MIBHvc_lKyWcBoCBhYQAvD_BwE&etcc_med=SEA&etcc_par=Google&etcc_cmp=Brand&etcc_grp=145789558312&etcc_bky=bet%20at%20home&etcc_mty=p&etcc_plc=&etcc_ctv=744616064597&etcc_bde=c&gad_source=1&gad_campaignid=9832816266&gbraid=0AAAAAD6rWrxc8S6R564TZI1ixI7XQeHLL&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qVVacNmoRpZG9lHVil0-EgZiw9iFIkqZa87jyegz-MIBHvc_lKyWcBoCBhYQAvD_BwE", "https://www.bet-at-home.com/de/promotions"],
                "Lottoland": ["https://www.lottoland.at/", ""],
            }

        }


    async def setup_browser(self, proxy: Optional[Dict] = None) -> None:
        logger.info("setup_browser skipped (Playwright runs in executor)")

        
    async def close_browser(self) -> None:
        """Close browser and context"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
            
    # async def find_competitor_urls(self, competitor: Dict) -> List[str]:
    # async def find_competitor_urls(self, competitor: CompetitorInfo) -> List[str]:

    #     """Find actual URLs for competitor using AI"""
    #     try:
    #         # Use AI to find URLs
    #         url_result = await self.url_finder.find_competitor_urls(
    #             competitor.name, 
    #             self.current_country
    #         )
            
    #         # Combine main and promotion URLs
    #         all_urls = url_result['main_urls'] + url_result['promotion_urls']
            
    #         if all_urls:
    #             logger.info(f"Found {len(all_urls)} URLs for {competitor.name}")
    #             for url in all_urls:
    #                 print(url)                    
    #             return all_urls
    #         else:
    #             logger.warning(f"No URLs found for {competitor.name}")
    #             return []
                
    #     except Exception as e:
    #         logger.error(f"Error finding URLs for {competitor.name}: {e}")
    #         return []

    async def find_competitor_urls(self, competitor: CompetitorInfo) -> List[str]:
        """Find actual URLs for competitor using AI and manual additions"""
        try:
            # Buscar automáticamente con el URLFinder
            url_result = await self.url_finder.find_competitor_urls(
                competitor.name,
                self.current_country
            )

            all_urls = url_result['main_urls'] + url_result['promotion_urls']

            # Si hay URLs manuales configuradas, añádelas
            manual_for_country = self.manual_urls.get(self.current_country, {})
            manual_for_brand = manual_for_country.get(competitor.name, [])
            if manual_for_brand:
                logger.info(f"✅ Adding manual URLs for {competitor.name}: {manual_for_brand}")
                all_urls.extend(manual_for_brand)

            # Elimina duplicados y devuelve
            all_urls = list(dict.fromkeys(all_urls))
            if all_urls:
                logger.info(f"Found {len(all_urls)} total URLs for {competitor.name}")
                for url in all_urls:
                    print(url)
                return all_urls
            else:
                logger.warning(f"No URLs found for {competitor.name}")
                return []

        except Exception as e:
            logger.error(f"Error finding URLs for {competitor.name}: {e}")
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

            # Extract wagering requirement (if present)
            wagering = self.extract_wagering(text)
            
            # Extract validity
            valid_until = self.extract_validity(text)
            
            # Create hash for deduplication
            hash_content = f"{competitor.name}_{title}_{bonus_amount}_{bonus_type}"
            hash_id = str(hash(hash_content))
            
            return PromotionData(
                competitor=competitor.name,
                country=competitor.country,
                title=title,
                description=text[:500],  # Limit description length
                bonus_amount=bonus_amount,
                bonus_type=bonus_type,
                conditions=conditions,
                wagering=wagering,
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
    
    # def extract_wagering(self, text: str) -> str:
    #     """Extract wagering requirements (e.g., 35x bonus, 50x, 20x spins)"""
    #     patterns = [
    #         r'(\d+\s*[xX]\s*(?:bonus|deposit|wager)?)',
    #         r'wagering\s*requirement\s*[:\-]?\s*(\d+[xX])',
    #         r'playthrough\s*[:\-]?\s*(\d+[xX])',
    #         r'rollover\s*[:\-]?\s*(\d+[xX])'
    #     ]
    #     for pattern in patterns:
    #         match = re.search(pattern, text, re.IGNORECASE)
    #         if match:
    #             return match.group(1).strip()
    #     return ""

    def extract_wagering(self, text: str) -> str:
        """
        Nuevo: usa reglas multi-idioma y normaliza resultado a '35x (bonus)' / '35x (deposit)' / '50% (bonus)'.
        Mantiene compatibilidad de tipo (devuelve str).
        """
        res = extract_wagering_from_text(text or "")
        return to_display_string(res)

        
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
                    
                    hash_content = f"{competitor.name}_{title}_{bonus_amount}"
                    hash_id = str(hash(hash_content))
                    
                    promotion = PromotionData(
                        competitor=competitor.name,
                        country=competitor.country,
                        title=title,
                        description=paragraph[:500],
                        bonus_amount=bonus_amount,
                        bonus_type=self.extract_bonus_type(paragraph),
                        conditions=self.extract_conditions(paragraph),
                        wagering=self.extract_wagering(paragraph),
                        valid_until=self.extract_validity(paragraph),
                        url=url,
                        scraped_at=current_time,
                        hash_id=hash_id
                    )
                    
                    promotions.append(promotion)
                    
        return promotions[:10]  # Limit to 10 promotions per page
    

    async def scrape_competitor_promotions(self, competitor_name: str, url: str, country: str) -> List[PromotionData]:
        try:
            # worker_path = Path(__file__).parent / "playwright_worker.py"
            worker_module = "scraper.playwright_worker"


            # 🔹 En Windows usamos subprocess.run en lugar de asyncio
            if sys.platform.startswith("win"):
                proc = subprocess.run(
                    [sys.executable, "-m", worker_module, competitor_name, url, country,
                    ",".join(["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"])],
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
                ",".join(["bonus", "promotion", "welcome", "jackpot", "free spins", "deposit", "tournament", "vip levels", "vip", "cashback", "vip levels", "loyalty", "points", "exclusive benefits"]),
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
            logger.info(f"🔄 Connecting to VPN for {country}...")

            vpn_ok = connect_cyberghost(country)  # True/False
            proxy = None  # No asumas estructura de dict aquí
            if isinstance(vpn_ok, dict) and vpn_ok.get("proxies"):
                proxy = vpn_ok["proxies"][0]
                logger.info(f"Using proxy for {country}: {proxy}")
            else:
                logger.info(f"No proxy configured (or simple VPN boolean), running without proxy")



            # vpn_config = get_vpn_config(country)
            # proxy = None
            # if vpn_config and vpn_config.get("proxies"):
            #     proxy = vpn_config["proxies"][0]  # Usamos el primer proxy disponible
            #     logger.info(f"Using proxy for {country}: {proxy}")
            # else:
            #     logger.info(f"No proxy configured for {country}, running without proxy")

            await self.setup_browser(proxy)

            
            # for competitor in competitors:
            #     try:
            #         print("entra en el bucle de competitors")
            #         print(competitor)
            #         logger.info(f"Scraping {competitor.name}...")
                    
            #         # Find URLs for this competitor
            #         urls = await self.find_competitor_urls(competitor)
            for competitor_dict in competitors:
                try:
                    competitor = CompetitorInfo(
                        name=competitor_dict["name"],
                        country=country,
                        url="",  # se llenará luego
                        search_terms=competitor_dict["search_terms"]
                    )

                    print("entra en el bucle de competitors")
                    print(competitor)
                    logger.info(f"Scraping {competitor.name}...")

                    # Find URLs for this competitor
                    urls = await self.find_competitor_urls(competitor)
                    
                    if not urls:
                        logger.warning(f"No URLs found for {competitor.name}, skipping...")
                        continue
                        
                    # Scrape each URL
                    for url in urls:
                        try:
                            logger.info(f"Scraping URL: {url}")
                            promotions = await self.scrape_competitor_promotions(competitor.name, url, country)
                            all_promotions.extend(promotions)
                            
                            await asyncio.sleep(random.uniform(2, 5))
                            
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error scraping competitor {competitor.name}: {e}")
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
            # for competitor in competitors:
            for competitor_dict in competitors:
                competitor = CompetitorInfo(
                    name=competitor_dict["name"],
                    country=country,
                    url="",
                    search_terms=competitor_dict["search_terms"]
                )
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
                                        if any(term in sentence.lower() for term in competitor.search_terms) and len(sentence) > 30:
                                            promotion = PromotionData(
                                                competitor=competitor.name,
                                                country=country,
                                                title=sentence[:100],
                                                description=sentence[:500],
                                                bonus_amount=self.extract_bonus_amount(sentence),
                                                bonus_type=self.extract_bonus_type(sentence),
                                                conditions='',
                                                wagering=self.extract_wagering(sentence),
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
                    logger.error(f"Fallback failed for {competitor.name}: {e}")
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
    
    # === NUEVO: intento profundo en T&C si falta wagering ===
    try:
        # (a) detecta posibles enlaces de T&C en la página
        tc_links = find_candidate_tc_links(html, url)[:3]  # limita a 3 por rendimiento

        if tc_links:
            for i, promo in enumerate(promotions):
                # promo puede ser dataclass PromotionData o dict, soportamos ambos
                current_wagering = getattr(promo, "wagering", None) if hasattr(promo, "wagering") else promo.get("wagering", "")
                if current_wagering:
                    continue  # ya tenemos wagering

                best_res = None
                # (b) recorre T&C links hasta extraer algo con confianza suficiente
                for tc in tc_links:
                    try:
                        page.goto(tc, timeout=25000)
                        page.wait_for_load_state("domcontentloaded", timeout=5000)
                        tc_text = page.inner_text("body", timeout=5000)
                        res = extract_wagering_from_text(tc_text)
                        if res and res.get("confidence", 0) >= 0.8:
                            best_res = res
                            break
                        # si no llega a 0.8 pero hay algo, guárdalo como plan B
                        if res and res.get("confidence", 0) >= 0.6 and not best_res:
                            best_res = res
                    except Exception:
                        continue

                # (c) si encontramos algo, volcamos al campo `wagering`
                if best_res:
                    wag_str = to_display_string(best_res)
                    if hasattr(promo, "wagering"):
                        setattr(promo, "wagering", wag_str)
                    else:
                        promo["wagering"] = wag_str
    except Exception as _:
        # No queremos romper el scraping por un fallo en esta fase
        pass
    # === FIN NUEVO ===

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
