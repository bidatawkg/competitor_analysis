#!/usr/bin/env python3
"""
Main script for Competitor Analysis System
Integrates scraping, database operations, and report generation
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
from pathlib import Path

# Add project paths
base_dir = Path(__file__).resolve().parent
sys.path.append(str(base_dir))
sys.path.append(str(base_dir / "scraper"))
sys.path.append(str(base_dir / "database"))

from scraper.competitor_scraper import CompetitorScraper, PromotionData
from database.db_manager import DatabaseManager
from database.deepseek_cleaner import DeepSeekCleaner

from dotenv import load_dotenv  # Optional dependency
load_dotenv()  # Optional

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configure logging
log_file = Path(__file__).resolve().parent / "main.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompetitorAnalysisSystem:
    """Main system class that orchestrates the entire process"""        

    def __init__(self, use_proxy: bool = False, headless: bool = True, deepseek_api_key: Optional[str] = None):
        self.scraper = CompetitorScraper(use_proxy=use_proxy, headless=headless)
        self.db_manager = DatabaseManager()
        base_dir = Path(__file__).resolve().parent  # carpeta donde está main.py
        self.output_dir = base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)  # crea la carpeta si no existe
        self.deepseek_api_key = deepseek_api_key or os.getenv('DEEPSEEK_API_KEY')
        
    async def run_full_analysis(self, country: str = "UAE") -> Dict[str, Any]:
        """Run complete analysis: scrape, store, compare, and export"""
        logger.info(f"Starting full analysis for country: {country}")
        
        try:
            # Step 1: Scrape competitor data
            logger.info("Step 1: Scraping competitor data...")
            promotions = await self.scraper.scrape_all_competitors(country)
            
            if not promotions:
                logger.warning("No promotions scraped")
            
            logger.info(f"Scraped {len(promotions)} promotions")
            
            # Step 2: Store in database
            logger.info("Step 2: Storing data in database...")
            new_count, updated_count, duplicate_count = self.db_manager.insert_promotions(promotions)

            # Step 2.5: Clean promotions with DeepSeek
            logger.info("Step 2.5: Cleaning promotions with DeepSeek...")
            cleaner = DeepSeekCleaner(self.db_manager.db_path)
            await cleaner.clean_latest_promotions(limit=100)
            
            # # Step 3: Compare with previous data
            # logger.info("Step 3: Comparing with previous data...")
            # current_date = datetime.now().isoformat()[:10]  # YYYY-MM-DD format
            # comparison_result = self.db_manager.compare_with_previous_clean(country, current_date)

            # # Step 4: Export results (CLEAN & ONLY NEW)
            # logger.info("Step 4: Exporting CLEAN-only NEW results...")
            # csv_file = self.db_manager.export_clean_to_csv(country, self.output_dir)
            # json_file = self.db_manager.export_clean_to_json(country, self.output_dir)

            # # Export CLEAN comparison results (only NEW for dashboard)
            # comp_csv, comp_json = self.db_manager.export_clean_comparison_results(country, self.output_dir) 

            # Step 3: Compare with previous data (SEMANTIC & DEDUPED)
            logger.info("Step 3: Comparing with previous data (semantic & dedup)...")
            current_date = datetime.now().date().isoformat()
            comparison_result = self.db_manager.compare_with_previous_clean_semantic(country, current_date)

            # Step 4: Export results (CLEAN & ONLY NEW & DEDUPED)
            logger.info("Step 4: Exporting CLEAN-only NEW results (semantic & deduped)...")
            csv_file = self.db_manager.export_clean_new_semantic_to_csv(country, self.output_dir)
            json_file = self.db_manager.export_clean_new_semantic_to_json(country, self.output_dir)

            # Export CLEAN comparison results (only NEW for dashboard)
            comp_csv, comp_json = self.db_manager.export_clean_comparison_results_semantic(country, self.output_dir)

            ########## ANÁLISIS IA DE LA SALIDA ######################

            # **** Step 4.5: AI Country-Level Analysis with DeepSeek ****
            logger.info("Step 4.5: Generating AI-based analysis (DeepSeek)...")
            try:
                import requests, json

                # Cargar datos del comp_json (que ya exportaste en Step 4)
                with open(comp_json, "r", encoding="utf-8") as f:
                    comp_data = json.load(f)

                # Construir prompt
                prompt = f"""
                Analiza todas las promociones de todos los competidores en el país {country}.
                El resultado debe ser un JSON estructurado a nivel país con la siguiente forma:

                {{
                  "country": "{country}",
                  "analysis": {{
                    "most_aggressive_promotions": [
                      {{ "competitor": "...", "title": "...", "bonus_type": "...", "bonus_amount": "...", "url": "..." }}
                    ],
                    "highlighted_games": [
                      {{ "competitor": "...", "game": "...", "context": "..." }}
                    ],
                    "average_values_by_promo_type": [
                      {{ "bonus_type": "...", "average_bonus": "..." }}
                    ],
                    "distinctive_data": [
                      "punto que llame la atención"
                    ]
                  }}
                }}

                Ten en cuenta:
                - Identifica las promos más agresivas por % o monto.
                - Si hay juegos concretos destacados (jackpots, torneos, etc.), inclúyelos.
                - Calcula valores medios por tipo de promoción (ej. Welcome Bonus, Free Spins).
                - Incluye datos diferenciales que sobresalgan.

                Datos de entrada:
                {json.dumps(comp_data, ensure_ascii=False, indent=2)}
                """

                url = "https://api.deepseek.com/v1/chat/completions"
                headers = {
                    'Authorization': f'Bearer {self.deepseek_api_key}',
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "Eres un analista que genera insights de promociones de casinos online."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                }

                response = requests.post(url, headers=headers, json=payload)
                result = response.json()

                # Guardar salida en un JSON
                analysis_file = self.output_dir / f"country_analysis_{country}.json"
                with open(analysis_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                logger.info(f"AI analysis saved to {analysis_file}")

            except Exception as e:
                logger.error(f"DeepSeek analysis failed: {e}")


            ########## FIN ANÁLISIS IA DE LA SALIDA ######################
            
            # Step 5: Generate summary report
            summary = self.generate_summary_report(country, comparison_result, new_count, updated_count)
            
            logger.info("Analysis completed successfully!")
            
            return {
                'country': country,
                'total_promotions_scraped': len(promotions),
                'new_promotions': new_count,
                'updated_promotions': updated_count,
                'duplicate_promotions': duplicate_count,
                'comparison_result': comparison_result,
                'exported_files': {
                    'all_promotions_csv': csv_file,
                    'all_promotions_json': json_file,
                    'new_promotions_csv': comp_csv,
                    'comparison_summary_json': comp_json
                },
                'summary_report': summary
            }
            
        except Exception as e:
            logger.error(f"Error in full analysis: {e}")
            raise
        
    # def generate_summary_report(self, country: str, comparison_result: Dict, new_count: int, updated_count: int) -> Dict[str, Any]:
    #     """Generate a summary report of the analysis"""
    #     stats = self.db_manager.get_statistics(country)
        
    #     summary = {
    #         'analysis_date': datetime.now().isoformat(),
    #         'country': country,
    #         'database_statistics': stats,
    #         'scraping_results': {
    #             'new_promotions_found': new_count,
    #             'updated_promotions': updated_count,
    #             'total_active_promotions': stats.get('active_promotions', 0)
    #         },
    #         'comparison_results': {
    #             'new_promotions_count': comparison_result.get('new_count', 0),
    #             'removed_promotions_count': comparison_result.get('removed_count', 0),
    #             'competitors_analyzed': comparison_result.get('competitors_analyzed', [])
    #         },
    #         'key_insights': self.generate_insights(stats, comparison_result)
    #     }
        
    #     return summary

    def generate_summary_report(self, country: str, comparison_result: Dict, new_count: int, updated_count: int) -> Dict[str, Any]:
        # Usa estadísticas CLEAN
        stats = self.db_manager.get_statistics_clean(country)

        summary = {
            'analysis_date': datetime.now().isoformat(),
            'country': country,
            'database_statistics': stats,
            'scraping_results': {
                'new_promotions_found': comparison_result.get('new_count', 0),
                'updated_promotions': 0,  # si quieres, mantenlo en 0 o impleméntalo clean
                'total_active_promotions': stats.get('total_promotions', 0)
            },
            'comparison_results': {
                'new_promotions_count': comparison_result.get('new_count', 0),
                'removed_promotions_count': comparison_result.get('removed_count', 0),
                'competitors_analyzed': comparison_result.get('competitors_analyzed', [])
            },
            'key_insights': self.generate_insights(stats, comparison_result)
        }
        return summary

        
    def generate_insights(self, stats: Dict, comparison_result: Dict) -> List[str]:
        """Generate key insights from the analysis"""
        insights = []
        
        # Competitor analysis
        by_competitor = stats.get('by_competitor', {})
        if by_competitor:
            most_active = max(by_competitor.items(), key=lambda x: x[1])
            insights.append(f"{most_active[0]} has the most promotions ({most_active[1]} active)")
            
            if len(by_competitor) > 1:
                least_active = min(by_competitor.items(), key=lambda x: x[1])
                insights.append(f"{least_active[0]} has the fewest promotions ({least_active[1]} active)")
        
        # Bonus type analysis
        by_type = stats.get('by_type', {})
        if by_type:
            most_common_type = max(by_type.items(), key=lambda x: x[1])
            insights.append(f"Most common bonus type: {most_common_type[0]} ({most_common_type[1]} promotions)")
        
        # New promotions insight
        new_count = comparison_result.get('new_count', 0)
        if new_count > 0:
            insights.append(f"{new_count} new promotions detected in this analysis")
        else:
            insights.append("No new promotions detected since last analysis")
            
        # Removed promotions insight
        removed_count = comparison_result.get('removed_count', 0)
        if removed_count > 0:
            insights.append(f"{removed_count} promotions were removed or expired")
            
        return insights

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Competitor Analysis System')
    parser.add_argument('--country', default='UAE', help='Country to analyze (default: UAE)')
    parser.add_argument('--use-proxy', action='store_true', help='Use proxy for scraping')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # Create analysis system
    system = CompetitorAnalysisSystem(use_proxy=args.use_proxy, headless=args.headless)
    
    try:
        # Run full analysis
        results = await system.run_full_analysis(args.country)
        
        # Print summary
        print("\n" + "="*60)
        print("COMPETITOR ANALYSIS SUMMARY")
        print("="*60)
        print(f"Country: {results['country']}")
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Promotions Scraped: {results['total_promotions_scraped']}")
        print(f"New Promotions: {results['new_promotions']}")
        print(f"Updated Promotions: {results['updated_promotions']}")
        print(f"Duplicate Promotions: {results['duplicate_promotions']}")
        
        print("\nComparison Results:")
        comp_result = results['comparison_result']
        print(f"  New promotions found: {comp_result.get('new_count', 0)}")
        print(f"  Removed promotions: {comp_result.get('removed_count', 0)}")
        print(f"  Competitors analyzed: {', '.join(comp_result.get('competitors_analyzed', []))}")
        
        print("\nExported Files:")
        for file_type, file_path in results['exported_files'].items():
            if file_path:
                print(f"  {file_type}: {file_path}")
        
        print("\nKey Insights:")
        for insight in results['summary_report']['key_insights']:
            print(f"  • {insight}")
            
        print("\n" + "="*60)
        print("Analysis completed successfully!")
        print("Files are ready for dashboard generation.")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
