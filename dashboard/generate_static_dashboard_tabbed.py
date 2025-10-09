import json
import os
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict, Counter

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

class TabbedStaticDashboardGenerator:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_and_clean_country_data(self, country_code: str):
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
        return SequenceMatcher(None, a, b).ratio() >= threshold

    def _dedupe_promotions(self, promos):
        unique = []
        for p in promos:
            desc_p = (p.get("description") or "").lower()
            btype_p = (p.get("bonus_type") or "").strip().lower()
            comp_p = (p.get("competitor") or "").strip().lower()

            is_dup = False
            for u in unique:
                desc_u = (u.get("description") or "").lower()
                btype_u = (u.get("bonus_type") or "").strip().lower()
                comp_u = (u.get("competitor") or "").strip().lower()

                if comp_p == comp_u and btype_p == btype_u:
                    if self._is_similar(desc_p, desc_u):
                        is_dup = True
                        break

            if not is_dup:
                unique.append(p)
        return unique

    def generate_tabbed_dashboard(self, countries):
        output_file = self.output_dir / f"dashboard_tabbed_final.html"

        tabs = []
        contents = []

        for idx, country in enumerate(countries):
            try:
                promotions = self.load_and_clean_country_data(country)
            except FileNotFoundError:
                continue

            active_class = "pill--active" if idx == 0 else ""
            tabs.append(f'<button class="pill {active_class}" onclick="openTab(event, \'{country}\')">{country}</button>')
            contents.append(self.generate_country_tab(country, promotions, idx == 0))

        html_content = self._wrap_html("\n".join(tabs), "\n".join(contents))
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_file

    def generate_country_tab(self, country, promotions, visible=False):
        total_promos = len(promotions)
        competitors = {p.get("competitor", "Unknown").strip() for p in promotions}
        bonus_types = {p.get("bonus_type", "Other").strip() for p in promotions}

        type_counts = Counter([p.get("bonus_type", "Other").strip() for p in promotions])
        comp_types = defaultdict(lambda: Counter())
        for p in promotions:
            comp_types[p.get("competitor", "Unknown").strip()][p.get("bonus_type", "Other").strip()] += 1

        types_sorted = sorted(type_counts.keys())
        competitors_sorted = sorted(comp_types.keys())

        if not types_sorted:
            types_sorted = ["N/A"]
        if not competitors_sorted:
            competitors_sorted = ["N/A"]

        stacked_matrix = []
        for t in types_sorted:
            row = []
            for c in competitors_sorted:
                row.append(comp_types[c].get(t, 0))
            stacked_matrix.append(row)

        chart_payload = {
            "types": types_sorted,
            "typeCounts": [type_counts.get(t, 0) for t in types_sorted],
            "competitors": competitors_sorted,
            "stackedByType": stacked_matrix,
        }

        if not any(chart_payload["typeCounts"]):
            chart_payload["types"] = ["No data"]
            chart_payload["typeCounts"] = [1]
        if not any(sum(r) for r in chart_payload["stackedByType"]):
            chart_payload["competitors"] = ["No data"]
            chart_payload["stackedByType"] = [[1]]

        # --- Insights AI ---
        analysis_html = ""
        analysis = self.load_country_analysis(country)
        if analysis and "analysis" in analysis:
            a = analysis["analysis"]

            promo_list = "".join(
                f"<li><strong>{p['competitor']}</strong>: {p['bonus_type']} - {p['bonus_amount']} "
                f"<a href='{p['url']}' target='_blank'>Link</a></li>"
                for p in a.get("most_aggressive_promotions", [])
            )

            games_list = "".join(
                f"<li><strong>{g['competitor']}</strong>: {g['game']} <em>({g['context']})</em></li>"
                for g in a.get("highlighted_games", [])
            )

            avg_list = "".join(
                f"<li><strong>{v['bonus_type']}</strong>: {v['average_bonus']}</li>"
                for v in a.get("average_values_by_promo_type", [])
            )

            distinctive = "".join(f"<li>{d}</li>" for d in a.get("distinctive_data", []))

            analysis_html = f"""
            <div class="analysis">
                <h3>Key Market Insights ({country})</h3>
                <div class="analysis-section">
                    <h4>🎯 More aggressive promotions</h4>
                    <ul>{promo_list or "<li>No data</li>"}</ul>
                </div>
                <div class="analysis-section">
                    <h4>🎮 Highlighted games</h4>
                    <ul>{games_list or "<li>No data</li>"}</ul>
                </div>
                <div class="analysis-section">
                    <h4>📊 Average values by promotion type</h4>
                    <ul>{avg_list or "<li>No data</li>"}</ul>
                </div>
                <div class="analysis-section">
                    <h4>⭐ Differential data</h4>
                    <ul>{distinctive or "<li>No data</li>"}</ul>
                </div>
            </div>
            """

        cards = []
        for p in promotions:
            bonus_type = p.get("bonus_type", "Other").strip()
            amount = p.get("bonus_amount", "N/A")
            competitor = p.get("competitor", "N/A").strip()
            desc = p.get("description", "")
            url = p.get("url", "#")

            cards.append(f"""
            <article class="card" data-type="{bonus_type}" data-competitor="{competitor}">
                <header class="card__head">
                    <div class="badge">{bonus_type}</div>
                    <a class="link" href="{url}" target="_blank" rel="noopener">Open</a>
                </header>
                <h3 class="card__title">{competitor}</h3>
                <p class="card__amount">{amount}</p>
                <p class="card__desc">{desc}</p>
                <p class="card__wagering"><strong>Wagering:</strong> {wagering}</p>
            </article>
            """)

        return f"""
        <section id="{country}" class="country" {'style="display:block;"' if visible else ''}>
            <div class="section-head">
                <h2 class="country__title">{country}</h2>
                <div class="stats">
                    <div class="stat"><div class="stat__num">{len(competitors)}</div><div class="stat__label">Competitors</div></div>
                    <div class="stat"><div class="stat__num">{total_promos}</div><div class="stat__label">Promotions</div></div>
                    <div class="stat"><div class="stat__num">{len(bonus_types)}</div><div class="stat__label">Bonus types</div></div>
                </div>
            </div>

            <div class="controls">
                <div class="control">
                    <label>Promotion Type</label>
                    <select class="select" id="type-{country}" onchange="filterCards('{country}')">
                        <option value="ALL">All</option>
                        {''.join(f'<option value="{b}">{b}</option>' for b in bonus_types)}
                    </select>
                </div>
                <div class="control">
                    <label>Search</label>
                    <input class="input" type="search" id="search-{country}" placeholder="Filter by text..." oninput="filterCards('{country}')" />
                </div>
            </div>

            <div class="charts">
                <div class="chart"><canvas id="donut-{country}"></canvas></div>
                <div class="chart"><canvas id="stacked-{country}"></canvas></div>
            </div>

            {analysis_html}

            <div class="grid" id="grid-{country}">
                {''.join(cards) if cards else '<p class="empty">No hay promociones para este país.</p>'}
            </div>

            <script>
            (function() {{
                const payload = {json.dumps(chart_payload)};
                console.log("Chart payload for {country}", payload);
                renderDonut("donut-{country}", payload.types, payload.typeCounts);
                renderStacked("stacked-{country}", payload.competitors, payload.types, payload.stackedByType);
            }})();
            </script>
        </section>
        """

    def load_country_analysis(self, country_code: str):
        json_path = max(
            self.output_dir.glob(f"country_analysis_{country_code}.json"),
            key=os.path.getctime,
            default=None,
        )
        if not json_path:
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return data

    def _wrap_html(self, tabs, contents):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
    <meta charset="UTF-8">
    <title>Competitors Dashboard</title>

    <!-- Chart.js antes de cualquier uso -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <!-- Funciones de gráficos disponibles ANTES de los scripts inline -->
    <script>
    function renderDonut(canvasId, labels, data) {{
    const colors = ["#6aa0ff","#9b76ff","#f6ad55","#48bb78","#f56565","#ed64a6","#38b2ac"];
    new Chart(document.getElementById(canvasId), {{
        type:'doughnut',
        data:{{labels:labels,datasets:[{{data:data,backgroundColor:colors}}]}},
        options:{{plugins:{{legend:{{position:'bottom',labels:{{color:'#e5e9f0'}}}}}}}}
    }});
    }}
    function renderStacked(canvasId, competitors, types, stackedByType) {{
    const colors = ["#6aa0ff","#9b76ff","#f6ad55","#48bb78","#f56565","#ed64a6","#38b2ac"];
    const datasets = types.map((t,i)=>({{label:t,data:stackedByType[i],stack:'stack-1',backgroundColor:colors[i % colors.length]}}));
    new Chart(document.getElementById(canvasId), {{
        type:'bar',
        data:{{labels:competitors,datasets:datasets}},
        options:{{scales:{{x:{{stacked:true,ticks:{{color:'#e5e9f0'}}}},y:{{stacked:true,ticks:{{color:'#e5e9f0'}}}}}},plugins:{{legend:{{position:'bottom',labels:{{color:'#e5e9f0'}}}}}}}}
    }});
    }}
    </script>

    <!-- CSS COMPLETO (tema oscuro + layout + cards + charts + insights) -->
    <style>
    :root {{
    --bg: #0b0f19;
    --panel: #131a29;
    --muted: #718096;
    --text: #e5e9f0;
    --accent: #6aa0ff;
    --accent-2: #9b76ff;
    --shadow: 0 10px 30px rgba(0,0,0,.35);
    --radius: 14px;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: var(--bg); color: var(--text); }}
    .container {{ max-width: 1280px; margin:auto; padding:20px; }}
    h1 {{ font-size:28px; margin-bottom:10px; }}
    .subtitle {{ font-size:13px; color:var(--muted); }}
    .nav {{ display:flex; gap:10px; margin:20px 0; flex-wrap:wrap; }}
    .pill {{ border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.05); padding:10px 16px; border-radius:999px; cursor:pointer; color:var(--text); }}
    .pill--active {{ background: linear-gradient(180deg, var(--accent), var(--accent-2)); color:white; }}
    .country {{ display:none; background: var(--panel); padding:18px; border-radius:var(--radius); box-shadow:var(--shadow); margin-bottom:20px; }}
    .section-head {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }}
    .stats {{ display:flex; gap:12px; }}
    .stat {{ background:rgba(255,255,255,.05); padding:10px 14px; border-radius:10px; text-align:center; min-width:110px; }}
    .stat__num {{ font-size:20px; font-weight:700; }}
    .stat__label {{ font-size:12px; color:var(--muted); }}
    .controls {{ display:flex; gap:16px; flex-wrap:wrap; margin:14px 0; }}
    .control {{ display:flex; flex-direction:column; gap:6px; }}
    .select,.input {{ background:var(--panel); border:1px solid rgba(255,255,255,.1); color:var(--text); padding:8px 12px; border-radius:8px; }}
    .select:focus,.input:focus {{ outline:none; border-color: rgba(106,160,255,.6); }}
    .charts {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr)); gap:16px; margin:10px 0; }}
    .chart {{ background:rgba(255,255,255,.05); padding:12px; border-radius:10px; min-height: 340px; height: 340px; display:flex; justify-content:center; align-items:center;}}
    .chart canvas {{width:100%; height:100%;}}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:14px; margin-top:10px; }}
    .card {{ background:var(--panel); border-radius:12px; padding:14px; box-shadow:var(--shadow); border:1px solid rgba(255,255,255,.06); }}
    .card__head {{ display:flex; justify-content:space-between; align-items:center; }}
    .badge {{ font-size:12px; padding:6px 10px; border-radius:999px; background:rgba(106,160,255,.2); }}
    .link {{ font-size:12px; background: linear-gradient(180deg, var(--accent), var(--accent-2)); color:white; padding:6px 10px; border-radius:8px; text-decoration:none; }}
    .card__title {{ font-size:16px; font-weight:600; margin:6px 0; }}
    .card__amount {{ font-weight:700; color:#c7f464; margin:0 0 6px; }}
    .card__desc {{ font-size:13px; color:var(--muted); }}
    .analysis {{ margin:20px 0; padding:16px; background:rgba(255,255,255,.03); border-radius:12px; border:1px solid rgba(255,255,255,.06); }}
    .analysis h3 {{ margin-bottom:10px; font-size:18px; }}
    .analysis-section {{ margin-bottom:12px; }}
    .analysis-section h4 {{ font-size:15px; margin:6px 0; color: var(--accent); }}
    .analysis-section ul {{ margin:0; padding-left:18px; font-size:13px; }}
    .analysis-section li {{ margin:4px 0; }}
    .empty {{ color: var(--muted); font-size:14px; padding:12px; }}
    </style>
    </head>
    <body>
    <div class="container">
    <h1>Competitors Dashboard</h1>
    <div class="subtitle">Generated on {now}</div>
    <div class="nav">{tabs}</div>
    {contents}
    </div>

    <!-- Funciones de interacción generales -->
    <script>
    function openTab(evt, country) {{
    document.querySelectorAll('.country').forEach(sec => sec.style.display='none');
    document.querySelectorAll('.pill').forEach(p=>p.classList.remove('pill--active'));
    document.getElementById(country).style.display='block';
    evt.currentTarget.classList.add('pill--active');
    }}
    function filterCards(country) {{
    const typeVal = document.getElementById('type-'+country).value;
    const q = document.getElementById('search-'+country).value.toLowerCase().trim();
    document.querySelectorAll('#grid-'+country+' .card').forEach(card => {{
        const ctype = card.getAttribute('data-type')||'';
        const text = card.innerText.toLowerCase();
        const byType = (typeVal==='ALL')||(ctype===typeVal);
        const byText = q===''||text.indexOf(q)!==-1;
        card.style.display=(byType&&byText)?'':'none';
    }});
    }}
    </script>
    </body>
    </html>
            """

