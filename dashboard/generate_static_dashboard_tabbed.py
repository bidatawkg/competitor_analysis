import json
import os
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

class TabbedStaticDashboardGenerator:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_and_clean_country_data(self, country_code: str):
        """Load cleaned JSON promotions and remove duplicates with fuzzy similarity"""
        json_path = max(
            self.output_dir.glob(f"clean_promotions_new_{country_code}_*.json"),
            key=os.path.getctime,
            default=None,
        )
        if not json_path:
            raise FileNotFoundError(f"No clean promotions JSON found for {country_code}")

        with open(json_path, "r", encoding="utf-8") as f:
            promotions = json.load(f)

        return self._dedupe_promotions(promotions)

    def _is_similar(self, a: str, b: str, threshold=0.85) -> bool:
        """Check if two strings are similar enough to be considered duplicates"""
        return SequenceMatcher(None, a, b).ratio() >= threshold

    def _dedupe_promotions(self, promos):
        unique = []
        for p in promos:
            desc_p = (p.get("description") or "").lower()
            btype_p = (p.get("bonus_type") or "").lower()
            comp_p = (p.get("competitor") or "").lower()

            is_dup = False
            for u in unique:
                desc_u = (u.get("description") or "").lower()
                btype_u = (u.get("bonus_type") or "").lower()
                comp_u = (u.get("competitor") or "").lower()

                if comp_p == comp_u and btype_p == btype_u:
                    if self._is_similar(desc_p, desc_u):
                        is_dup = True
                        break

            if not is_dup:
                unique.append(p)
        return unique

    def generate_tabbed_dashboard(self, countries):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"dashboard_tabbed_final.html"

        tabs = []
        contents = []

        for country in countries:
            try:
                promotions = self.load_and_clean_country_data(country)
            except FileNotFoundError:
                continue

            tabs.append(f'<button class="tablinks" onclick="openTab(event, \'{country}\')">{country}</button>')
            contents.append(self.generate_country_tab(country, promotions))

        html_content = self._wrap_html("\n".join(tabs), "\n".join(contents))
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_file

    def generate_country_tab(self, country, promotions):
        total_promos = len(promotions)
        competitors = {p.get("competitor", "Unknown") for p in promotions}
        total_competitors = len(competitors)
        new_promotions = total_promos  # All are "new" in this context
        bonus_types = {p.get("bonus_type", "Other") for p in promotions}

        cards = []
        for p in promotions:
            bonus_type = p.get("bonus_type", "Other")
            amount = p.get("bonus_amount", "N/A")
            competitor = p.get("competitor", "N/A")
            desc = p.get("description", "")
            url = p.get("url", "#")

            cards.append(f"""
            <div class="promo-card" data-bonus-type="{bonus_type}">
                <h2>{competitor}</h2>
                <h4>{bonus_type}</h4>
                <p><strong style="color:red">{amount}</strong></p>
                <p>{desc}</p>
                <a href="{url}" target="_blank">Visit site</a>
            </div>
            """)

        # JSON for chart data
        chart_data = json.dumps(promotions)

        return f"""
        <div id="{country}" class="tabcontent">
            <h2>{country} - Market Overview</h2>
            <div class="stats-row">
                <div class="stat-box"><h3>{total_competitors}</h3><p>Competitors</p></div>
                <div class="stat-box"><h3>{total_promos}</h3><p>Total Promotions</p></div>
                <div class="stat-box"><h3>{new_promotions}</h3><p>New Promotions</p></div>
                <div class="stat-box"><h3>{len(bonus_types)}</h3><p>Bonus Types</p></div>
            </div>

            <div class="filter-row">
                <label for="filter-{country}">Filter by Bonus Type:</label>
                <select id="filter-{country}" onchange="filterPromotions('{country}')">
                    <option value="All">All</option>
                    {''.join(f'<option value="{b}">{b}</option>' for b in bonus_types)}
                </select>
            </div>

            <div class="charts-row">
                <div class="chart-box"><canvas id="pie_{country}"></canvas></div>
                <div class="chart-box"><canvas id="bar_{country}"></canvas></div>
            </div>

            <div class="promotions-grid" id="promos-{country}">
                {''.join(cards)}
            </div>

            <script>
                const data_{country} = {chart_data};
                renderCharts("{country}", data_{country});
            </script>
        </div>
        """

    def _wrap_html(self, tabs, contents):
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Competitor Promotions Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
.tab button {{ background: #eee; border: none; padding: 10px; cursor: pointer; }}
.tabcontent {{ display: none; padding: 20px; border-top: none; }}
.stats-row {{ display: flex; gap: 20px; margin-bottom: 20px; }}
.stat-box {{ flex: 1; background: #f5f5f5; padding: 15px; text-align: center; border-radius: 8px; }}
.promotions-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 20px; }}
.promo-card {{ border: 1px solid #ddd; padding: 10px; border-radius: 8px; background: #fff; }}
.filter-row {{ margin: 15px 0; }}
.charts-row {{ display: flex; gap: 20px; justify-content: space-around; margin: 20px 0; }}
.chart-box {{ flex: 1; width: 500px; height: 550px; }}
.chart-box canvas {{ max-width: 100% !important; max-height: 300px !important; }}
</style>
</head>
<body>

<h1>Competitor Promotions Dashboard</h1>
<div class="tab">{tabs}</div>
{contents}

<script>
function openTab(evt, tabName) {{
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {{
        tabcontent[i].style.display = "none";
    }}
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {{
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }}
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}}
document.querySelector(".tab button").click();

function filterPromotions(country) {{
    const select = document.getElementById("filter-" + country);
    const value = select.value;
    const cards = document.querySelectorAll("#promos-" + country + " .promo-card");
    cards.forEach(c => {{
        if (value === "All" || c.dataset.bonusType === value) {{
            c.style.display = "block";
        }} else {{
            c.style.display = "none";
        }}
    }});
}}

function renderCharts(country, data) {{
    const counts = {{}};
    const compCounts = {{}};
    data.forEach(p => {{
        counts[p.bonus_type] = (counts[p.bonus_type] || 0) + 1;
        compCounts[p.competitor] = (compCounts[p.competitor] || 0) + 1;
    }});

    const ctxPie = document.getElementById("pie_" + country).getContext("2d");
    new Chart(ctxPie, {{
        type: "pie",
        data: {{
            labels: Object.keys(counts),
            datasets: [{{ data: Object.values(counts), backgroundColor: ["#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f","#edc949"] }}]
        }}
    }});

    const ctxBar = document.getElementById("bar_" + country).getContext("2d");
    new Chart(ctxBar, {{
        type: "bar",
        data: {{
            labels: Object.keys(compCounts),
            datasets: [{{ label: "Promotions", data: Object.values(compCounts), backgroundColor: "#4e79a7" }}]
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
    }});
}}
</script>

</body>
</html>
        """

