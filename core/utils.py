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
        .assertions-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .assertions-table th, .assertions-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #eee; }}
        .assertions-table th {{ background: #f2f2f2; }}
        .assertion-pass {{ color: green; font-weight: bold; }}
        .assertion-fail {{ color: red; font-weight: bold; }}
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
    for idx, r in enumerate(cases_results):
        status_class = 'pass' if r['status']=='PASS' else 'fail'
        html += f"""
            <tr>
                <td>{r['case_name']}</td>
                <td class="{status_class}">{r['status']}</td>
                <td>{r['response_status']}</td>
                <td>{r['duration']}</td>
                <td><button onclick="toggle('detail_{idx}')">查看</button></td>
            </tr>
            <tr id="detail_{idx}" class="detail">
                <td colspan="5">
"""
        # Add assertions details if available
        if 'assertions' in r and r['assertions']:
            html += f"""
                    <div class="assertions-detail">
                        <h4>断言结果</h4>
                        <table class="assertions-table">
                            <thead>
                                <tr>
                                    <th>类型</th>
                                    <th>目标</th>
                                    <th>条件</th>
                                    <th>期望值</th>
                                    <th>实际值</th>
                                    <th>通过状态</th>
                                </tr>
                            </thead>
                            <tbody>
"""
            for ar in r['assertions']:
                assertion = ar['assertion']
                passed_class = 'assertion-pass' if ar['passed'] else 'assertion-fail'
                passed_text = '通过' if ar['passed'] else '失败'
                # Format actual value for display
                actual_value = ar['actual_value']
                if actual_value is None:
                    actual_value_display = 'null'
                elif isinstance(actual_value, (dict, list)):
                    actual_value_display = json.dumps(actual_value, ensure_ascii=False)
                else:
                    actual_value_display = str(actual_value)
                html += f"""
                                <tr>
                                    <td>{assertion.get('type', '')}</td>
                                    <td>{assertion.get('target', '')}</td>
                                    <td>{assertion.get('condition', '')}</td>
                                    <td>{assertion.get('expected_value', '')}</td>
                                    <td>{actual_value_display}</td>
                                    <td class="{passed_class}">{passed_text}</td>
                                </tr>
"""
            html += """
                            </tbody>
                        </table>
                    </div>
"""
        # Keep the original error message and response body for backward compatibility
        error_msg = r.get('error_message', '')
        response_body = r.get('response_body', '')
        if error_msg or response_body:
            html += f"""
                    <div class="original-error">
                        <h4>原始错误信息和响应体</h4>
                        <pre>错误信息: {error_msg}</pre>
                        <pre>响应体: {response_body}</pre>
                    </div>
"""
        html += f"""
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