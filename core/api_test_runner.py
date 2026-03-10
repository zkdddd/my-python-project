import pandas as pd
import requests
import json
import os
import time
from datetime import datetime
from core.utils import safe_json_loads, compare_json

class APITestRunner:
    def __init__(self):
        self.results = []

    def run_single(self, case):
        """
        执行单个测试用例
        case: 字典，包含 id, name, method, url, headers, body, expected_status, expected_body
        返回结果字典
        """
        start_time = datetime.now().isoformat(sep=' ', timespec='seconds')
        start_ts = time.time()
        result = {
            'case_id': case['id'],
            'case_name': case['name'],
            'status': 'FAIL',
            'response_status': None,
            'response_body': None,
            'error_message': '',
            'start_time': start_time,
            'end_time': None,
            'duration': None
        }
        try:
            # 解析 headers 和 body
            headers = safe_json_loads(case['headers']) or {}
            body = safe_json_loads(case['body'])
            # 发送请求
            response = requests.request(
                method=case['method'],
                url=case['url'],
                headers=headers,
                json=body,
                timeout=10
            )
            result['response_status'] = response.status_code
            result['response_body'] = response.text

            # 断言状态码
            status_ok = (response.status_code == case['expected_status'])

            # 断言响应体（如果期望体非空，则尝试 JSON 比较）
            body_ok = True
            if case['expected_body'] and case['expected_body'].strip():
                expected_json = safe_json_loads(case['expected_body'])
                actual_json = safe_json_loads(response.text)
                diff = compare_json(actual_json, expected_json)
                if diff:
                    body_ok = False
                    result['error_message'] = f"响应体差异: {diff}"
                else:
                    result['error_message'] = ''  # 清空之前的错误
            else:
                # 如果没有期望体，则认为通过
                pass

            if status_ok and body_ok:
                result['status'] = 'PASS'
            elif not status_ok:
                result['error_message'] = f"状态码期望 {case['expected_status']} 实际 {response.status_code}"

        except Exception as e:
            result['error_message'] = str(e)

        end_time = datetime.now().isoformat(sep=' ', timespec='seconds')
        result['end_time'] = end_time
        result['duration'] = round(time.time() - start_ts, 3)
        self.results.append(result)
        return result

    def run_batch(self, cases):
        """批量执行用例"""
        self.results = []
        for case in cases:
            self.run_single(case)
        return self.results

    def run_data_driven(self, template_case, data_rows, field_mapping):
        """
        数据驱动执行
        :param template_case: 原始用例模板（字典）
        :param data_rows: 数据行列表，每行是一个字典（列名->值）
        :param field_mapping: 字段映射，例如 {"username":"user", "password":"pwd"}
                              表示将模板中的 ${username} 替换为 data['user']
        :return: 包含所有子结果的主结果字典
        """
        sub_results = []
        overall_pass = True

        for row in data_rows:
            # 深拷贝模板，避免修改原数据
            case_copy = template_case.copy()
            # 替换请求体中的变量
            if case_copy.get('body'):
                body = case_copy['body']
                for var_name, col_name in field_mapping.items():
                    placeholder = f'${{{var_name}}}'
                    if placeholder in body:
                        # 从当前行数据中获取对应列的值，转为字符串
                        val = str(row.get(col_name, ''))
                        body = body.replace(placeholder, val)
                case_copy['body'] = body

            # 如果需要，也可以替换 URL 或 Headers 中的变量（类似逻辑）

            # 执行单个请求（复用 run_single 方法）
            sub_result = self.run_single(case_copy)
            # 标记该子结果对应的数据行（可选，用于报告）
            sub_result['data_row'] = row
            sub_results.append(sub_result)

            if sub_result['status'] != 'PASS':
                overall_pass = False

        # 构造主用例结果
        main_result = {
            'case_id': template_case['id'],
            'case_name': template_case['name'] + ' [数据驱动]',
            'status': 'PASS' if overall_pass else 'FAIL',
            'sub_results': sub_results,
            'start_time': sub_results[0]['start_time'] if sub_results else '',
            'end_time': sub_results[-1]['end_time'] if sub_results else '',
            'duration': sum(r['duration'] for r in sub_results)
        }
        return main_result