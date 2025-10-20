#!/usr/bin/env python3
"""
Complete Competitor Analysis Runner - FINAL TABBED VERSION
Executes analysis for all countries and generates TABBED STATIC dashboard
"""

import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any
import os
import sys

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import CompetitorAnalysisSystem
from dashboard.generate_static_dashboard_tabbed import TabbedStaticDashboardGenerator

# 🔧 Fix para Windows: usar SelectorEventLoop en lugar de ProactorEventLoop
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinalAnalysisRunner:
    """Runs complete analysis for all countries and generates TABBED STATIC dashboard"""
    
    def __init__(self):
        # self.countries = ["AE", "SA", "KW", "QA", "OM", "BH", "JO", "NZ"]
        self.countries = ["CH"]
        # self.countries = ["DE","AT","CH"]
        self.analysis_system = CompetitorAnalysisSystem()
        self.dashboard_generator = TabbedStaticDashboardGenerator()
        
    async def run_complete_analysis(self, countries: List[str] = None) -> Dict[str, Any]:
        """Run analysis for all specified countries"""
        if countries is None:
            countries = self.countries
            
        logger.info(f"Starting complete analysis for countries: {', '.join(countries)}")
        
        results = {}
        total_promotions = 0
        
        for country in countries:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"ANALYZING COUNTRY: {country}")
                logger.info(f"{'='*60}")
                
                # Run analysis for this country
                country_result = await self.analysis_system.run_full_analysis(country)
                
                if 'error' not in country_result:
                    results[country] = country_result
                    total_promotions += country_result.get('total_promotions_scraped', 0)
                    
                    logger.info(f"✅ {country} analysis completed:")
                    logger.info(f"   - Promotions found: {country_result.get('total_promotions_scraped', 0)}")
                    logger.info(f"   - New promotions: {country_result.get('new_promotions', 0)}")
                    logger.info(f"   - Updated promotions: {country_result.get('updated_promotions', 0)}")
                else:
                    logger.error(f"❌ {country} analysis failed: {country_result.get('message', 'Unknown error')}")
                    results[country] = country_result
                    
            except Exception as e:
                logger.error(f"❌ Error analyzing {country}: {e}")
                results[country] = {
                    'error': str(e),
                    'country': country,
                    'total_promotions_scraped': 0
                }
                
        # Generate summary
        summary = self._generate_complete_summary(results, total_promotions)
        
        logger.info(f"\n{'='*60}")
        logger.info("COMPLETE ANALYSIS SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Countries analyzed: {len(countries)}")
        logger.info(f"Total promotions found: {total_promotions}")
        logger.info(f"Successful countries: {len([r for r in results.values() if 'error' not in r])}")
        logger.info(f"Failed countries: {len([r for r in results.values() if 'error' in r])}")
        
        return {
            'summary': summary,
            'results_by_country': results,
            'total_promotions': total_promotions,
            'analysis_date': datetime.now().isoformat()
        }
        
    def _generate_complete_summary(self, results: Dict[str, Any], total_promotions: int) -> Dict[str, Any]:
        """Generate complete analysis summary"""
        successful_countries = []
        failed_countries = []
        
        for country, result in results.items():
            if 'error' not in result:
                successful_countries.append({
                    'country': country,
                    'promotions': result.get('total_promotions_scraped', 0),
                    'new_promotions': result.get('new_promotions', 0),
                    'competitors': result.get('summary_report', {}).get('competitors_analyzed', [])
                })
            else:
                failed_countries.append({
                    'country': country,
                    'error': result.get('message', 'Unknown error')
                })
                
        return {
            'total_countries_analyzed': len(results),
            'successful_countries': successful_countries,
            'failed_countries': failed_countries,
            'total_promotions_found': total_promotions,
            'success_rate': len(successful_countries) / len(results) * 100 if results else 0
        }
        
    def generate_tabbed_dashboard(self, countries: List[str] = None) -> str:
        """Generate TABBED STATIC dashboard with country navigation"""
        if countries is None:
            countries = self.countries
            
        logger.info("Generating TABBED STATIC dashboard with country navigation...")
        
        try:
            # Generate tabbed dashboard for all countries
            # dashboard_file = self.dashboard_generator.generate_tabbed_html(countries)
            dashboard_file = self.dashboard_generator.generate_tabbed_dashboard(countries)
            
            logger.info(f"✅ Tabbed dashboard generated: {dashboard_file}")
            return dashboard_file
            
        except Exception as e:
            logger.error(f"❌ Error generating tabbed dashboard: {e}")
            raise
            
    async def run_everything(self, countries: List[str] = None) -> Dict[str, Any]:
        """Run complete analysis and generate TABBED STATIC dashboard in one command"""
        logger.info("🚀 STARTING COMPLETE COMPETITOR ANALYSIS SYSTEM - FINAL TABBED VERSION")
        logger.info("="*80)
        
        # Step 1: Run analysis for all countries
        analysis_results = await self.run_complete_analysis(countries)
        
        # Step 2: Generate TABBED STATIC dashboard
        try:
            dashboard_file = self.generate_tabbed_dashboard(countries)
            analysis_results['dashboard_file'] = dashboard_file
        except Exception as e:
            logger.error(f"Tabbed dashboard generation failed: {e}")
            analysis_results['dashboard_error'] = str(e)
            
        # Step 3: Final summary
        logger.info("\n" + "="*80)
        logger.info("🎯 COMPLETE ANALYSIS FINISHED - TABBED DASHBOARD READY")
        logger.info("="*80)
        
        if 'dashboard_file' in analysis_results:
            logger.info(f"✅ TABBED Dashboard ready: {analysis_results['dashboard_file']}")
            logger.info("📊 Open dashboard_tabbed_final.html in your browser")
            logger.info("🎯 Navigate between countries with professional tabs!")
            logger.info("💡 Clean, organized, professional presentation")
        else:
            logger.error("❌ Tabbed dashboard generation failed")
            
        logger.info(f"📈 Total promotions analyzed: {analysis_results['total_promotions']}")
        logger.info(f"🌍 Countries processed: {len(analysis_results['results_by_country'])}")
        
        return analysis_results

