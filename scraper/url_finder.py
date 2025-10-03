#!/usr/bin/env python3
"""
URL Finder Module - Uses AI to find competitor URLs automatically
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import os

from dotenv import load_dotenv  # Optional dependency
load_dotenv()  # Optional

logging.basicConfig(level=logging.INFO )
logger = logging.getLogger(__name__)

class URLFinder:
    def __init__(self, deepseek_api_key: Optional[str] = None):
        self.deepseek_api_key = deepseek_api_key or os.getenv('DEEPSEEK_API_KEY')
        
    async def find_competitor_urls(self, competitor_name: str, country: str) -> Dict[str, List[str]]:
        """Find URLs for a competitor using AI and patterns"""
        logger.info(f"Finding URLs for {competitor_name} in {country}")
        
        # Try AI first
        ai_urls = await self._find_urls_with_ai(competitor_name, country)
        
        # Pattern-based backup
        pattern_urls = self._generate_pattern_urls(competitor_name)
        
        # Validate URLs
        all_urls = list(set(ai_urls + pattern_urls))
        validated_urls = await self._validate_urls(all_urls)
        
        # Categorize
        main_urls = []
        promotion_urls = []
        
        for url in validated_urls:
            if self._is_promotion_url(url):
                promotion_urls.append(url)
            else:
                main_urls.append(url)
                
        if not promotion_urls and main_urls:
            promotion_urls = self._generate_promotion_urls(main_urls[0])
            
        return {
            'main_urls': main_urls[:3],
            'promotion_urls': promotion_urls[:5]
        }
        
    async def _find_urls_with_ai(self, competitor_name: str, country: str) -> List[str]:
        """Use DeepSeek AI to find URLs"""
        if not self.deepseek_api_key:
            logger.warning("DeepSeek API key not provided")
            return []
            
        try:
            prompt = f"""List only the official and currently accessible URLs of "{competitor_name}" casino in {country}. Output only valid URLs, one per line. No additional text, comments, or explanations."""
            
            headers = {
                'Authorization': f'Bearer {self.deepseek_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 500,
                'temperature': 0.1
            }
            
            async with aiohttp.ClientSession( ) as session:
                async with session.post(
                    'https://api.deepseek.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=30
                 ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        return self._extract_urls_from_text(content)
                    else:
                        logger.error(f"DeepSeek API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"AI URL search error: {e}")
            return []
            
    def _generate_pattern_urls(self, competitor_name: str) -> List[str]:
        """Generate URLs using common patterns"""
        urls = []
        base_names = [
            competitor_name.lower().replace(" ", ""),
            competitor_name.lower().replace(" ", "-"),
            competitor_name.lower().replace("casino", "").replace("bet", "").strip()
        ]
        
        tlds = ['.com', '.net', '.org', '.casino', '.bet']
        
        for base_name in base_names:
            if len(base_name) > 2:
                for tld in tlds:
                    urls.extend([
                        f"https://{base_name}{tld}",
                        f"https://www.{base_name}{tld}"
                    ] )
        return urls[:15]
        
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text )
        return [re.sub(r'[.,;!?]+$', '', url) for url in urls if self._is_valid_url(url)]
        
    def _is_valid_url(self, url: str) -> bool:
        """Check URL validity"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except:
            return False
            
    async def _validate_urls(self, urls: List[str]) -> List[str]:
        """Validate URLs by checking accessibility"""
        valid_urls = []
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10 )) as session:
            tasks = [self._check_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, is_valid in zip(urls, results):
                if is_valid is True:
                    valid_urls.append(url)
        return valid_urls
        
    async def _check_url(self, session: aiohttp.ClientSession, url: str ) -> bool:
        """Check single URL"""
        try:
            async with session.head(url, allow_redirects=True) as response:
                return response.status < 400
        except:
            return False
            
    def _is_promotion_url(self, url: str) -> bool:
        """Check if URL is promotion-related"""
        keywords = ['promotion', 'bonus', 'offer', 'deal', 'welcome', 'free', 'tournament']
        return any(keyword in url.lower() for keyword in keywords)
        
    def _generate_promotion_urls(self, base_url: str) -> List[str]:
        """Generate promotion URLs from base URL"""
        paths = ['/promotions', '/bonuses', '/offers', '/welcome-bonus', '/tournaments']
        return [urljoin(base_url, path) for path in paths]

# Ejemplo de configuración con servicios gratuitos
VPN_CONFIGS = {
    'AE': {
        'country_code': 'AE',
        'proxies': [
            # ProtonVPN Free (necesitas crear cuenta)
            {'server': 'http://free.protonvpn.com:8080', 'username': '3KVsdJTDZmZMltlf', 'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'}
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Dubai, UAE'
    },
    'SA': {
        'country_code': 'SA', 
        'proxies': [
            {'server': 'http://free.protonvpn.com:8080', 'username': '3KVsdJTDZmZMltlf', 'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'}
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Riyadh, Saudi Arabia'
    },
    'KW': {
        'country_code': 'KW', 
        'proxies': [
            {'server': 'http://free.protonvpn.com:8080', 'username': '3KVsdJTDZmZMltlf', 'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'}
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Kuwait City, Kuwait'
    },
    'QA': {
        'country_code': 'QA',
        'proxies': [
            # ProtonVPN Free (necesitas crear cuenta)
            {
                'server': 'http://free.protonvpn.com:8080',
                'username': '3KVsdJTDZmZMltlf',
                'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'
            }
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Doha, Qatar'
    },
    'OM': {
        'country_code': 'OM',
        'proxies': [
            {
                'server': 'http://free.protonvpn.com:8080',
                'username': '3KVsdJTDZmZMltlf',
                'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'
            }
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Muscat, Oman'
    },
    'BH': {
        'country_code': 'BH',
        'proxies': [
            {
                'server': 'http://free.protonvpn.com:8080',
                'username': '3KVsdJTDZmZMltlf',
                'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'
            }
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Manama, Bahrain'
    },
    'JO': {
        'country_code': 'JO',
        'proxies': [
            {
                'server': 'http://free.protonvpn.com:8080',
                'username': '3KVsdJTDZmZMltlf',
                'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'
            }
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Amman, Jordan'
    },
    'NZ': {
        'country_code': 'NZ',
        'proxies': [
            {
                'server': 'http://free.protonvpn.com:8080',
                'username': '3KVsdJTDZmZMltlf',
                'password': 'BpB9r8UNKMTcaOCU0LC19VHE8KXI3WZI'
            }
        ],
        'vpn_service': 'ProtonVPN',
        'location': 'Auckland, New Zealand'
    }
    
}

def get_vpn_config(country: str ) -> Dict:
    return VPN_CONFIGS.get(country, {})
