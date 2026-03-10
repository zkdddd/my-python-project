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
        df = pd.read_excel(file_path, encoding='utf-8')
    else:
        raise ValueError("不支持数据文件类型，请使用csv或excel")
    return df.to_dict('records')

def safe_json_loads(s):
    """安全地将字符串解析为 JSON，失败返回 None"""
    if not s:
        return None
    try:
        return json.loads(s)
    except:
        return None

def compare_json(actual, expected):
    """使用 DeepDiff 比较两个 JSON 对象，返回差异描述"""
    if actual is None and expected is None:
        return None
    if actual is None or expected is None:
        return "实际/期望值为空"
    diff = DeepDiff(expected, actual, ignore_order=True)
    if not diff:
        return None
    # 简化差异输出
    result = []
    for key, value in diff.items():
        result.append(f"{key}: {value}")
    return "; ".join(result)

def generate_html_report(run_data, cases_results, run_id):
    """生成单个运行批次的 HTML 报告（这里简化为只显示本次运行结果）"""
    # 可复用之前游戏测试框架的报告生成逻辑，但需要调整数据源
    # 这里给出一个简化版本
    from config import REPORT_DIR
    filename = f"report_{run_id}_{int(time.time())}.html"
    filepath = os.path.join(REPORT_DIR, filename)

    total = len(cases_results)
    passed = sum(1 for r in cases_results if r['status'] == 'PASS')
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0
    html = ""
    for r in cases_results:
        if 'sub_results' in r:
            # 主行
            html += f"<tr class='data-driven' onclick='toggleSubRows(this)'>"
            html += f"<td>{r['case_name']}</td><td>{r['status']}</td>..."
            html += "</tr>"
            # 子行（初始隐藏）
            for sub in r['sub_results']:
                html += f"<tr class='sub-result' style='display:none'>"
                html += f"<td>↳ {sub.get('data_row', '')}</td><td>{sub['status']}</td>..."
                html += "</tr>"
        else:
            # 普通行
            html += f"<tr>..."
    html = f"""<!DOCTYPE html>
    
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告 #{run_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 8px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .detail {{ background: #eee; padding: 10px; display: none; }}
    </style>
</head>
<body>
    <h1>接口自动化测试报告 #{run_id}</h1>
    <div class="summary">
        <p>运行时间: {run_data['start_time']} 至 {run_data['end_time']}</p>
        <p>总计: {total} | 通过: <span class="pass">{passed}</span> | 失败: <span class="fail">{failed}</span> | 通过率: {pass_rate:.1f}%</p>
    </div>
    <table>
        <thead>
            <tr><th>用例名称</th><th>状态</th><th>响应码</th><th>耗时(秒)</th><th>详情</th></tr>
        </thead>
        <tbody>
"""
    for r in cases_results:
        status_class = 'pass' if r['status']=='PASS' else 'fail'
        html += f"""
            <tr>
                <td>{r['case_name']}</td>
                <td class="{status_class}">{r['status']}</td>
                <td>{r['response_status']}</td>
                <td>{r['duration']}</td>
                <td><button onclick="toggle('detail_{r['case_id']}')">查看</button></td>
            </tr>
            <tr id="detail_{r['case_id']}" class="detail">
                <td colspan="5">
                    <pre>错误信息: {r['error_message']}</pre>
                    <pre>响应体: {r['response_body']}</pre>
                </td>
            </tr>
"""
    html += """
        </tbody>
    </table>
    <script>
        function toggle(id) {
            var el = document.getElementById(id);
            if (el.style.display === 'none' || el.style.display === '') {
                el.style.display = 'table-row';
            } else {
                el.style.display = 'none';
            }
        }
        # 添加
        function toggleSubRows(mainRow) {
    var nextRows = [];
    var sibling = mainRow.nextElementSibling;
    while (sibling && sibling.classList.contains('sub-result')) {
        nextRows.push(sibling);
        sibling = sibling.nextElementSibling;
    }
    for (var row of nextRows) {
        row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
    }
}
    </script>
</body>
</html>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    return filename