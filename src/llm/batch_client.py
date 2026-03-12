"""
智谱批量处理 API 客户端
用于批量处理论文提取任务
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import httpx

from src.config import config
from src.logging_config import get_logger


class ZhiPuBatchClient:
    """智谱批量处理 API 客户端"""
    
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.zai_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        self._client = httpx.AsyncClient(timeout=300.0)  # 批量任务可能需要更长超时
        self.logger = get_logger()
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    async def upload_file(self, file_path: Path, purpose: str = "batch") -> str:
        """
        上传文件
        
        Args:
            file_path: 文件路径
            purpose: 文件用途（batch）
            
        Returns:
            file_id
        """
        url = f"{self.BASE_URL}/files"
        
        with open(file_path, 'rb') as f:
            files = {
                "file": (file_path.name, f, "application/jsonl")
            }
            data = {
                "purpose": purpose
            }
            
            self.logger.info(f"上传文件: {file_path}")
            
            response = await self._client.post(
                url,
                headers=self.headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            
            result = response.json()
            file_id = result["id"]
            
            self.logger.info(f"上传成功: file_id={file_id}")
            return file_id
    
    async def create_batch(
        self,
        input_file_id: str,
        endpoint: str = "/v4/chat/completions",
        metadata: Optional[dict] = None
    ) -> str:
        """
        创建批处理任务
        
        Args:
            input_file_id: 输入文件 ID
            endpoint: 端点（/v4/chat/completions）
            metadata: 元数据
            
        Returns:
            batch_id
        """
        url = f"{self.BASE_URL}/batches"
        
        payload = {
            "input_file_id": input_file_id,
            "endpoint": endpoint,
            "auto_delete_input_file": False,
            "metadata": metadata or {}
        }
        
        self.logger.info(f"创建批处理任务: input_file_id={input_file_id}")
        
        response = await self._client.post(
            url,
            headers={**self.headers, "Content-Type": "application/json"},
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        batch_id = result["id"]
        
        self.logger.info(f"批处理任务已创建: batch_id={batch_id}, status={result.get('status')}")
        return batch_id
    
    async def get_batch(self, batch_id: str) -> dict:
        """
        获取批处理任务状态
        
        Args:
            batch_id: 批处理任务 ID
            
        Returns:
            任务详情
        """
        url = f"{self.BASE_URL}/batches/{batch_id}"
        
        response = await self._client.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    async def wait_for_completion(
        self,
        batch_id: str,
        poll_interval: int = 30,
        max_wait: int = 3600
    ) -> dict:
        """
        等待批处理任务完成
        
        Args:
            batch_id: 批处理任务 ID
            poll_interval: 轮询间隔（秒）
            max_wait: 最大等待时间（秒）
            
        Returns:
            任务详情
        """
        self.logger.info(f"等待批处理任务完成: batch_id={batch_id}")
        
        elapsed = 0
        while elapsed < max_wait:
            batch = await self.get_batch(batch_id)
            status = batch.get("status")
            
            self.logger.info(
                f"任务状态: {status}, "
                f"进度: {batch.get('completed', 0)}/{batch.get('total', 0)}"
            )
            
            if status == "completed":
                self.logger.info(f"批处理任务完成: batch_id={batch_id}")
                return batch
            elif status == "failed":
                error = batch.get("error_file_id")
                raise Exception(f"批处理任务失败: error_file_id={error}")
            elif status in ["expired", "cancelled"]:
                raise Exception(f"批处理任务异常: status={status}")
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise Exception(f"批处理任务超时: batch_id={batch_id}")
    
    async def download_result(self, file_id: str, output_path: Path) -> Path:
        """
        下载结果文件
        
        Args:
            file_id: 文件 ID
            output_path: 输出路径
            
        Returns:
            文件路径
        """
        url = f"{self.BASE_URL}/files/{file_id}/content"
        
        self.logger.info(f"下载结果文件: file_id={file_id}")
        
        response = await self._client.get(url, headers=self.headers)
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        self.logger.info(f"结果文件已保存: {output_path}")
        return output_path
    
    async def list_batches(self, limit: int = 10) -> list[dict]:
        """
        列出批处理任务
        
        Args:
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        url = f"{self.BASE_URL}/batches"
        params = {"limit": limit}
        
        response = await self._client.get(
            url,
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        return response.json().get("data", [])
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def test_batch_api():
    """测试批量 API"""
    print("\n" + "="*60)
    print("🧪 智谱批量处理 API 测试")
    print("="*60)
    
    # 创建测试 JSONL 文件
    test_file = Path("tests/data/batch_test.jsonl")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建测试请求
    test_requests = [
        {
            "custom_id": "test-1",
            "method": "POST",
            "url": "/v4/chat/completions",
            "body": {
                "model": "glm-4-plus",
                "messages": [
                    {"role": "user", "content": "请用一句话介绍什么是多重免疫荧光（mIF）技术？"}
                ],
                "max_tokens": 100
            }
        },
        {
            "custom_id": "test-2",
            "method": "POST",
            "url": "/v4/chat/completions",
            "body": {
                "model": "glm-4-plus",
                "messages": [
                    {"role": "user", "content": "请用一句话介绍什么是 DOI？"}
                ],
                "max_tokens": 100
            }
        }
    ]
    
    # 写入 JSONL 文件
    with open(test_file, 'w', encoding='utf-8') as f:
        for req in test_requests:
            f.write(json.dumps(req, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 测试文件已创建: {test_file}")
    print(f"   包含 {len(test_requests)} 个请求")
    
    async with ZhiPuBatchClient() as client:
        # Step 1: 上传文件
        print("\n[1/5] 上传文件...")
        file_id = await client.upload_file(test_file)
        print(f"   ✅ file_id: {file_id}")
        
        # Step 2: 创建批处理任务
        print("\n[2/5] 创建批处理任务...")
        batch_id = await client.create_batch(file_id)
        print(f"   ✅ batch_id: {batch_id}")
        
        # Step 3: 查询任务状态
        print("\n[3/5] 查询任务状态...")
        batch = await client.get_batch(batch_id)
        print(f"   状态: {batch.get('status')}")
        
        # Step 4: 等待完成（最多等待 5 分钟）
        print("\n[4/5] 等待任务完成...")
        try:
            batch = await client.wait_for_completion(
                batch_id,
                poll_interval=10,
                max_wait=300
            )
            print(f"   ✅ 任务完成")
            
            # Step 5: 下载结果
            print("\n[5/5] 下载结果...")
            output_file_id = batch.get("output_file_id")
            if output_file_id:
                output_path = Path(f"tests/data/batch_result_{batch_id}.jsonl")
                await client.download_result(output_file_id, output_path)
                print(f"   ✅ 结果已保存: {output_path}")
                
                # 读取并显示结果
                with open(output_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        result = json.loads(line)
                        print(f"\n   custom_id: {result.get('custom_id')}")
                        response = result.get('response', {})
                        if response.get('status_code') == 200:
                            body = response.get('body', {})
                            content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
                            print(f"   回答: {content[:100]}...")
                        else:
                            print(f"   ❌ 错误: {response.get('status_code')}")
            else:
                print("   ⚠️  无输出文件")
                
        except Exception as e:
            print(f"   ❌ 任务失败: {e}")
            
            # 查看错误文件
            error_file_id = batch.get("error_file_id")
            if error_file_id:
                error_path = Path(f"tests/data/batch_error_{batch_id}.jsonl")
                await client.download_result(error_file_id, error_path)
                print(f"   错误文件: {error_path}")
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_batch_api())