async def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description='Complete Competitor Analysis System - FINAL TABBED VERSION')
    parser.add_argument('--countries', nargs='+', 
                       choices=['UAE', 'Saudi Arabia', 'Kuwait'],
                       help='Countries to analyze (default: all)')
    parser.add_argument('--mode', choices=['analysis', 'dashboard', 'complete'],
                       default='complete',
                       help='Mode: analysis only, dashboard only, or complete (default)')
    
    args = parser.parse_args()
    
    runner = FinalAnalysisRunner()
    
    try:
        if args.mode == 'analysis':
            # Run analysis only
            results = await runner.run_complete_analysis(args.countries)
            print("\n✅ Analysis completed. Run with --mode dashboard to generate tabbed dashboard.")
            
        elif args.mode == 'dashboard':
            # Generate TABBED dashboard only
            dashboard_file = runner.generate_tabbed_dashboard(args.countries)
            print(f"\n✅ TABBED Dashboard generated: {dashboard_file}")
            print("🎯 Professional country navigation with tabs!")
            
        else:
            # Run everything
            results = await runner.run_everything(args.countries)
            
            if 'dashboard_file' in results:
                print(f"\n🎉 SUCCESS! Complete analysis finished with TABBED dashboard.")
                print(f"📊 Dashboard: {results['dashboard_file']}")
                print(f"📈 Total promotions: {results['total_promotions']}")
                print("🎯 Open dashboard_tabbed_final.html - professional country navigation!")
            else:
                print(f"\n⚠️  Analysis completed but tabbed dashboard generation failed.")
                print(f"📈 Total promotions: {results['total_promotions']}")
                
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        print("\n❌ Analysis interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
