"""Build a self-contained data snapshot for GitHub Pages (Plotly loaded from CDN)."""
import html
import json
from pathlib import Path

import pandas as pd

from analysis import MIN_PROJECTS, aggregate, forecast, prepare

ROOT = Path(__file__).parent


def build(source: Path = ROOT / "data/ieg_ratings.csv", target: Path = ROOT / "docs/index.html") -> dict:
    data, quality = prepare(pd.read_csv(source))
    views = {}
    for dimension, field in (("Region", "wb_region"), ("Global practice", "global_practice")):
        groups = {}
        for label, subset in data.groupby(field):
            annual = aggregate(subset, field)
            observed = annual.loc[annual.projects >= MIN_PROJECTS]
            if observed.empty:
                continue
            projection, scores = forecast(annual)
            groups[label] = {
                "observed": observed[["final_closing_fy", "projects", "satisfactory", "rate"]].to_dict("records"),
                "projection": projection.to_dict("records"),
                "scores": scores.to_dict("records"),
            }
        views[dimension] = groups
    if not any(views.values()):
        raise ValueError("No eligible groups; refusing to write an empty dashboard")
    payload = json.dumps({"quality": quality, "views": views}, ensure_ascii=False).replace("</", "<\\/")
    document = TEMPLATE.replace("__PAYLOAD__", payload).replace("__SNAPSHOT__", html.escape(quality["snapshot_date"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return quality


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>World Bank project outcomes | Exploratory dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#17283b;background:#f5f8fb}
*{box-sizing:border-box} body{margin:0}header{background:#102c45;color:white;padding:25px max(calc((100vw - 1100px)/2),24px)}
header h1{margin:0;font-size:2rem}header p{margin:8px 0 0;color:#d5e2ef;max-width:780px}
main{max-width:1100px;margin:auto;padding:24px} .eyebrow{color:#75cce4;text-transform:uppercase;font-size:.77rem;letter-spacing:.12em;font-weight:700}
.controls,.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-bottom:20px}
.cards{grid-template-columns:repeat(3,minmax(0,1fr))} .card,section{background:white;border:1px solid #dbe5ec;border-radius:12px;padding:20px;box-shadow:0 2px 10px #183b5c09}
label{display:block;font-size:.8rem;font-weight:700;color:#36546b;margin-bottom:7px}select{width:100%;padding:10px;border:1px solid #bbccd9;border-radius:7px;background:white;font:inherit}
.card span{display:block;color:#526c7f;font-size:.83rem}.card strong{display:block;font-size:1.65rem;margin:8px 0 1px}.card small{color:#526c7f}
.grid{display:grid;grid-template-columns:1.6fr 1fr;gap:16px;margin-top:16px}h2{font-size:1.1rem;margin:0 0 16px}p{line-height:1.55}
table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{padding:9px 6px;text-align:left;border-bottom:1px solid #e7edf2}th{color:#526c7f} td:last-child,th:last-child{text-align:right}
.scroll{overflow:auto;max-height:440px}#chart{height:440px}.note{font-size:.85rem;color:#536d80}footer{max-width:1100px;margin:0 auto 30px;padding:0 24px;color:#526c7f;font-size:.85rem}
a{color:#126998}@media(max-width:720px){.cards,.controls,.grid{grid-template-columns:1fr}header h1{font-size:1.55rem}}
</style></head><body>
<header><div class="eyebrow">Portfolio evidence · IEG ratings</div><h1>World Bank project outcomes</h1>
<p>Evaluated projects rated moderately satisfactory or above, grouped by final closing fiscal year. Source snapshot: __SNAPSHOT__.</p></header>
<main><div class="controls"><div><label for="dimension">Compare by</label><select id="dimension"><option>Region</option><option>Global practice</option></select></div>
<div><label for="group">Select group</label><select id="group"></select></div></div>
<div class="cards"><div class="card"><span>Latest eligible cohort</span><strong id="year">—</strong><small>At least ten evaluated projects</small></div>
<div class="card"><span>Rated MS or above</span><strong id="rate">—</strong><small id="change"></small></div>
<div class="card"><span>Evaluated projects</span><strong id="count">—</strong><small>Equal project weight</small></div></div>
<section><h2>Historical trend and exploratory projection</h2><div id="chart" role="img" aria-label="Project outcome trend chart"></div>
<p class="note" id="forecastNote"></p></section>
<div class="grid"><section><h2>Comparison in selected closing year</h2><div class="scroll"><table><thead><tr><th id="groupHeading">Region</th><th>Projects</th><th>MS+ share</th></tr></thead><tbody id="comparison"></tbody></table></div></section>
<section><h2>Forecast check</h2><div id="scores"></div><p class="note">The ±backtest MAE band is an illustrative scenario, not a calibrated confidence interval.</p></section></div>
<section style="margin-top:16px"><h2>Interpret with care</h2><p id="quality"></p><p>IEG's development outcome rating combines relevance, efficacy, and efficiency. The MS+ share is the count rated Moderately Satisfactory, Satisfactory, or Highly Satisfactory divided by projects with recognized ratings. This is an <strong>evaluation rating</strong>, not an individual results-framework indicator, beneficiary count, or measure of attributable impact.</p>
<p>Recent cohorts may be incomplete because projects are evaluated after closing. Each project has equal weight; differences in project mix, classification changes, and missing ratings limit comparisons. Region and global practice reflect source classifications at the snapshot date. Extrapolations cannot predict an individual project's results or establish causal effects.</p>
<p><a href="https://financesone.worldbank.org/ieg-world-bank-project-performance-ratings/DS00053">Official IEG source</a> · <a href="https://github.com/LuguReign/world-bank-outcomes">Methods and reproducible code</a></p></section></main>
<footer>Independent portfolio analysis · World Bank Group data (CC BY 4.0). Not an official World Bank dashboard.</footer>
<script type="application/json" id="data">__PAYLOAD__</script>
<script>
const dataset=JSON.parse(document.getElementById('data').textContent);
const dim=document.getElementById('dimension'), group=document.getElementById('group');
const pct=x=>(x*100).toFixed(1)+'%'; const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function groups(){let list=Object.keys(dataset.views[dim.value]).sort((a,b)=>a.localeCompare(b));group.innerHTML=list.map(x=>'<option>'+esc(x)+'</option>').join('');if(dim.value==='Region'&&list.includes('Western and Central Africa'))group.value='Western and Central Africa';render()}
function render(){const item=dataset.views[dim.value][group.value];if(!item)return;
const rows=item.observed,latest=rows.at(-1),prev=rows.at(-2),f=item.projection;
document.getElementById('year').textContent='FY'+latest.final_closing_fy;
document.getElementById('rate').textContent=pct(latest.rate);
document.getElementById('change').textContent=prev?((latest.rate-prev.rate)>=0?'+':'')+((latest.rate-prev.rate)*100).toFixed(1)+' pp vs prior eligible cohort':'No earlier eligible cohort';
document.getElementById('count').textContent=latest.projects.toLocaleString();
let traces=[{x:rows.map(x=>x.final_closing_fy),y:rows.map(x=>x.rate),customdata:rows.map(x=>x.projects),type:'scatter',mode:'lines+markers',name:'Evaluated cohorts',line:{color:'#126998',width:3},hovertemplate:'FY%{x}<br>MS+ %{y:.1%}<br>Projects %{customdata}<extra></extra>'}];
if(f.length){traces.push({x:f.map(x=>x.final_closing_fy),y:f.map(x=>x.projected_rate),type:'scatter',mode:'lines+markers',name:'Exploratory projection',line:{color:'#de8543',dash:'dash',width:3},hovertemplate:'FY%{x}<br>Projected %{y:.1%}<extra></extra>'});
traces.push({x:f.map(x=>x.final_closing_fy).concat(f.map(x=>x.final_closing_fy).reverse()),y:f.map(x=>x.upper_scenario).concat(f.map(x=>x.lower_scenario).reverse()),type:'scatter',fill:'toself',fillcolor:'rgba(222,133,67,.15)',line:{color:'transparent'},name:'± backtest MAE',hoverinfo:'skip'});}
Plotly.newPlot('chart',traces,{margin:{l:60,r:16,t:12,b:55},paper_bgcolor:'white',plot_bgcolor:'white',yaxis:{title:'MS+ share',tickformat:'.0%',range:[0,1],gridcolor:'#e7edf2'},xaxis:{title:'Final closing FY',dtick:2},legend:{orientation:'h',y:-.28}}, {responsive:true,displayModeBar:false});
document.getElementById('forecastNote').textContent=f.length?`Selected ${f[0].method}; ${f[0].backtest_years} consecutive one-year backtests, MAE ${pct(f[0].backtest_mae)}. Three later closing cohorts shown as scenarios.`:'Forecast withheld: fewer than eight eligible cohorts or fewer than three consecutive one-year backtests.';
const comparison=Object.entries(dataset.views[dim.value]).map(([name,v])=>({name,row:v.observed.find(x=>x.final_closing_fy===latest.final_closing_fy)})).filter(x=>x.row).sort((a,b)=>b.row.rate-a.row.rate);
document.getElementById('groupHeading').textContent=dim.value;
document.getElementById('comparison').innerHTML=comparison.map(x=>`<tr><td>${esc(x.name)}</td><td>${x.row.projects.toLocaleString()}</td><td>${pct(x.row.rate)}</td></tr>`).join('');
document.getElementById('scores').innerHTML=item.scores.length?`<p>Selected method: <strong>${esc(f[0].method)}</strong></p><table><tr><th>Candidate</th><th>MAE</th></tr>${item.scores.map(x=>`<tr><td>${esc(x.method)}</td><td>${pct(x.mae)}</td></tr>`).join('')}</table>`:'<p>Insufficient consecutive cohorts for a defensible backtest.</p>';
}
const q=dataset.quality;document.getElementById('quality').textContent=`Snapshot ${q.snapshot_date}: ${q.source_rows.toLocaleString()} source rows, ${q.unique_projects.toLocaleString()} unique project IDs, ${q.included_projects.toLocaleString()} included rated projects. Closing cohorts after FY${q.cohort_cutoff} excluded to reduce evaluation lag. Cohorts with fewer than ten projects are hidden.`;
dim.addEventListener('change',groups);group.addEventListener('change',render);groups();
</script></body></html>'''


if __name__ == "__main__":
    print(build())
