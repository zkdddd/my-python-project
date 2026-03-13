import json
import os
import time

import pandas as pd
from deepdiff import DeepDiff

def load_data_from_source(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path, encoding='utf-8')
    elif file_path.endswith(('.xlsx','xls')):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("不支持数据文件类型，请使用csv或excel")
    return df.to_dict('records')

def safe_json_loads(s):
    if not s:
        return None
    try:
        return json.loads(s)
    except:
        return None

def compare_json(actual, expected):
    if actual is None and expected is None:
        return None
    if actual is None or expected is None:
        return "实际/期望值为空"
    diff = DeepDiff(expected, actual, ignore_order=True)
    if not diff:
        return None
    result = []
    for key, value in diff.items():
        result.append(f"{key}: {value}")
    return "; ".join(result)

def generate_html_report(run_data, cases_results, run_id):
    from config import REPORT_DIR
    
    filename = f"report_{run_id}_{int(time.time())}.html"
    filepath = os.path.join(REPORT_DIR, filename)

    total = len(cases_results)
    passed = sum(1 for r in cases_results if r['status'] == 'PASS')
    failed = total - passed
    total_duration = sum(r.get('duration', 0) or 0 for r in cases_results)
    
    cases_json = json.dumps(cases_results, ensure_ascii=False, default=str)

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 #REPLACE_RUN_ID</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        :root { --p:#6366f1; --s:#10b981; --d:#ef4444; --w:#f59e0b; --grad:linear-gradient(135deg,#667eea,#764ba2); }
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--grad);min-height:100vh;padding:0 0 50px;color:#1e293b}
        .glass{background:rgba(255,255,255,0.88);backdrop-filter:blur(20px)}
        .navbar{padding:1rem 2rem;box-shadow:0 2px 8px rgba(0,0,0,0.08)}
        .navbar h1{font-size:1.35rem;font-weight:700;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
        .container{max-width:1400px;margin:0 auto;padding:2rem}
        .card{background:rgba(255,255,255,0.88);backdrop-filter:blur(20px);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 8px 32px rgba(0,0,0,0.1)}
        .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem}
        .stat-card{background:rgba(255,255,255,0.9);border-radius:12px;padding:1.1rem;display:flex;align-items:center;gap:0.85rem;transition:all 0.3s}
        .stat-card:hover{transform:translateY(-3px);box-shadow:0 10px 20px rgba(0,0,0,0.12)}
        .stat-icon{width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem}
        .stat-icon.t{background:linear-gradient(135deg,#e0e7ff,#c7d2fe);color:var(--p)}
        .stat-icon.p{background:linear-gradient(135deg,#d1fae5,#a7f3d0);color:var(--s)}
        .stat-icon.f{background:linear-gradient(135deg,#fee2e2,#fecaca);color:var(--d)}
        .stat-icon.d{background:linear-gradient(135deg,#fef3c7,#fde68a);color:var(--w)}
        .stat-value{font-size:1.4rem;font-weight:700}.stat-label{font-size:.75rem;color:#64748b}
        .charts-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1.5rem}
        .chart-wrap{background:rgba(255,255,255,0.75);border-radius:12px;padding:1.25rem}
        .chart-wrap h5{font-size:.9rem;font-weight:600;margin-bottom:0.85rem;color:#334155}
        .filter-bar{display:flex;gap:0.85rem;align-items:center;flex-wrap:wrap;padding:1rem 1.25rem;background:rgba(255,255,255,0.75);border-radius:12px;margin-bottom:1rem}
        .search-box{flex:1;min-width:180px;position:relative}
        .search-box input{width:100%;padding:.55rem .9rem .55rem 2.3rem;border:2px solid rgba(99,102,241,0.2);border-radius:8px;font-size:.85rem;transition:all 0.3s}
        .search-box input:focus{border-color:var(--p);outline:none;box-shadow:0 0 0 3px rgba(99,102,241,0.1)}
        .search-box i{position:absolute;left:.7rem;top:50%;transform:translateY(-50%);color:#94a3b8}
        .filter-btn{padding:.45rem .9rem;border:1px solid rgba(99,102,241,0.25);border-radius:8px;background:rgba(255,255,255,0.9);cursor:pointer;font-weight:500;font-size:.85rem;transition:all 0.3s}
        .filter-btn:hover,.filter-btn.active{background:var(--p);color:#fff;border-color:var(--p)}
        .case-list{list-style:none;padding:0;margin:0}
        .case-item{border-bottom:1px solid rgba(0,0,0,0.04)}
        .case-item:hover{background:rgba(99,102,241,0.03)}
        .case-header{padding:.9rem 1.1rem;display:flex;align-items:center;gap:0.9rem;cursor:pointer;transition:all 0.3s}
        .case-header:hover{background:rgba(99,102,241,0.04)}
        .case-status{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem}
        .case-status.p{background:#d1fae5;color:var(--s)}.case-status.f{background:#fee2e2;color:var(--d)}
        .case-info{flex:1;min-width:0}
        .case-name{font-weight:600;font-size:.88rem}
        .case-meta{font-size:.78rem;color:#64748b;display:flex;gap:0.9rem;margin-top:.12rem}
        .case-duration{font-size:.82rem;color:#94a3b8;white-space:nowrap}
        .btn-icon{width:30px;height:30px;border:none;border-radius:7px;background:#f1f5f9;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.3s}
        .btn-icon:hover{background:var(--p);color:#fff}
        .case-detail{display:none;background:rgba(248,250,252,0.85);border-top:1px solid rgba(0,0,0,0.04)}
        .case-detail.show{display:block}
        .detail-content{padding:1.1rem}
        .detail-section{margin-bottom:1.1rem}
        .detail-section h6{font-size:.82rem;font-weight:600;margin-bottom:.55rem;color:#334155}
        .detail-row{display:flex;margin-bottom:.35rem;font-size:.82rem}
        .detail-label{width:85px;flex-shrink:0;color:#64748b;font-weight:500}
        .detail-value{flex:1;word-break:break-all;background:#fff;padding:.45rem;border-radius:6px;border:1px solid #e2e8f0;max-height:160px;overflow:auto}
        .detail-value pre{margin:0;white-space:pre-wrap}
        .assertions-table{width:100%;border-collapse:collapse;font-size:.78rem}
        .assertions-table th{background:#fff;padding:.55rem;text-align:left;font-weight:600;border-bottom:2px solid #e2e8f0}
        .assertions-table td{padding:.55rem;border-bottom:1px solid #f1f5f9}
        .assertion-pass{color:var(--s);font-weight:600}.assertion-fail{color:var(--d);font-weight:600}
        .assertion-badge{display:inline-block;padding:.12rem .45rem;border-radius:4px;font-size:.68rem;margin-right:.15rem}
        .assertion-badge.status_code{background:#e0e7ff;color:#4f46e5}
        .assertion-badge.json_path{background:#d1fae5;color:#059669}
        .text-danger{color:var(--d)}.text-info{color:#3b82f6}
        footer{background:rgba(255,255,255,0.9);padding:.9rem;text-align:center;color:#64748b;font-size:.82rem}
        @media(max-width:768px){.charts-grid{grid-template-columns:1fr}.stats-grid{grid-template-columns:repeat(2,1fr)}}
        @keyframes fadeInUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        .card{animation:fadeInUp 0.5s ease-out}
    </style>
</head>
<body>
    <nav class="glass navbar"><div style="display:flex;justify-content:space-between;align-items:center;width:100%"><h1><i class="fas fa-vial"></i> 测试报告</h1><span style="background:rgba(255,255,255,0.35);padding:.2rem .7rem;border-radius:20px;font-size:.82rem">REPLACE_TIME</span></div></nav>
    <div class="container">
        <div class="card">
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-icon t"><i class="fas fa-list"></i></div><div class="stat-info"><div class="stat-value">REPLACE_TOTAL</div><div class="stat-label">总用例</div></div></div>
                <div class="stat-card"><div class="stat-icon p"><i class="fas fa-check-circle"></i></div><div class="stat-info"><div class="stat-value" style="color:var(--s)">REPLACE_PASSED</div><div class="stat-label">通过</div></div></div>
                <div class="stat-card"><div class="stat-icon f"><i class="fas fa-times-circle"></i></div><div class="stat-info"><div class="stat-value" style="color:var(--d)">REPLACE_FAILED</div><div class="stat-label">失败</div></div></div>
                <div class="stat-card"><div class="stat-icon d"><i class="fas fa-stopwatch"></i></div><div class="stat-info"><div class="stat-value">REPLACE_DURATION</div><div class="stat-label">总耗时</div></div></div>
            </div>
        </div>
        <div class="charts-grid">
            <div class="chart-wrap"><h5><i class="fas fa-chart-pie"></i> 通过率</h5><canvas id="passRateChart"></canvas></div>
            <div class="chart-wrap"><h5><i class="fas fa-chart-bar"></i> 耗时分布</h5><canvas id="durationChart"></canvas></div>
        </div>
        <div class="filter-bar">
            <div class="search-box"><i class="fas fa-search"></i><input type="text" id="searchInput" placeholder="搜索用例名称..."></div>
            <button class="filter-btn active" data-filter="all">全部</button><button class="filter-btn" data-filter="pass">通过</button><button class="filter-btn" data-filter="fail">失败</button>
            <span style="margin-left:auto;color:#64748b;font-size:.85rem">显示 <span id="filteredCount">REPLACE_COUNT</span> 条</span>
        </div>
        <div class="card" style="padding:0;overflow:hidden">
            <div style="padding:.95rem 1.1rem;border-bottom:1px solid rgba(0,0,0,0.04);font-weight:600"><i class="fas fa-list"></i> 测试结果</div>
            <ul class="case-list" id="caseList">REPLACE_CASE_LIST</ul>
        </div>
        <div style="text-align:center;margin-top:1.5rem"><a href="/" style="background:var(--p);color:#fff;padding:.55rem 1.4rem;border-radius:8px;text-decoration:none;font-weight:500;font-size:.9rem;display:inline-flex;align-items:center;gap:.5rem;transition:all 0.3s"><i class="fas fa-home"></i> 返回首页</a></div>
    </div>
    <footer>&copy; 2026 接口自动化测试平台</footer>
    <script>REPLACE_SCRIPT</script>
</body>
</html>'''
    
    time_range = run_data.get('start_time', '') + ' ~ ' + run_data.get('end_time', '')
    html = html.replace('REPLACE_RUN_ID', str(run_id))
    html = html.replace('REPLACE_TIME', time_range)
    html = html.replace('REPLACE_TOTAL', str(total))
    html = html.replace('REPLACE_PASSED', str(passed))
    html = html.replace('REPLACE_FAILED', str(failed))
    html = html.replace('REPLACE_DURATION', f"{total_duration:.2f}s")
    html = html.replace('REPLACE_COUNT', str(total))
    
    case_list_html = ''
    for idx, r in enumerate(cases_results):
        is_data_driven = 'sub_results' in r and r['sub_results']
        status_class = 'p' if r['status'] == 'PASS' else 'f'
        status_icon = '&#10003;' if r['status'] == 'PASS' else '&#10007;'
        duration_ms = int((r.get('duration') or 0) * 1000)
        assertions_failed = 0
        if 'assertions' in r:
            assertions_failed = sum(1 for a in r['assertions'] if not a.get('passed', True))
        
        error_msg = (r.get('error_message') or '').replace('`', '\\`').replace('\n', ' ')
        
        case_list_html += f'''<li class="case-item" data-status="{r['status']}" data-name="{r['case_name'].lower()}">
            <div class="case-header" onclick="toggleDetail({idx})">
                <div class="case-status {status_class}">{status_icon}</div>
                <div class="case-info">
                    <div class="case-name">{r['case_name']}{'<i class="fas fa-database text-info" style="margin-left:6px;"></i>' if is_data_driven else ''}</div>
                    <div class="case-meta"><span><i class="fas fa-code"></i> {r.get("response_status","N/A")}</span><span><i class="fas fa-clock"></i> {duration_ms}ms</span>{'<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> "+str(assertions_failed)+" 个失败</span>' if assertions_failed>0 else ''}</div>
                </div>
                <div class="case-duration">{duration_ms}ms</div>
            </div>
            <div class="case-detail" id="detail_{idx}">
                <div class="detail-content">
                    <div class="detail-section"><h6><i class="fas fa-exclamation-circle text-danger"></i> 错误信息</h6><div class="detail-value"><pre>{error_msg}</pre></div></div>
                    <div class="detail-section"><h6><i class="fas fa-code"></i> 请求信息</h6><div class="detail-row"><div class="detail-label">URL</div><div class="detail-value"><pre>{r.get("url","N/A")}</pre></div></div></div>
                    <div class="detail-section"><h6><i class="fas fa-response"></i> 响应信息</h6><div class="detail-row"><div class="detail-label">状态码</div><div class="detail-value"><pre>{r.get("response_status","N/A")}</pre></div></div><div class="detail-row"><div class="detail-label">响应体</div><div class="detail-value"><pre>{(r.get("response_body","") or "")[:1800]}</pre></div></div></div>'''
        
        if 'assertions' in r and r['assertions']:
            case_list_html += f'''<div class="detail-section"><h6><i class="fas fa-check-square"></i> 断言结果 <span class="assertion-badge header">{assertions_failed} 个失败</span></h6><table class="assertions-table"><thead><tr><th>类型</th><th>目标</th><th>条件</th><th>期望值</th><th>实际值</th><th>结果</th></tr></thead><tbody>'''
            for ar in r['assertions']:
                assertion = ar.get('assertion', {})
                passed_class = 'assertion-pass' if ar.get('passed', True) else 'assertion-fail'
                passed_text = '&#10003; 通过' if ar.get('passed', True) else '&#10007; 失败'
                actual_value = ar.get('actual_value')
                if actual_value is None: actual_value_display = 'null'
                elif isinstance(actual_value, (dict, list)): actual_value_display = str(actual_value)[:180]
                else: actual_value_display = str(actual_value)[:180]
                case_list_html += f'''<tr><td><span class="assertion-badge {assertion.get("type","")}">{assertion.get("type","")}</span></td><td><code>{assertion.get("target","")}</code></td><td>{assertion.get("condition","")}</td><td><code>{assertion.get("expected_value","")}</code></td><td><code>{actual_value_display}</code></td><td class="{passed_class}">{passed_text}</td></tr>'''
            case_list_html += '</tbody></table></div>'
        
        case_list_html += '</div></div></li>'
    
    html = html.replace('REPLACE_CASE_LIST', case_list_html)
    
    script = f'''const casesData = {cases_json};
document.addEventListener("DOMContentLoaded",function(){{
    new Chart(document.getElementById("passRateChart"),{{type:"doughnut",data:{{labels:["通过","失败"],datasets:[{{data:({passed},{failed}),backgroundColor:["#10b981","#ef4444"]}}]}},{{responsive:true,maintainAspectRatio:false}});
    const caseLabels=casesData.slice(0,10).map(c=>c.case_name.substring(0,15));
    const caseDurations=casesData.slice(0,10).map(c=>(c.duration||0)*1000);
    const caseColors=casesData.slice(0,10).map(c=>c.status==="PASS"?"#10b981":"#ef4444");
    new Chart(document.getElementById("durationChart"),{{type:"bar",data:{{labels:caseLabels,datasets:[{{label:"耗时(ms)",data:caseDurations,backgroundColor:caseColors,borderRadius:4}}]}},{{responsive:true,maintainAspectRatio:false}});
}});
function toggleDetail(idx){{var d=document.getElementById("detail_"+idx);d.classList.toggle("show");}}
var filterBtns=document.querySelectorAll(".filter-btn"),searchInput=document.getElementById("searchInput"),caseItems=document.querySelectorAll(".case-item"),filteredCountSpan=document.getElementById("filteredCount");
function applyFilters(){{var af=document.querySelector(".filter-btn.active").dataset.filter,st=searchInput.value.toLowerCase(),vc=0;caseItems.forEach(function(i){{var s=i.dataset.status,n=i.dataset.name,sm=af==="all"||(af==="pass"&&s==="PASS")||(af==="fail"&&s==="FAIL");if(sm&&n.includes(st)){{i.style.display="";vc++}}else{{i.style.display="none"}}}});filteredCountSpan.textContent=vc;}}
filterBtns.forEach(function(b){{b.addEventListener("click",function(){{filterBtns.forEach(function(x){{x.classList.remove("active")}});b.classList.add("active");applyFilters();}});}});
searchInput.addEventListener("input",applyFilters);'''
    
    html = html.replace('REPLACE_SCRIPT', script)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return filename
