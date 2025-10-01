#!/usr/bin/env python3
"""
Static Dashboard Generator with Tabbed Navigation
Creates a completely static HTML file with country navigation tabs
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TabbedStaticDashboardGenerator:
    """Generates a completely static HTML dashboard with tabbed country navigation"""
    
    def __init__(self, output_dir: str = None, dashboard_dir: str = None):
        self.output_dir = output_dir or "output"
        self.dashboard_dir = dashboard_dir or "dashboard"
        
    def find_latest_files_for_country(self, country: str) -> Dict[str, Optional[str]]:
        """Find the latest data files for a specific country"""
        files = {}
        
        # Find promotions file
        promotions_pattern = f"{self.output_dir}/promotions_{country}_*.json"
        promotions_files = glob.glob(promotions_pattern)
        if promotions_files:
            files['promotions'] = max(promotions_files, key=os.path.getctime)
            
        # Find comparison file
        comparison_pattern = f"{self.output_dir}/comparison_summary_{country}_*.json"
        comparison_files = glob.glob(comparison_pattern)
        if comparison_files:
            files['comparison'] = max(comparison_files, key=os.path.getctime)
            
        return files
        
    def clean_promotion_data(self, promo: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and format promotion data for display"""
        # Clean title - remove excessive whitespace and newlines
        title = promo.get('title', '').strip()
        title = re.sub(r'\s+', ' ', title)  # Replace multiple spaces with single space
        title = title.replace('\n', ' ').replace('\r', '')
        
        # Limit title length
        if len(title) > 100:
            title = title[:97] + "..."
            
        # Clean description
        description = promo.get('description', '').strip()
        description = re.sub(r'\s+', ' ', description)
        description = description.replace('\n', ' ').replace('\r', '')
        
        # Limit description length
        if len(description) > 200:
            description = description[:197] + "..."
            
        # Clean bonus amount
        bonus_amount = promo.get('bonus_amount', '').strip()
        if not bonus_amount:
            bonus_amount = "N/A"
            
        # Clean bonus type
        bonus_type = promo.get('bonus_type', 'Other').strip()
        if not bonus_type:
            bonus_type = "Other"
            
        # Clean conditions
        conditions = promo.get('conditions', '').strip()
        if len(conditions) > 150:
            conditions = conditions[:147] + "..."
            
        # Clean valid until
        valid_until = promo.get('valid_until', '').strip()
        if not valid_until:
            valid_until = "N/A"
            
        return {
            'competitor': promo.get('competitor', 'Unknown'),
            'country': promo.get('country', ''),
            'title': title if title else 'Promotion Available',
            'description': description if description else 'Details available on website',
            'bonus_amount': bonus_amount,
            'bonus_type': bonus_type,
            'conditions': conditions if conditions else 'See website for terms',
            'valid_until': valid_until,
            'url': promo.get('url', ''),
            'scraped_at': promo.get('scraped_at', '')
        }
        
    def load_and_clean_country_data(self, country: str) -> Dict[str, Any]:
        """Load and clean real data for a country"""
        files = self.find_latest_files_for_country(country)
        data = {'promotions': [], 'comparison': {}}
        
        # Load promotions data
        if 'promotions' in files and files['promotions']:
            try:
                with open(files['promotions'], 'r', encoding='utf-8') as f:
                    promotions_data = json.load(f)
                    
                    # Clean and filter promotions
                    valid_promotions = []
                    for promo in promotions_data:
                        # Only include promotions with meaningful content
                        title = promo.get('title', '').strip()
                        competitor = promo.get('competitor', '').strip()
                        
                        if (title and len(title) > 10 and competitor and 
                            not title.startswith('\\n\\n\\n') and
                            ('casino' in title.lower() or 'bonus' in title.lower() or 
                             'promotion' in title.lower() or promo.get('bonus_amount'))):
                            
                            cleaned_promo = self.clean_promotion_data(promo)
                            valid_promotions.append(cleaned_promo)
                    
                    data['promotions'] = valid_promotions
                    logger.info(f"Loaded {len(valid_promotions)} valid promotions for {country}")
                    
            except Exception as e:
                logger.error(f"Error loading promotions for {country}: {e}")
                
        # Load comparison data
        if 'comparison' in files and files['comparison']:
            try:
                with open(files['comparison'], 'r', encoding='utf-8') as f:
                    data['comparison'] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading comparison for {country}: {e}")
                
        return data
        
    def generate_tabbed_html(self, countries: List[str] = None) -> str:
        """Generate completely static HTML with tabbed navigation"""
        if countries is None:
            countries = ["UAE", "Saudi Arabia", "Kuwait"]
            
        # Load all real data
        all_data = {}
        total_promotions = 0
        all_competitors = set()
        
        for country in countries:
            country_data = self.load_and_clean_country_data(country)
            if country_data['promotions']:  # Only include countries with real data
                all_data[country] = country_data
                total_promotions += len(country_data['promotions'])
                
                # Collect competitors
                for promo in country_data['promotions']:
                    all_competitors.add(promo['competitor'])
                    
        if not all_data:
            raise ValueError("No valid promotion data found. Please run analysis first.")
            
        # Calculate statistics
        stats = self.calculate_statistics(all_data)
        
        # Generate HTML
        html_content = self.create_tabbed_html_content(all_data, stats)
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(self.dashboard_dir, f"tabbed_dashboard_{timestamp}.html")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        # Also create final version
        final_file = os.path.join(self.dashboard_dir, "dashboard_tabbed_final.html")
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"Tabbed dashboard generated: {final_file}")
        return final_file
        
    def calculate_statistics(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics from real data"""
        total_promotions = 0
        all_competitors = set()
        bonus_types = {}
        countries_stats = {}
        
        for country, data in all_data.items():
            promotions = data.get('promotions', [])
            comparison = data.get('comparison', {})
            
            # Country-specific stats
            country_competitors = set()
            country_bonus_types = {}
            
            for promo in promotions:
                competitor = promo.get('competitor', 'Unknown')
                bonus_type = promo.get('bonus_type', 'Other')
                
                all_competitors.add(competitor)
                country_competitors.add(competitor)
                
                bonus_types[bonus_type] = bonus_types.get(bonus_type, 0) + 1
                country_bonus_types[bonus_type] = country_bonus_types.get(bonus_type, 0) + 1
                
            countries_stats[country] = {
                'total_promotions': len(promotions),
                'competitors': list(country_competitors),
                'competitor_count': len(country_competitors),
                'bonus_types': country_bonus_types,
                'new_promotions': comparison.get('new_promotions_count', 0),
                'last_update': comparison.get('comparison_date', datetime.now().strftime('%Y-%m-%d'))
            }
            
            total_promotions += len(promotions)
            
        return {
            'total_promotions': total_promotions,
            'total_competitors': len(all_competitors),
            'total_countries': len(all_data),
            'all_competitors': list(all_competitors),
            'bonus_types': bonus_types,
            'countries_stats': countries_stats,
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    def create_tabbed_html_content(self, all_data: Dict[str, Any], stats: Dict[str, Any]) -> str:
        """Create the complete tabbed HTML content"""
        
        # Generate country tabs navigation
        country_tabs_nav = self.generate_country_tabs_nav(all_data)
        
        # Generate country tab contents
        country_tabs_content = self.generate_country_tabs_content(all_data, stats)
        
        # Generate overall statistics
        overall_stats_html = self.generate_overall_stats(stats)
        
        # Generate insights
        insights_html = self.generate_insights(stats, all_data)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YYY Casino - Competitor Analysis Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        .header h1 {{
            color: #2c3e50;
            font-size: 2.8rem;
            margin-bottom: 15px;
            font-weight: 700;
        }}

        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.2rem;
            margin-bottom: 20px;
        }}

        .header .meta-info {{
            color: #95a5a6;
            font-size: 1rem;
            margin-top: 15px;
        }}

        .overall-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 35px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
        }}

        .stat-number {{
            font-size: 3.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 10px;
            display: block;
        }}

        .stat-label {{
            color: #7f8c8d;
            font-size: 1.1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* Tab Navigation Styles */
        .tabs-container {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }}

        .tabs-nav {{
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #e9ecef;
            flex-wrap: wrap;
        }}

        .tab-button {{
            background: none;
            border: none;
            padding: 15px 30px;
            font-size: 1.1rem;
            font-weight: 600;
            color: #7f8c8d;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            margin: 0 5px;
        }}

        .tab-button.active {{
            color: #667eea;
            border-bottom-color: #667eea;
        }}

        .tab-button:hover:not(.active) {{
            color: #495057;
            background: rgba(102, 126, 234, 0.1);
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .country-header {{
            text-align: center;
            margin-bottom: 30px;
        }}

        .country-title {{
            color: #2c3e50;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 15px;
        }}

        .country-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .country-stat {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(240, 147, 251, 0.3);
        }}

        .country-stat-number {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .country-stat-label {{
            font-size: 1rem;
            opacity: 0.9;
            font-weight: 500;
        }}

        .promotions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }}

        .promotion-card {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid #667eea;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .promotion-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
        }}

        .promotion-competitor {{
            color: #667eea;
            font-weight: 700;
            font-size: 1.2rem;
            margin-bottom: 12px;
        }}

        .promotion-title {{
            color: #2c3e50;
            font-weight: 600;
            margin-bottom: 12px;
            line-height: 1.4;
            font-size: 1.05rem;
        }}

        .promotion-bonus {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 12px;
            font-size: 0.95rem;
        }}

        .promotion-type {{
            background: #e9ecef;
            color: #495057;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
            margin-left: 10px;
        }}

        .promotion-description {{
            color: #6c757d;
            font-size: 0.95rem;
            margin-top: 12px;
            line-height: 1.5;
        }}

        .insights-section {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }}

        .insights-title {{
            color: #2c3e50;
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 25px;
            text-align: center;
        }}

        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
        }}

        .insight-card {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(79, 172, 254, 0.3);
        }}

        .insight-card h4 {{
            font-size: 1.3rem;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        .insight-card p {{
            font-size: 1rem;
            line-height: 1.6;
            opacity: 0.95;
        }}

        .no-data {{
            text-align: center;
            padding: 60px;
            color: #7f8c8d;
            font-size: 1.2rem;
        }}

        .footer {{
            text-align: center;
            margin-top: 50px;
            color: rgba(255, 255, 255, 0.9);
            padding: 30px;
        }}

        .footer p {{
            margin: 8px 0;
            font-size: 1rem;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            
            .header h1 {{
                font-size: 2.2rem;
            }}
            
            .tabs-nav {{
                flex-direction: column;
            }}
            
            .tab-button {{
                margin: 5px 0;
            }}
            
            .promotions-grid {{
                grid-template-columns: 1fr;
            }}
            
            .overall-stats {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎰 YYY Casino - Competitor Analysis</h1>
            <p class="subtitle">Real-time competitive intelligence dashboard</p>
            <div class="meta-info">
                <strong>Analysis Date:</strong> {stats['generation_date']}<br>
                <strong>Countries Available:</strong> {', '.join(all_data.keys())}<br>
                <strong>Total Promotions Found:</strong> {stats['total_promotions']} real promotions
            </div>
        </div>

        <!-- Overall Statistics -->
        {overall_stats_html}

        <!-- Key Insights -->
        {insights_html}

        <!-- Country Tabs -->
        <div class="tabs-container">
            <div class="tabs-nav">
                {country_tabs_nav}
            </div>
            
            {country_tabs_content}
        </div>

        <!-- Footer -->
        <div class="footer">
            <p><strong>© 2024 YYY Casino - Data & AI Department</strong></p>
            <p>Dashboard generated with real competitor data • Last updated: {stats['generation_date']}</p>
            <p>All data sourced from actual competitor websites • No simulated or sample data</p>
        </div>
    </div>

    <script>
        // Simple tab switching functionality
        function showTab(countryId) {{
            // Hide all tab contents
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => {{
                content.classList.remove('active');
            }});
            
            // Remove active class from all buttons
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(button => {{
                button.classList.remove('active');
            }});
            
            // Show selected tab content
            const selectedTab = document.getElementById(countryId);
            if (selectedTab) {{
                selectedTab.classList.add('active');
            }}
            
            // Add active class to clicked button
            const selectedButton = document.querySelector(`[onclick="showTab('${{countryId}}')"]`);
            if (selectedButton) {{
                selectedButton.classList.add('active');
            }}
        }}
        
        // Show first tab by default
        document.addEventListener('DOMContentLoaded', function() {{
            const firstTab = document.querySelector('.tab-content');
            const firstButton = document.querySelector('.tab-button');
            
            if (firstTab && firstButton) {{
                firstTab.classList.add('active');
                firstButton.classList.add('active');
            }}
        }});
    </script>
</body>
</html>"""
        
        return html_content
        
    def generate_overall_stats(self, stats: Dict[str, Any]) -> str:
        """Generate overall statistics HTML"""
        return f"""
        <div class="overall-stats">
            <div class="stat-card">
                <span class="stat-number">{stats['total_promotions']}</span>
                <div class="stat-label">Total Promotions</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{stats['total_competitors']}</span>
                <div class="stat-label">Active Competitors</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{stats['total_countries']}</span>
                <div class="stat-label">Countries Analyzed</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{len(stats['bonus_types'])}</span>
                <div class="stat-label">Bonus Types Found</div>
            </div>
        </div>
        """
        
    def generate_country_tabs_nav(self, all_data: Dict[str, Any]) -> str:
        """Generate country tabs navigation HTML"""
        nav_html = ""
        
        country_flags = {
            "UAE": "🇦🇪",
            "Saudi Arabia": "🇸🇦", 
            "Kuwait": "🇰🇼"
        }
        
        for country in all_data.keys():
            flag = country_flags.get(country, "🏳️")
            country_id = country.replace(" ", "_").lower()
            promotions_count = len(all_data[country].get('promotions', []))
            
            nav_html += f"""
            <button class="tab-button" onclick="showTab('{country_id}')">
                {flag} {country} ({promotions_count})
            </button>
            """
            
        return nav_html
        
    def generate_country_tabs_content(self, all_data: Dict[str, Any], stats: Dict[str, Any]) -> str:
        """Generate country tab contents HTML"""
        content_html = ""
        
        country_flags = {
            "UAE": "🇦🇪",
            "Saudi Arabia": "🇸🇦", 
            "Kuwait": "🇰🇼"
        }
        
        for country, data in all_data.items():
            country_id = country.replace(" ", "_").lower()
            flag = country_flags.get(country, "🏳️")
            promotions = data.get('promotions', [])
            country_stats = stats['countries_stats'].get(country, {})
            
            # Country statistics
            country_stats_html = f"""
            <div class="country-stats">
                <div class="country-stat">
                    <div class="country-stat-number">{len(promotions)}</div>
                    <div class="country-stat-label">Total Promotions</div>
                </div>
                <div class="country-stat">
                    <div class="country-stat-number">{country_stats.get('competitor_count', 0)}</div>
                    <div class="country-stat-label">Active Competitors</div>
                </div>
                <div class="country-stat">
                    <div class="country-stat-number">{country_stats.get('new_promotions', 0)}</div>
                    <div class="country-stat-label">New Promotions</div>
                </div>
                <div class="country-stat">
                    <div class="country-stat-number">{len(country_stats.get('bonus_types', {}))}</div>
                    <div class="country-stat-label">Bonus Types</div>
                </div>
            </div>
            """
            
            # Promotions grid
            promotions_html = ""
            if promotions:
                promotions_html = '<div class="promotions-grid">'
                for promo in promotions:
                    promotions_html += f"""
                    <div class="promotion-card">
                        <div class="promotion-competitor">{promo['competitor']}</div>
                        <div class="promotion-title">{promo['title']}</div>
                        <div>
                            <span class="promotion-bonus">{promo['bonus_amount']}</span>
                            <span class="promotion-type">{promo['bonus_type']}</span>
                        </div>
                        <div class="promotion-description">{promo['description']}</div>
                    </div>
                    """
                promotions_html += '</div>'
            else:
                promotions_html = '<div class="no-data">No promotions found for this country</div>'
                
            content_html += f"""
            <div id="{country_id}" class="tab-content">
                <div class="country-header">
                    <h2 class="country-title">{flag} {country}</h2>
                </div>
                {country_stats_html}
                {promotions_html}
            </div>
            """
            
        return content_html
        
    def generate_insights(self, stats: Dict[str, Any], all_data: Dict[str, Any]) -> str:
        """Generate insights HTML"""
        insights = []
        
        # Combine all promotions for analysis
        all_promotions = []
        for country, data in all_data.items():
            for promo in data.get('promotions', []):
                promo_copy = promo.copy()
                promo_copy['country'] = country
                all_promotions.append(promo_copy)
        
        # Most active competitor
        competitor_counts = {}
        for promo in all_promotions:
            comp = promo.get('competitor', 'Unknown')
            competitor_counts[comp] = competitor_counts.get(comp, 0) + 1
            
        if competitor_counts:
            top_competitor = max(competitor_counts.keys(), key=lambda x: competitor_counts[x])
            insights.append({
                'title': '🏆 Most Active Competitor',
                'description': f'{top_competitor} leads the market with {competitor_counts[top_competitor]} active promotions across all analyzed countries.'
            })
            
        # Most common bonus type
        bonus_types = stats.get('bonus_types', {})
        if bonus_types:
            top_bonus_type = max(bonus_types.keys(), key=lambda x: bonus_types[x])
            insights.append({
                'title': '🎁 Popular Promotion Type',
                'description': f'{top_bonus_type} is the most common promotion type with {bonus_types[top_bonus_type]} offers, indicating market preference.'
            })
            
        # Market coverage
        insights.append({
            'title': '🌍 Market Coverage',
            'description': f'Analysis covers {stats["total_countries"]} countries with {stats["total_competitors"]} unique competitors, providing comprehensive market intelligence.'
        })
        
        # Data freshness
        insights.append({
            'title': '⏰ Real-time Data',
            'description': f'All {stats["total_promotions"]} promotions are sourced from live competitor websites, ensuring accuracy and relevance for strategic decisions.'
        })
        
        insights_html = f"""
        <div class="insights-section">
            <h3 class="insights-title">📊 Key Market Insights</h3>
            <div class="insights-grid">
        """
        
        for insight in insights:
            insights_html += f"""
                <div class="insight-card">
                    <h4>{insight['title']}</h4>
                    <p>{insight['description']}</p>
                </div>
            """
            
        insights_html += """
            </div>
        </div>
        """
        
        return insights_html

def main():
    """Main function to generate tabbed dashboard"""
    generator = TabbedStaticDashboardGenerator()
    
    try:
        dashboard_file = generator.generate_tabbed_html()
        
        print("\n" + "="*80)
        print("TABBED DASHBOARD GENERATION COMPLETED")
        print("="*80)
        print(f"Dashboard file: {dashboard_file}")
        print("\n✅ Tabbed dashboard ready!")
        print("📊 Open dashboard_tabbed_final.html in your browser")
        print("🎯 Navigate between countries with tabs!")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error generating tabbed dashboard: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
