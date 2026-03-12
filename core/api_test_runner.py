import pandas as pd
import requests
import json
import os
import time
import re
from datetime import datetime
from core.utils import safe_json_loads, compare_json
from models import get_assertions_by_case

# Try to import jsonpath_ng, set flag if available
JSONPATH_AVAILABLE = False
parse_func = None
ext_parse_func = None
try:
    from jsonpath_ng import parse as parse_func
    from jsonpath_ng.ext import parse as ext_parse_func
    JSONPATH_AVAILABLE = True
except ImportError:
    pass

class APITestRunner:
    def __init__(self):
        self.results = []
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def _extract_value(self, response, assertion):
        """根据断言类型提取实际值"""
        assertion_type = assertion['type']
        target = assertion.get('target', '')
        
        if assertion_type == 'status_code':
            return response.status_code
        elif assertion_type == 'response_time':
            return response.elapsed.total_seconds() * 1000  # 转换为毫秒
        elif assertion_type == 'header':
            return response.headers.get(target, '')
        elif assertion_type == 'json_path':
            if not JSONPATH_AVAILABLE:
                return None
            try:
                # 尝试使用扩展语法（支持过滤器等）
                jsonpath_expr = ext_parse_func(target)
            except:
                # 如果失败，尝试基本语法
                try:
                    jsonpath_expr = parse_func(target)
                except:
                    return None
            matches = jsonpath_expr.find(response.json())
            if matches:
                # 返回第一个匹配的值
                return matches[0].value
            else:
                return None
        elif assertion_type == 'regex':
            return response.text
        else:
            return None

    def _compare_values(self, actual, condition, expected):
        """根据条件比较实际值和期望值"""
        # 处理特殊条件
        if condition in ['exists', 'not_exists']:
            exists = actual is not None and (not isinstance(actual, str) or actual != '')
            return exists if condition == 'exists' else not exists
        
        if condition == 'type':
            if actual is None:
                actual_type = 'null'
            elif isinstance(actual, str):
                actual_type = 'string'
            elif isinstance(actual, bool):
                actual_type = 'boolean'
            elif isinstance(actual, (int, float)):
                actual_type = 'number'
            elif isinstance(actual, list):
                actual_type = 'array'
            elif isinstance(actual, dict):
                actual_type = 'object'
            else:
                actual_type = type(actual).__name__
            return actual_type == expected.lower()
        
        # 处理空期望值的情况
        if expected is None or expected == '':
            if condition in ['equals', 'not_equals']:
                return actual == expected if condition == 'equals' else actual != expected
            elif condition in ['contains', 'not_contains']:
                if isinstance(actual, str):
                    return (expected in actual) if condition == 'contains' else (expected not in actual)
                else:
                    return False
            return False
        
        # 尝试将值转换为适当的类型进行比较
        try:
            # 尝试数值比较
            if isinstance(actual, (int, float)) or (isinstance(actual, str) and actual.replace('.', '', 1).isdigit()):
                actual_num = float(actual) if isinstance(actual, str) else actual
                expected_num = float(expected)
                if condition == 'equals':
                    return actual_num == expected_num
                elif condition == 'not_equals':
                    return actual_num != expected_num
                elif condition == 'gt':
                    return actual_num > expected_num
                elif condition == 'lt':
                    return actual_num < expected_num
                elif condition == 'ge':
                    return actual_num >= expected_num
                elif condition == 'le':
                    return actual_num <= expected_num
        except (ValueError, TypeError):
            pass
        
        # 字符串比较
        actual_str = str(actual) if actual is not None else ''
        expected_str = str(expected)
        
        if condition == 'equals':
            return actual_str == expected_str
        elif condition == 'not_equals':
            return actual_str != expected_str
        elif condition == 'contains':
            return expected_str in actual_str
        elif condition == 'not_contains':
            return expected_str not in actual_str
        elif condition == 'gt':
            return actual_str > expected_str
        elif condition == 'lt':
            return actual_str < expected_str
        elif condition == 'ge':
            return actual_str >= expected_str
        elif condition == 'le':
            return actual_str <= expected_str
        else:
            return False

    def _evaluate_assertions(self, response, assertions):
        """评估所有断言并返回结果"""
        assertion_results = []
        overall_pass = True
        
        for assertion in assertions:
            if not assertion.get('enabled', True):
                assertion_results.append({
                    'assertion': assertion,
                    'passed': True,  # 跳过的断言视为通过
                    'actual_value': 'SKIPPED',
                    'error_message': '断言已禁用'
                })
                continue
            
            try:
                actual_value = self._extract_value(response, assertion)
                passed = self._compare_values(actual_value, assertion['condition'], assertion.get('expected_value'))
                
                if not passed:
                    overall_pass = False
                
                assertion_results.append({
                    'assertion': assertion,
                    'passed': passed,
                    'actual_value': actual_value,
                    'error_message': '' if passed else f"断言失败: 期望 {assertion['condition']} {assertion.get('expected_value', '')}, 实际 {actual_value}"
                })
            except Exception as e:
                overall_pass = False
                assertion_results.append({
                    'assertion': assertion,
                    'passed': False,
                    'actual_value': 'ERROR',
                    'error_message': f"断言执行错误: {str(e)}"
                })
        
        return overall_pass, assertion_results

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
            'duration': None,
            'assertions': []  # 新增断言结果字段
        }
        try:
            # 解析 headers 和 body
            headers = safe_json_loads(case['headers']) or {}
            # 合并默认headers
            headers = {**self.default_headers, **headers}
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

            # 获取断言配置
            assertions = get_assertions_by_case(case['id'])
            # 如果没有配置断言，则使用旧的 expected_status 和 expected_body 作为默认断言
            if not assertions:
                # 构造默认断言：状态码断言和响应体完全匹配断言
                assertions = []
                if case['expected_status'] is not None:
                    assertions.append({
                        'type': 'status_code',
                        'condition': 'equals',
                        'expected_value': str(case['expected_status']),
                        'enabled': True,
                        'sort_order': 0
                    })
                if case['expected_body'] and case['expected_body'].strip():
                    # 这里我们使用 json_path 的 $ 来匹配整个 JSON 对象，但如果响应体不是 JSON，则使用字符串比较
                    # 为了简单，我们将其作为一个自定义断言类型：response_bodyEquals
                    # 然而，为了复用现有框架，我们可以使用 json_path 的 $ 和 condition equals，但前提是响应体是有效的 JSON
                    # 如果响应体不是 JSON，则断言会失败。这是一个已知限制。
                    # 为了向后兼容，我们仍然添加这个断言，但如果响应体不是 JSON，则会失败。
                    assertions.append({
                        'type': 'json_path',
                        'target': '$',
                        'condition': 'equals',
                        'expected_value': case['expected_body'],
                        'enabled': True,
                        'sort_order': 1
                    })
            
            # 评估断言
            overall_pass, assertion_results = self._evaluate_assertions(response, assertions)
            result['assertions'] = assertion_results
            result['status'] = 'PASS' if overall_pass else 'FAIL'
            # 如果有断言失败，我们可以将第一个失败的断言的错误消息设置为 error_message（保持向后兼容）
            if not overall_pass:
                for ar in assertion_results:
                    if not ar['passed'] and ar['error_message']:
                        result['error_message'] = ar['error_message']
                        break

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