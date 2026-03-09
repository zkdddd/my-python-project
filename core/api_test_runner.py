import requests
import json
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