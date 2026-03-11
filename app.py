import pandas as pd
from flask import Flask, request, render_template, jsonify, url_for, redirect
import json
import time
from datetime import datetime
from werkzeug.utils import secure_filename
from models import init_db, add_case, get_all_cases, get_case, update_case, delete_case, add_data_source, \
    get_all_data_sources
from models import add_test_run, get_test_runs, get_run_detail, get_run_statistics
from core.api_test_runner import APITestRunner
from core.utils import generate_html_report
from config import DEBUG
from config import UPLOAD_FOLDER
from core.utils import load_data_from_source  # 导入新函数
from models import get_data_source            # 确保已导入
import os

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 初始化数据库
init_db()

@app.route('/')
def index():
    cases = get_all_cases()
    return render_template('index.html', cases=cases)

@app.route('/case/new', methods=['GET', 'POST'])
def new_case():
    if request.method == 'POST':
        name = request.form['name']
        method = request.form['method']
        url = request.form['url']
        headers = request.form.get('headers', '')
        body = request.form.get('body', '')
        expected_status = int(request.form['expected_status'])
        expected_body = request.form.get('expected_body', '')
        description = request.form.get('description', '')
        data_source_id = request.form.get('data_source_id', None)
        data_mapping = request.form.get('data_mapping', '')
        add_case(name, method, url, headers, body, expected_status, expected_body, description,data_source_id,data_mapping)
        return redirect('/')
    data_sources = get_all_data_sources()
    return render_template('case_form.html', case=None,data_sources=data_sources)

@app.route('/case/<int:case_id>', methods=['GET', 'POST'])
def edit_case(case_id):
    case = get_case(case_id)
    if request.method == 'POST':
        name = request.form['name']
        method = request.form['method']
        url = request.form['url']
        headers = request.form.get('headers', '')
        body = request.form.get('body', '')
        expected_status = int(request.form['expected_status'])
        expected_body = request.form.get('expected_body', '')
        description = request.form.get('description', '')
        data_source_id = request.form.get('data_source_id', None)
        data_mapping = request.form.get('data_mapping', '')
        update_case(case_id, name, method, url, headers, body, expected_status, expected_body, description,data_source_id,data_mapping)
        return redirect('/')
    data_sources = get_all_data_sources()
    return render_template('case_form.html', case=case,data_sources = data_sources)

@app.route('/case/<int:case_id>/delete')
def delete_case_route(case_id):
    delete_case(case_id)
    return redirect('/')

@app.route('/run', methods=['POST'])
def run_test():
    # 获取要运行的用例ID列表（支持多选）
    case_ids = request.form.getlist('case_ids')
    if not case_ids:
        return jsonify({'error': '请选择至少一个用例'}), 400

    cases = [get_case(cid) for cid in case_ids]
    # 转换为字典列表（Row 对象需转 dict）
    case_dicts = []
    for c in cases:
        case_dicts.append({
            'id': c['id'],
            'name': c['name'],
            'method': c['method'],
            'url': c['url'],
            'headers': c['headers'],
            'body': c['body'],
            'expected_status': c['expected_status'],
            'expected_body': c['expected_body'],
            'data_source_id' : c['data_source_id'],#新增数据驱动
            'data_mapping': c['data_mapping']
        })

    runner = APITestRunner()
    results = runner.run_batch(case_dicts)


    for case in case_dicts:
        if case.get('data_source_id'):
            source = get_data_source(case['data_source_id'])
            if not source:
                continue
            file_path = source['file_path']
            try:
                data_rows = load_data_from_source(file_path)
            except Exception as e:
                results.append({
                    'case_id' :case['id'],
                    'case_name': case['name'],
                    'status': 'FAIL',
                    'error_message': f"数据源加载失败:{str(e)}"
                })
                continue

                # 解析字段映射（JSON字符串 -> 字典）
            mapping = json.loads(case['data_mapping'] or '{}')
            main_result = runner.run_data_driven(case, data_rows, mapping)
            results.append(main_result)
    else:
        # 普通执行
        result = runner.run_single(case)
        results.append(result)
    # 保存运行记录到数据库
    run_ids = []
    for r in results:
        run_id = add_test_run(
            case_id=r['case_id'],
            status=r['status'],
            response_status=r['response_status'],
            response_body=r['response_body'],
            error_message=r['error_message'],
            start_time=r['start_time'],
            end_time=r['end_time'],
            duration=r['duration'],
            report_path=''  # 稍后生成报告后再更新
        )
        r['run_id'] = run_id
        run_ids.append(run_id)

    # 生成本次运行的总体报告（假设一次批量运行生成一个报告）
    # 为简化，我们为每个运行单独生成报告，但也可以聚合。这里使用第一个 run_id 作为批次ID
    batch_id = run_ids[0] if run_ids else int(time.time())
    report_file = generate_html_report(
        run_data={'start_time': results[0]['start_time'], 'end_time': results[-1]['end_time']},
        cases_results=results,
        run_id=batch_id
    )
    # 可选：更新每条记录的 report_path
    report_url = url_for('static', filename=f'reports/{report_file}')
    return jsonify({'report_url': report_url})

@app.route('/history')
def history():
    runs = get_test_runs(100)
    stats = get_run_statistics(30)  # 最近30天趋势
    return render_template('history.html', runs=runs, stats=stats)

@app.route('/report/<int:run_id>')
def view_report(run_id):
    # 直接访问生成的静态报告文件
    # 需要知道 report_path，这里简单返回一个页面引导
    run = get_run_detail(run_id)
    if run and run['report_path']:
        report_url = url_for('static', filename='reports/' + run['report_path'])
        return redirect(report_url)
    return "报告不存在", 404

# 在 app.py 中添加上传路由
@app.route('/data_source/new', methods=['GET', 'POST'])
def upload_data_source():
    if request.method == 'POST':
        name = request.form['name']
        file = request.files['file']
        if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # 读取列名
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            columns = df.columns.tolist()

            # 存入数据库
            add_data_source(name, file_path, json.dumps(columns))
            return redirect('/data_sources')
    return render_template('upload_data.html')


@app.route('/data_sources')
def list_data_sources():
    sources = get_all_data_sources()
    return render_template('data_sources.html', sources=sources)
if __name__ == '__main__':
    app.run(debug=DEBUG)