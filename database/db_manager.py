#!/usr/bin/env python3
"""
Database Manager for Competitor Analysis
Handles SQLite database operations for storing and comparing promotion data
"""

import sqlite3
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib
import os
from pathlib import Path
from collections import defaultdict
import re
import unicodedata



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    wagering: str
    valid_until: str
    url: str
    scraped_at: str
    hash_id: str

class DatabaseManager:
    """Manages SQLite database operations for competitor analysis"""
    
    def __init__(self, db_path: str = "database/competitors.db"):
        self.db_path = db_path
        self.ensure_database_exists()
        
    def ensure_database_exists(self) -> None:
        """Create database and tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create promotions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor TEXT NOT NULL,
                    country TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    bonus_amount TEXT,
                    bonus_type TEXT,
                    conditions TEXT,
                    wagering TEXT,
                    valid_until TEXT,
                    url TEXT,
                    scraped_at TEXT NOT NULL,
                    hash_id TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create comparison results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparison_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comparison_date TEXT NOT NULL,
                    country TEXT NOT NULL,
                    total_new_promotions INTEGER DEFAULT 0,
                    total_updated_promotions INTEGER DEFAULT 0,
                    total_removed_promotions INTEGER DEFAULT 0,
                    competitors_analyzed TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_competitor_country ON promotions(competitor, country)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash_id ON promotions(hash_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraped_at ON promotions(scraped_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_active ON promotions(is_active)")
            
            conn.commit()
            logger.info("Database and tables created/verified successfully")
            
    def insert_promotions(self, promotions: List[PromotionData]) -> Tuple[int, int, int]:
        """
        Insert promotions into database
        Returns: (new_count, updated_count, duplicate_count)
        """
        new_count = 0
        updated_count = 0
        duplicate_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for promotion in promotions:
                try:
                    # Check if promotion already exists
                    cursor.execute(
                        "SELECT id, scraped_at FROM promotions WHERE hash_id = ?",
                        (promotion.hash_id,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing promotion
                        cursor.execute("""
                            UPDATE promotions SET
                                title = ?, description = ?, bonus_amount = ?,
                                bonus_type = ?, conditions = ?, wagering = ?, valid_until = ?,
                                url = ?, scraped_at = ?, is_active = 1
                            WHERE hash_id = ?
                        """, (
                            promotion.title, promotion.description, promotion.bonus_amount,
                            promotion.bonus_type, promotion.conditions, promotion.wagering, promotion.valid_until,
                            promotion.url, promotion.scraped_at, promotion.hash_id
                        ))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                        else:
                            duplicate_count += 1
                    else:
                        # Insert new promotion
                        cursor.execute("""
                            INSERT INTO promotions (
                                competitor, country, title, description, bonus_amount,
                                bonus_type, conditions, wagering, valid_until, url, scraped_at, hash_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            promotion.competitor, promotion.country, promotion.title,
                            promotion.description, promotion.bonus_amount, promotion.bonus_type,
                            promotion.conditions, promotion.wagering, promotion.valid_until, promotion.url,
                            promotion.scraped_at, promotion.hash_id
                        ))
                        new_count += 1
                        
                except sqlite3.IntegrityError as e:
                    logger.warning(f"Integrity error inserting promotion: {e}")
                    duplicate_count += 1
                except Exception as e:
                    logger.error(f"Error inserting promotion: {e}")
                    
            conn.commit()
            
        logger.info(f"Database insert results: {new_count} new, {updated_count} updated, {duplicate_count} duplicates")
        return new_count, updated_count, duplicate_count
        
    def get_promotions_by_country(self, country: str, active_only: bool = True) -> List[Dict]:
        """Get all promotions for a specific country"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM promotions WHERE country = ?"
            params = [country]
            
            if active_only:
                query += " AND is_active = 1"
                
            query += " ORDER BY scraped_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
    def get_promotions_by_competitor(self, competitor: str, country: str = None) -> List[Dict]:
        """Get all promotions for a specific competitor"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM promotions WHERE competitor = ? AND is_active = 1"
            params = [competitor]
            
            if country:
                query += " AND country = ?"
                params.append(country)
                
            query += " ORDER BY scraped_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
    def get_clean_promotions_by_country(self, country: str, active_only: bool = True) -> List[Dict]:
        """Get promotions from clean_promotions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM clean_promotions WHERE country = ?"
            params = [country]
            
            if active_only:
                query += " AND 1=1"  # (puedes añadir flag is_active si lo añades)
                
            query += " ORDER BY scraped_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def compare_with_previous_clean(self, country: str, current_date: str) -> Dict[str, Any]:
        """Compare clean_promotions instead of raw promotions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM clean_promotions 
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            current_promotions = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT * FROM clean_promotions 
                WHERE country = ? AND date(scraped_at) < date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            previous_promotions = [dict(row) for row in cursor.fetchall()]
            
            current_hashes = {p['hash_id'] for p in current_promotions}
            previous_hashes = {p['hash_id'] for p in previous_promotions}
            
            new_hashes = current_hashes - previous_hashes
            removed_hashes = previous_hashes - current_hashes
            
            new_promotions = [p for p in current_promotions if p['hash_id'] in new_hashes]
            removed_promotions = [p for p in previous_promotions if p['hash_id'] in removed_hashes]
            
            comparison_result = {
                'comparison_date': current_date,
                'country': country,
                'new_promotions': new_promotions,
                'removed_promotions': removed_promotions,
                'total_current': len(current_promotions),
                'total_previous': len(previous_promotions),
                'new_count': len(new_promotions),
                'removed_count': len(removed_promotions),
                'competitors_analyzed': list(set(p['competitor'] for p in current_promotions))
            }
            
            return comparison_result

    
    def compare_with_previous(self, country: str, current_date: str) -> Dict[str, Any]:
        """Compare current promotions with previous scraping session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get current promotions (from today)
            cursor.execute("""
                SELECT * FROM promotions 
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            current_promotions = [dict(row) for row in cursor.fetchall()]
            
            # Get previous promotions (before today)
            cursor.execute("""
                SELECT * FROM promotions 
                WHERE country = ? AND date(scraped_at) < date(?)
                AND is_active = 1
                ORDER BY competitor, title
            """, (country, current_date))
            previous_promotions = [dict(row) for row in cursor.fetchall()]
            
            # Create hash sets for comparison
            current_hashes = {p['hash_id'] for p in current_promotions}
            previous_hashes = {p['hash_id'] for p in previous_promotions}
            
            # Find new, updated, and removed promotions
            new_hashes = current_hashes - previous_hashes
            removed_hashes = previous_hashes - current_hashes
            common_hashes = current_hashes & previous_hashes
            
            new_promotions = [p for p in current_promotions if p['hash_id'] in new_hashes]
            removed_promotions = [p for p in previous_promotions if p['hash_id'] in removed_hashes]
            
            # Mark removed promotions as inactive
            if removed_hashes:
                cursor.execute(f"""
                    UPDATE promotions SET is_active = 0 
                    WHERE hash_id IN ({','.join(['?' for _ in removed_hashes])})
                """, list(removed_hashes))
                conn.commit()
                
            comparison_result = {
                'comparison_date': current_date,
                'country': country,
                'new_promotions': new_promotions,
                'removed_promotions': removed_promotions,
                'total_current': len(current_promotions),
                'total_previous': len(previous_promotions),
                'new_count': len(new_promotions),
                'removed_count': len(removed_promotions),
                'competitors_analyzed': list(set(p['competitor'] for p in current_promotions))
            }
            
            # Save comparison results
            self.save_comparison_result(comparison_result)
            
            return comparison_result
            
    def save_comparison_result(self, result: Dict[str, Any]) -> None:
        """Save comparison result to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO comparison_results (
                    comparison_date, country, total_new_promotions,
                    total_updated_promotions, total_removed_promotions,
                    competitors_analyzed
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result['comparison_date'],
                result['country'],
                result['new_count'],
                0,  # updated count (not implemented yet)
                result['removed_count'],
                json.dumps(result['competitors_analyzed'])
            ))
            
            conn.commit()
            
    def export_to_csv(self, country: str, output_path: str) -> str:
        """Export promotions to CSV file"""
        promotions = self.get_promotions_by_country(country)
        
        if not promotions:
            logger.warning(f"No promotions found for country: {country}")
            return ""
            
        csv_file = f"{output_path}/promotions_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if promotions:
                writer = csv.DictWriter(f, fieldnames=promotions[0].keys())
                writer.writeheader()
                writer.writerows(promotions)
                
        logger.info(f"Exported {len(promotions)} promotions to {csv_file}")
        return csv_file
        
    def export_to_json(self, country: str, output_path: str) -> str:
        """Export promotions to JSON file"""
        promotions = self.get_promotions_by_country(country)
        
        json_file = f"{output_path}/promotions_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(promotions, f, indent=2, ensure_ascii=False, default=str)
            
        logger.info(f"Exported {len(promotions)} promotions to {json_file}")
        return json_file
        
    def export_comparison_results(self, country: str, output_path: str) -> Tuple[str, str]:
        """Export comparison results to CSV and JSON"""
        comparison = self.get_latest_comparison(country)
        
        if not comparison:
            logger.warning(f"No comparison results found for country: {country}")
            return "", ""
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export new promotions to CSV
        csv_file = f"{output_path}/new_promotions_{country}_{timestamp}.csv"
        if comparison['new_promotions']:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=comparison['new_promotions'][0].keys())
                writer.writeheader()
                writer.writerows(comparison['new_promotions'])
        else:
            # Create empty CSV with headers
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['competitor', 'country', 'title', 'description', 'bonus_amount', 
                               'bonus_type', 'conditions', 'valid_until', 'url', 'scraped_at'])
                
        # Export comparison summary to JSON
        json_file = f"{output_path}/comparison_summary_{country}_{timestamp}.json"
        summary = {
            'comparison_date': comparison['comparison_date'],
            'country': comparison['country'],
            'total_current_promotions': comparison['total_current'],
            'total_previous_promotions': comparison['total_previous'],
            'new_promotions_count': comparison['new_count'],
            'removed_promotions_count': comparison['removed_count'],
            'competitors_analyzed': comparison['competitors_analyzed'],
            'new_promotions': comparison['new_promotions']
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
        logger.info(f"Exported comparison results to {csv_file} and {json_file}")
        return csv_file, json_file
        
    def get_latest_comparison(self, country: str) -> Optional[Dict]:
        """Get the latest comparison result for a country"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM comparison_results 
                WHERE country = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (country,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            # Get the actual promotion data
            comparison_date = result['comparison_date']
            
            # Get new promotions from that date
            cursor.execute("""
                SELECT * FROM promotions 
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, comparison_date))
            
            new_promotions = [dict(row) for row in cursor.fetchall()]
            
            return {
                'comparison_date': comparison_date,
                'country': country,
                'new_promotions': new_promotions,
                'removed_promotions': [],  # Would need additional logic to track
                'total_current': len(new_promotions),
                'total_previous': 0,  # Would need additional logic
                'new_count': result['total_new_promotions'],
                'removed_count': result['total_removed_promotions'],
                'competitors_analyzed': json.loads(result['competitors_analyzed']) if result['competitors_analyzed'] else []
            }
            
    def get_statistics(self, country: str = None) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total promotions
            if country:
                cursor.execute("SELECT COUNT(*) FROM promotions WHERE country = ?", (country,))
            else:
                cursor.execute("SELECT COUNT(*) FROM promotions")
            stats['total_promotions'] = cursor.fetchone()[0]
            
            # Active promotions
            if country:
                cursor.execute("SELECT COUNT(*) FROM promotions WHERE country = ? AND is_active = 1", (country,))
            else:
                cursor.execute("SELECT COUNT(*) FROM promotions WHERE is_active = 1")
            stats['active_promotions'] = cursor.fetchone()[0]
            
            # Promotions by competitor
            if country:
                cursor.execute("""
                    SELECT competitor, COUNT(*) as count 
                    FROM promotions 
                    WHERE country = ? AND is_active = 1
                    GROUP BY competitor
                """, (country,))
            else:
                cursor.execute("""
                    SELECT competitor, COUNT(*) as count 
                    FROM promotions 
                    WHERE is_active = 1
                    GROUP BY competitor
                """)
            stats['by_competitor'] = dict(cursor.fetchall())
            
            # Promotions by type
            if country:
                cursor.execute("""
                    SELECT bonus_type, COUNT(*) as count 
                    FROM promotions 
                    WHERE country = ? AND is_active = 1
                    GROUP BY bonus_type
                """, (country,))
            else:
                cursor.execute("""
                    SELECT bonus_type, COUNT(*) as count 
                    FROM promotions 
                    WHERE is_active = 1
                    GROUP BY bonus_type
                """)
            stats['by_type'] = dict(cursor.fetchall())
            
            # Latest scraping date
            if country:
                cursor.execute("""
                    SELECT MAX(scraped_at) 
                    FROM promotions 
                    WHERE country = ?
                """, (country,))
            else:
                cursor.execute("SELECT MAX(scraped_at) FROM promotions")
            stats['latest_scraping'] = cursor.fetchone()[0]
            
            return stats

    # --- MÉTODOS CLEAN NUEVOS (añádelos en DatabaseManager) ---

    def _get_today_str(self) -> str:
        return datetime.now().date().isoformat()

    def compare_with_previous_clean(self, country: str, current_date: str) -> Dict[str, Any]:
        """Compare usando SOLO clean_promotions y guarda el resultado en comparison_results."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # actuales = solo los de hoy (lo nuevo)
            cursor.execute("""
                SELECT * FROM clean_promotions 
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            current_promotions = [dict(row) for row in cursor.fetchall()]

            # anteriores = todo lo de días anteriores
            cursor.execute("""
                SELECT * FROM clean_promotions 
                WHERE country = ? AND date(scraped_at) < date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            previous_promotions = [dict(row) for row in cursor.fetchall()]

            current_hashes = {p['hash_id'] for p in current_promotions}
            previous_hashes = {p['hash_id'] for p in previous_promotions}

            new_hashes = current_hashes - previous_hashes
            removed_hashes = previous_hashes - current_hashes

            new_promotions = [p for p in current_promotions if p['hash_id'] in new_hashes]
            removed_promotions = [p for p in previous_promotions if p['hash_id'] in removed_hashes]

            result = {
                'comparison_date': current_date,
                'country': country,
                'new_promotions': new_promotions,          # SOLO lo de hoy que no existía
                'removed_promotions': removed_promotions,  # lo que existía y hoy no está
                'total_current': len(current_promotions),
                'total_previous': len(previous_promotions),
                'new_count': len(new_promotions),
                'removed_count': len(removed_promotions),
                'competitors_analyzed': list(set(p['competitor'] for p in current_promotions))
            }

            # Guardamos en comparison_results (reaprovechando la tabla)
            self.save_comparison_result(result)
            return result

    def get_latest_clean_comparison(self, country: str) -> Optional[Dict]:
        """Devuelve la última comparación (clean) y los NEW de ese día desde clean_promotions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM comparison_results 
                WHERE country = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (country,))
            row = cursor.fetchone()
            if not row:
                return None

            comparison_date = row['comparison_date']

            # NEW del día (desde clean_promotions)
            cursor.execute("""
                SELECT * FROM clean_promotions
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, comparison_date))
            todays_clean = [dict(r) for r in cursor.fetchall()]

            return {
                'comparison_date': comparison_date,
                'country': country,
                'new_promotions': todays_clean,  # lo nuevo del día en clean
                'removed_promotions': [],
                'total_current': len(todays_clean),
                'total_previous': 0,
                'new_count': row['total_new_promotions'],
                'removed_count': row['total_removed_promotions'],
                'competitors_analyzed': json.loads(row['competitors_analyzed']) if row['competitors_analyzed'] else []
            }

    def export_clean_to_csv(self, country: str, output_path: str) -> str:
        """Exporta SOLO lo nuevo de HOY desde clean_promotions."""
        today = self._get_today_str()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM clean_promotions
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, today))
            rows = [dict(r) for r in cursor.fetchall()]

        if not rows:
            logging.warning(f"No new clean promotions for {country} on {today}")
            return ""

        csv_file = f"{output_path}/clean_promotions_new_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        logging.info(f"Exported {len(rows)} NEW clean promotions to {csv_file}")
        return csv_file

    def export_clean_to_json(self, country: str, output_path: str) -> str:
        """Exporta SOLO lo nuevo de HOY desde clean_promotions a JSON."""
        today = self._get_today_str()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM clean_promotions
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, today))
            rows = [dict(r) for r in cursor.fetchall()]

        json_file = f"{output_path}/clean_promotions_new_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=2, ensure_ascii=False, default=str)
        logging.info(f"Exported {len(rows)} NEW clean promotions to {json_file}")
        return json_file

    def export_clean_comparison_results(self, country: str, output_path: str) -> Tuple[str, str]:
        """Genera CSV/JSON para el dashboard usando SOLO lo NUEVO de la última comparación CLEAN."""
        comparison = self.get_latest_clean_comparison(country)
        if not comparison:
            logging.warning(f"No clean comparison results for country: {country}")
            return "", ""

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # CSV con SOLO los new_promotions (clean)
        csv_file = f"{output_path}/clean_new_promotions_{country}_{timestamp}.csv"
        if comparison['new_promotions']:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=comparison['new_promotions'][0].keys())
                writer.writeheader()
                writer.writerows(comparison['new_promotions'])
        else:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['competitor', 'country', 'title', 'description', 'bonus_amount',
                                'bonus_type', 'conditions', 'valid_until', 'url', 'scraped_at', 'hash_id'])

        # JSON resumen SOLO con lo nuevo
        json_file = f"{output_path}/clean_comparison_summary_{country}_{timestamp}.json"
        summary = {
            'comparison_date': comparison['comparison_date'],
            'country': comparison['country'],
            'new_promotions_count': comparison['new_count'],
            'removed_promotions_count': comparison['removed_count'],
            'competitors_analyzed': comparison['competitors_analyzed'],
            'new_promotions': comparison['new_promotions'],  # para el dashboard
        }
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

        logging.info(f"Exported CLEAN comparison results to {csv_file} and {json_file}")
        return csv_file, json_file

    def get_statistics_clean(self, country: str = None) -> Dict[str, Any]:
        """Stats desde clean_promotions (puedes usarlo en el summary)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            stats = {}

            if country:
                cursor.execute("SELECT COUNT(*) FROM clean_promotions WHERE country = ?", (country,))
            else:
                cursor.execute("SELECT COUNT(*) FROM clean_promotions")
            stats['total_promotions'] = cursor.fetchone()[0]

            # por competidor
            if country:
                cursor.execute("""
                    SELECT competitor, COUNT(*) as count
                    FROM clean_promotions
                    WHERE country = ?
                    GROUP BY competitor
                """, (country,))
            else:
                cursor.execute("""
                    SELECT competitor, COUNT(*) as count
                    FROM clean_promotions
                    GROUP BY competitor
                """)
            stats['by_competitor'] = dict(cursor.fetchall())

            # por tipo
            if country:
                cursor.execute("""
                    SELECT bonus_type, COUNT(*) as count
                    FROM clean_promotions
                    WHERE country = ?
                    GROUP BY bonus_type
                """, (country,))
            else:
                cursor.execute("""
                    SELECT bonus_type, COUNT(*) as count
                    FROM clean_promotions
                    GROUP BY bonus_type
                """)
            stats['by_type'] = dict(cursor.fetchall())

            # última fecha
            if country:
                cursor.execute("""
                    SELECT MAX(scraped_at)
                    FROM clean_promotions
                    WHERE country = ?
                """, (country,))
            else:
                cursor.execute("SELECT MAX(scraped_at) FROM clean_promotions")
            stats['latest_scraping'] = cursor.fetchone()[0]

            return stats
    
    # --- Helpers de normalización/dedupe (añadir dentro de DatabaseManager) ---

    import re, unicodedata
    from collections import defaultdict

    def _normalize_text(self, s: str) -> str:
        if not s:
            return ""
        s = s.lower().strip()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        # sinónimos frecuentes multi-idioma
        s = s.replace("first time deposit", "first deposit")
        s = s.replace("primer deposito", "first deposit")
        s = s.replace("primer depósito", "first deposit")
        s = s.replace("bono de bienvenida", "welcome bonus")
        s = s.replace("crypto para deportes", "crypto sports")
        s = s.replace("deportes", "sports")
        s = re.sub(r"[^a-z0-9%$€\s\.,\-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _parse_amount_key(self, amount: str, description: str) -> str:
        UNIT_LIST = ['€', '$', '£', 'usdt', 'usd', 'eur', 'aed', 'zar', 'gbp', 'brl']  # orden: tokens largos primero
        UNIT_RE = r'(?:' + '|'.join(UNIT_LIST) + r')'
        CURRENCY_MAP = {'€':'eur', '$':'usd', '£':'gbp', 'usdt':'usdt','usd':'usd','eur':'eur','aed':'aed','zar':'zar','gbp':'gbp','brl':'brl'}

        text = f"{amount or ''} {description or ''}".lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))

        # Porcentajes
        pct = re.findall(r"(\d{1,3})\s*%", text)
        pct = [str(int(p)) for p in pct if p.isdigit()]

        # Cantidades con moneda (200 usdt, €20, $100, etc.)
        curr = []
        for m in re.finditer(rf"(\d[\d\.,]*)\s*{UNIT_RE}", text):
            num = m.group(1).replace(".", "").replace(",", "")
            try:
                numi = str(int(num))
            except:
                continue
            unit_raw = m.group(0)[len(m.group(1)):].strip().lower()
            unit = CURRENCY_MAP.get(unit_raw, unit_raw)
            curr.append(f"{numi}{unit}")
        # Formato unidad primero ($100)
        for m in re.finditer(rf"{UNIT_RE}\s*(\d[\d\.,]*)", text):
            unit_raw = m.group(0)[:len(m.group(0)) - len(m.group(1))].strip().lower()
            unit = CURRENCY_MAP.get(unit_raw, unit_raw)
            num = m.group(1).replace(".", "").replace(",", "")
            try:
                numi = str(int(num))
            except:
                continue
            curr.append(f"{numi}{unit}")

        # Free spins
        spins = re.findall(r"(\d+)\s*(?:free\s*spins|spins|giros|tiradas)", text)
        spins = [str(int(s)) for s in spins]

        parts = []
        if pct:
            parts.append("pct:" + "+".join(sorted(set(pct))))
        if curr:
            parts.append("amt:" + "+".join(sorted(set(curr))))
        if spins:
            parts.append("spins:" + "+".join(sorted(set(spins))))
        return "|".join(parts) if parts else ""

    def _semantic_signature(self, row: Dict[str, Any]) -> str:
        competitor = self._normalize_text(row.get("competitor"))
        country = (row.get("country") or "").upper()
        btype = self._normalize_text(row.get("bonus_type"))
        amount_key = self._parse_amount_key(row.get("bonus_amount") or "", row.get("description") or "")
        conditions = self._normalize_text(row.get("conditions") or "")
        # Pistas de condiciones
        cond_tokens = []
        for kw in ["first deposit", "wagering", "crypto", "sports", "registration", "welcome bonus"]:
            if kw in conditions:
                cond_tokens.append(kw)
        cond_key = "+".join(cond_tokens)
        key = f"{competitor}|{country}|{btype}|{amount_key}|{cond_key}"
        return key.strip("|")

    def _choose_best(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        # “Mejor” = más campos llenos, descripción más informativa, URL más limpia; desempate por id
        def score(r):
            filled = sum(1 for k in ["bonus_amount","conditions","valid_until"] if (r.get(k) or "").strip())
            desc_len = len((r.get("description") or "").strip())
            url = (r.get("url") or "")
            url_penalty = url.count("?") + url.count("&")
            return (filled, desc_len, -url_penalty, -len(url), -r["id"])
        return sorted(records, key=score, reverse=True)[0]

    def _dedupe_by_signature(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        groups = defaultdict(list)
        for r in rows:
            groups[self._semantic_signature(r)].append(r)
        return [self._choose_best(lst) for lst in groups.values()]

    # --- Nueva comparación semántica CLEAN (añadir dentro de DatabaseManager) ---

    def compare_with_previous_clean_semantic(self, country: str, current_date: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # HOY
            cursor.execute("""
                SELECT * FROM clean_promotions
                WHERE country = ? AND date(scraped_at) = date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            today_rows = [dict(r) for r in cursor.fetchall()]

            # ANTES DE HOY
            cursor.execute("""
                SELECT * FROM clean_promotions
                WHERE country = ? AND date(scraped_at) < date(?)
                ORDER BY competitor, title
            """, (country, current_date))
            prev_rows = [dict(r) for r in cursor.fetchall()]

        # Dedup dentro del día
        today_unique = self._dedupe_by_signature(today_rows)
        # Firmas previas
        prev_sigs = { self._semantic_signature(r) for r in prev_rows }
        # Novedades reales vs histórico
        new_promos = [r for r in today_unique if self._semantic_signature(r) not in prev_sigs]

        result = {
            "comparison_date": current_date,
            "country": country,
            "new_promotions": new_promos,           # SOLO novedades, ya deduplicadas
            "removed_promotions": [],               # (opcional: se puede calcular con firmas)
            "total_current": len(today_unique),     # únicos de hoy (internamente)
            "total_previous": len(prev_rows),
            "new_count": len(new_promos),
            "removed_count": 0,
            "competitors_analyzed": list({ r["competitor"] for r in today_unique })
        }

        # Guardar resumen en comparison_results (reutilizando tu método)
        self.save_comparison_result(result)
        return result

    # --- Exportaciones nuevas basadas en la comparación semántica ---

    def export_clean_new_semantic_to_json(self, country: str, output_path: str) -> str:
        today = datetime.now().date().isoformat()
        cmp = self.compare_with_previous_clean_semantic(country, today)
        rows = cmp["new_promotions"]

        json_file = f"{output_path}/clean_promotions_new_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Exported {len(rows)} NEW (semantic) clean promotions to {json_file}")
        return json_file

    def export_clean_new_semantic_to_csv(self, country: str, output_path: str) -> str:
        today = datetime.now().date().isoformat()
        cmp = self.compare_with_previous_clean_semantic(country, today)
        rows = cmp["new_promotions"]

        csv_file = f"{output_path}/clean_promotions_new_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            else:
                writer = csv.writer(f)
                writer.writerow(["competitor","country","title","description","bonus_amount",
                                "bonus_type","conditions","valid_until","url","scraped_at","hash_id"])
        logger.info(f"Exported {len(rows)} NEW (semantic) clean promotions to {csv_file}")
        return csv_file
    
    def export_clean_comparison_results_semantic(self, country: str, output_path: str) -> Tuple[str, str]:
        today = datetime.now().date().isoformat()
        cmp = self.compare_with_previous_clean_semantic(country, today)

        # export a JSON resumen
        json_file = f"{output_path}/comparison_results_semantic_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(cmp, f, indent=2, ensure_ascii=False, default=str)

        # export a CSV resumen (ej. con totales y lista de nuevas promos)
        csv_file = f"{output_path}/comparison_results_semantic_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "comparison_date", "country", "new_count",
                "removed_count", "total_current", "total_previous",
                "competitors_analyzed"
            ])
            writer.writerow([
                cmp["comparison_date"], cmp["country"], cmp["new_count"],
                cmp["removed_count"], cmp["total_current"], cmp["total_previous"],
                ";".join(cmp["competitors_analyzed"])
            ])
        logger.info(f"Exported semantic comparison results to {csv_file}, {json_file}")
        return csv_file, json_file




def main():
    """Test the database manager"""
    db = DatabaseManager()
    
    # Test with sample data
    sample_promotions = [
        PromotionData(
            competitor="Test Casino",
            country="UAE",
            title="Welcome Bonus",
            description="Get 100% bonus on first deposit",
            bonus_amount="$1000",
            bonus_type="Welcome Bonus",
            conditions="Wagering requirement: 35x",
            valid_until="2024-12-31",
            url="https://test.com",
            scraped_at=datetime.now().isoformat(),
            hash_id=str(hash("Test Casino_Welcome Bonus_$1000"))
        )
    ]
    
    # Insert test data
    new_count, updated_count, duplicate_count = db.insert_promotions(sample_promotions)
    print(f"Inserted: {new_count} new, {updated_count} updated, {duplicate_count} duplicates")
    
    # Get statistics
    stats = db.get_statistics("UAE")
    print(f"Statistics: {stats}")
    
    # Export data
    csv_file = db.export_to_csv("UAE", "output")
    json_file = db.export_to_json("UAE", "output")
    print(f"Exported to: {csv_file}, {json_file}")

if __name__ == "__main__":
    main()
