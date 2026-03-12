"""
Unit tests for BatchProcessor
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.processors.batch_processor import BatchProcessor
from src.db.models import RawMarkdown


@pytest.fixture
def batch_processor():
    """创建 BatchProcessor 实例"""
    return BatchProcessor()


@pytest.fixture
def sample_papers():
    """创建示例论文列表"""
    return [
        RawMarkdown(
            doi="10.1016/j.example.2024.001",
            pmid="12345678",
            markdown_content="# Test Paper\n\n## Abstract\nThis is a test.",
            source_url="https://doi.org/10.1016/j.example.2024.001",
            processing_status="pending"
        ),
        RawMarkdown(
            doi="10.1016/j.example.2024.002",
            pmid="12345679",
            markdown_content="# Another Paper\n\n## Introduction\nAnother test.",
            source_url="https://doi.org/10.1016/j.example.2024.002",
            processing_status="pending"
        )
    ]


@pytest.mark.asyncio
async def test_get_unprocessed_papers(batch_processor):
    """测试获取未处理论文"""
    with patch('src.processors.batch_processor.get_session') as mock_session:
        # Mock 数据库返回
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        mock_session_instance = AsyncMock()
        mock_session_instance.execute.return_value = mock_result
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        papers = await batch_processor.get_unprocessed_papers(limit=10)
        
        assert isinstance(papers, list)


@pytest.mark.asyncio
async def test_build_batch_file(batch_processor, sample_papers, tmp_path):
    """测试构建 JSONL 文件"""
    output_dir = tmp_path / "batch"
    
    file_path = await batch_processor.build_batch_file(
        sample_papers,
        output_dir=output_dir
    )
    
    # 验证文件存在
    assert file_path.exists()
    assert file_path.suffix == ".jsonl"
    
    # 验证文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        assert len(lines) == 2  # 2 篇论文
        
        # 验证第一行是有效的 JSON
        import json
        first_line = json.loads(lines[0])
        assert "custom_id" in first_line
        assert "method" in first_line
        assert "url" in first_line
        assert "body" in first_line
        assert first_line["body"]["model"] == "glm-4-plus"
        assert first_line["body"]["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_mark_as_processing(batch_processor, sample_papers):
    """测试标记为处理中"""
    batch_id = "batch_test_123"
    
    with patch('src.processors.batch_processor.get_session') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        await batch_processor.mark_as_processing(sample_papers, batch_id)
        
        # 验证调用了数据库更新
        assert mock_session_instance.execute.called
        assert mock_session_instance.commit.called


@pytest.mark.asyncio
async def test_mark_as_completed(batch_processor):
    """测试标记为完成"""
    doi = "10.1016/j.example.2024.001"
    extracted_data = {
        "title": "Test Paper",
        "published_at": "2024-01-01",
        "corresponding_author": {
            "name": "John Doe",
            "email": "john@example.com"
        }
    }
    
    with patch('src.processors.batch_processor.get_session') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        await batch_processor.mark_as_completed(doi, extracted_data)
        
        # 验证调用了数据库更新
        assert mock_session_instance.execute.called
        assert mock_session_instance.commit.called


@pytest.mark.asyncio
async def test_mark_as_failed(batch_processor):
    """测试标记为失败"""
    doi = "10.1016/j.example.2024.001"
    error_message = "JSON 解析失败"
    
    with patch('src.processors.batch_processor.get_session') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        await batch_processor.mark_as_failed(doi, error_message)
        
        # 验证调用了数据库更新
        assert mock_session_instance.execute.called
        assert mock_session_instance.commit.called


@pytest.mark.asyncio
async def test_get_processing_stats(batch_processor):
    """测试获取处理统计"""
    with patch('src.processors.batch_processor.get_session') as mock_session:
        # Mock 数据库返回
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ('pending', 10),
            ('processing', 5),
            ('completed', 100),
            ('failed', 3)
        ]
        
        mock_session_instance = AsyncMock()
        mock_session_instance.execute.return_value = mock_result
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        stats = await batch_processor.get_processing_stats()
        
        assert stats['pending'] == 10
        assert stats['processing'] == 5
        assert stats['completed'] == 100
        assert stats['failed'] == 3


@pytest.mark.asyncio
async def test_build_batch_file_empty_papers(batch_processor):
    """测试空论文列表"""
    with pytest.raises(ValueError, match="论文列表为空"):
        await batch_processor.build_batch_file([])
