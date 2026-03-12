"""
Integration tests for BatchPipeline
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.pipeline_batch import BatchPipeline


@pytest.fixture
def pipeline():
    """创建 BatchPipeline 实例"""
    return BatchPipeline()


@pytest.mark.asyncio
async def test_run_batch_extraction_no_papers(pipeline):
    """测试没有未处理论文的情况"""
    with patch.object(pipeline.batch_processor, 'get_unprocessed_papers', return_value=[]):
        result = await pipeline.run_batch_extraction(limit=10)
        
        assert result['status'] == 'no_papers'
        assert result['total_papers'] == 0
        assert result['successful'] == 0
        assert result['failed'] == 0


@pytest.mark.asyncio
async def test_run_batch_extraction_success(pipeline, tmp_path):
    """测试成功的批处理流程"""
    from src.db.models import RawMarkdown
    
    # Mock 论文
    papers = [
        RawMarkdown(
            doi="10.1016/j.example.2024.001",
            pmid="12345678",
            markdown_content="# Test",
            source_url="https://doi.org/10.1016/j.example.2024.001",
            processing_status="pending"
        )
    ]
    
    # Mock 批处理客户端
    mock_client = AsyncMock()
    mock_client.upload_file.return_value = "file_123"
    mock_client.create_batch.return_value = "batch_123"
    mock_client.wait_for_completion.return_value = {
        "output_file_id": "output_123"
    }
    mock_client.download_result.return_value = tmp_path / "results.jsonl"
    
    # 创建模拟的结果文件
    import json
    result_file = tmp_path / "results.jsonl"
    with open(result_file, 'w') as f:
        f.write(json.dumps({
            "custom_id": "doi_10.1016_j.example.2024.001",
            "response": {
                "status_code": 200,
                "body": {
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "title": "Test",
                                "corresponding_author": {"name": "John"}
                            })
                        }
                    }]
                }
            }
        }) + '\n')
    
    with patch.object(pipeline.batch_processor, 'get_unprocessed_papers', return_value=papers):
        with patch.object(pipeline.batch_processor, 'mark_as_processing'):
            with patch.object(pipeline.batch_processor, 'mark_as_completed'):
                with patch('src.pipeline_batch.ZhiPuBatchClient', return_value=mock_client):
                    result = await pipeline.run_batch_extraction(
                        limit=10,
                        wait_for_completion=True,
                        max_wait_minutes=1
                    )
                    
                    assert result['status'] == 'completed'
                    assert result['batch_id'] == "batch_123"
                    assert result['total_papers'] == 1


@pytest.mark.asyncio
async def test_check_batch_status(pipeline):
    """测试查询批处理状态"""
    mock_client = AsyncMock()
    mock_client.get_batch.return_value = {
        "id": "batch_123",
        "status": "in_progress",
        "total": 10,
        "completed": 5,
        "failed": 0
    }
    
    with patch('src.pipeline_batch.ZhiPuBatchClient', return_value=mock_client):
        status = await pipeline.check_batch_status("batch_123")
        
        assert status['batch_id'] == "batch_123"
        assert status['status'] == "in_progress"
        assert status['total'] == 10
        assert status['completed'] == 5


@pytest.mark.asyncio
async def test_get_processing_stats(pipeline):
    """测试获取处理统计"""
    with patch.object(pipeline.batch_processor, 'get_processing_stats', return_value={
        'pending': 10,
        'processing': 5,
        'completed': 100,
        'failed': 3
    }):
        stats = await pipeline.get_processing_stats()
        
        assert stats['pending'] == 10
        assert stats['processing'] == 5
        assert stats['completed'] == 100
        assert stats['failed'] == 3


@pytest.mark.asyncio
async def test_update_paper_lead(pipeline):
    """测试更新 paper_leads 表"""
    doi = "10.1016/j.example.2024.001"
    data = {
        "title": "Test Title",
        "published_at": "2024-01-01",
        "corresponding_author": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-123-456-7890",
            "institution": "Harvard",
            "address": "Cambridge, MA"
        }
    }
    
    with patch('src.pipeline_batch.get_session') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        await pipeline._update_paper_lead(doi, data)
        
        # 验证数据库更新被调用
        assert mock_session_instance.execute.called
        assert mock_session_instance.commit.called
