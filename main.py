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
from typing import List, Dict, Any
import argparse
from pathlib import Path

# Add project paths
base_dir = Path(__file__).resolve().parent
sys.path.append(str(base_dir))
sys.path.append(str(base_dir / "scraper"))
sys.path.append(str(base_dir / "database"))

from scraper.competitor_scraper import CompetitorScraper, PromotionData
from database.db_manager import DatabaseManager

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
    
    def __init__(self, use_proxy: bool = False, headless: bool = True):
        self.scraper = CompetitorScraper(use_proxy=use_proxy, headless=headless)
        self.db_manager = DatabaseManager()
        base_dir = Path(__file__).resolve().parent  # carpeta donde está main.py
        self.output_dir = base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)  # crea la carpeta si no existe
        
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
            
            # Step 3: Compare with previous data
            logger.info("Step 3: Comparing with previous data...")
            current_date = datetime.now().isoformat()[:10]  # YYYY-MM-DD format
            comparison_result = self.db_manager.compare_with_previous(country, current_date)
            
            # Step 4: Export results
            logger.info("Step 4: Exporting results...")
            csv_file = self.db_manager.export_to_csv(country, self.output_dir)
            json_file = self.db_manager.export_to_json(country, self.output_dir)
            
            # Export comparison results
            comp_csv, comp_json = self.db_manager.export_comparison_results(country, self.output_dir)
            
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
        
    def generate_summary_report(self, country: str, comparison_result: Dict, new_count: int, updated_count: int) -> Dict[str, Any]:
        """Generate a summary report of the analysis"""
        stats = self.db_manager.get_statistics(country)
        
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'country': country,
            'database_statistics': stats,
            'scraping_results': {
                'new_promotions_found': new_count,
                'updated_promotions': updated_count,
                'total_active_promotions': stats.get('active_promotions', 0)
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
