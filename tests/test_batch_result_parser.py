"""
Unit tests for BatchResultParser
"""

import pytest
from pathlib import Path
import json

from src.processors.batch_result_parser import BatchResultParser


@pytest.fixture
def parser():
    """创建 BatchResultParser 实例"""
    return BatchResultParser()


@pytest.fixture
def sample_result_file(tmp_path):
    """创建示例结果文件"""
    file_path = tmp_path / "results.jsonl"
    
    # 成功的结果
    success_result = {
        "custom_id": "doi_10.1016_j.example.2024.001",
        "response": {
            "status_code": 200,
            "body": {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "title": "Test Paper Title",
                            "published_at": "2024-01-15",
                            "corresponding_author": {
                                "name": "John Doe",
                                "email": "john@example.com",
                                "phone": "+1-123-456-7890",
                                "institution": "Harvard University",
                                "address": "Cambridge, MA, USA"
                            }
                        }, ensure_ascii=False)
                    }
                }]
            }
        }
    }
    
    # 失败的结果
    failed_result = {
        "custom_id": "doi_10.1016_j.example.2024.002",
        "response": {
            "status_code": 500,
            "body": {
                "error": {
                    "message": "Internal server error"
                }
            }
        }
    }
    
    # JSON 解析错误的结果
    parse_error_result = {
        "custom_id": "doi_10.1016_j.example.2024.003",
        "response": {
            "status_code": 200,
            "body": {
                "choices": [{
                    "message": {
                        "content": "This is not valid JSON"
                    }
                }]
            }
        }
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(success_result, ensure_ascii=False) + '\n')
        f.write(json.dumps(failed_result, ensure_ascii=False) + '\n')
        f.write(json.dumps(parse_error_result, ensure_ascii=False) + '\n')
    
    return file_path


def test_parse_result_file(parser, sample_result_file):
    """测试解析结果文件"""
    results = parser.parse_result_file(sample_result_file)
    
    assert len(results) == 3
    
    # 验证第一个结果（成功）
    assert results[0]['status'] == 'success'
    assert results[0]['doi'] == '10.1016/j.example.2024.001'
    assert results[0]['data']['title'] == "Test Paper Title"
    assert results[0]['data']['corresponding_author']['name'] == "John Doe"
    
    # 验证第二个结果（失败）
    assert results[1]['status'] == 'failed'
    assert results[1]['doi'] == '10.1016/j.example.2024.002'
    
    # 验证第三个结果（解析错误）
    assert results[2]['status'] == 'parse_error'
    assert results[2]['doi'] == '10.1016/j.example.2024.003'


def test_parse_llm_response_valid_json(parser):
    """测试解析有效的 JSON 响应"""
    content = json.dumps({
        "title": "Test Title",
        "published_at": "2024-01-01",
        "corresponding_author": {
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
    })
    
    data = parser._parse_llm_response(content)
    
    assert data['title'] == "Test Title"
    assert data['published_at'] == "2024-01-01"
    assert data['corresponding_author']['name'] == "Jane Doe"


def test_parse_llm_response_json_in_text(parser):
    """测试从文本中提取 JSON"""
    content = """
    Here is the extracted information:
    
    {
        "title": "Test Title",
        "published_at": "2024-01-01",
        "corresponding_author": {
            "name": "Jane Doe",
            "email": "jane@example.com"
        }
    }
    
    That's all.
    """
    
    data = parser._parse_llm_response(content)
    
    assert data['title'] == "Test Title"


def test_parse_llm_response_invalid(parser):
    """测试无效的 JSON 响应"""
    content = "This is not JSON at all"
    
    with pytest.raises(ValueError, match="无法解析 LLM 响应为 JSON"):
        parser._parse_llm_response(content)


def test_validate_and_clean_data(parser):
    """测试数据验证和清理"""
    data = {
        "title": "Test Title",
        "published_at": "2024-01-01",
        "corresponding_author": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-123-456-7890",
            "institution": "Harvard University",
            "address": "Cambridge, MA, USA"
        }
    }
    
    cleaned = parser._validate_and_clean_data(data)
    
    assert cleaned['title'] == "Test Title"
    assert cleaned['published_at'] == "2024-01-01"
    assert cleaned['corresponding_author']['name'] == "John Doe"


def test_validate_and_clean_data_missing_fields(parser):
    """测试缺失字段的数据清理"""
    data = {
        "title": "Test Title",
        # published_at 缺失
        "corresponding_author": {
            "name": "John Doe"
            # 其他字段缺失
        }
    }
    
    cleaned = parser._validate_and_clean_data(data)
    
    assert cleaned['title'] == "Test Title"
    assert cleaned['published_at'] is None
    assert cleaned['corresponding_author']['name'] == "John Doe"
    assert cleaned['corresponding_author']['email'] is None


def test_parse_date_valid(parser):
    """测试有效日期解析"""
    assert parser._parse_date("2024-01-15") == "2024-01-15"
    assert parser._parse_date("2024/01/15") == "2024-01-15"
    assert parser._parse_date("January 15, 2024") == "2024-01-15"


def test_parse_date_invalid(parser):
    """测试无效日期解析"""
    assert parser._parse_date("invalid date") is None
    assert parser._parse_date("") is None
    assert parser._parse_date(None) is None


def test_get_summary(parser, sample_result_file):
    """测试获取摘要"""
    results = parser.parse_result_file(sample_result_file)
    summary = parser.get_summary(results)
    
    assert summary['total'] == 3
    assert summary['success'] == 1
    assert summary['failed'] == 1
    assert summary['parse_error'] == 1


def test_parse_result_file_not_found(parser):
    """测试文件不存在"""
    with pytest.raises(FileNotFoundError):
        parser.parse_result_file(Path("nonexistent.jsonl"))
