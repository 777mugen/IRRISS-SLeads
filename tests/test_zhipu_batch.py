"""
测试智谱批量处理 API（独立版本）
"""

import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
import os

import httpx


async def test_batch_api():
    """测试批量 API"""
    load_dotenv()
    
    api_key = os.getenv("ZAI_API_KEY")
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    
    print("\n" + "="*60)
    print("🧪 智谱批量处理 API 测试")
    print("="*60)
    print(f"API Key: {api_key[:20]}...")
    
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
        }
    ]
    
    # 写入 JSONL 文件
    with open(test_file, 'w', encoding='utf-8') as f:
        for req in test_requests:
            f.write(json.dumps(req, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 测试文件已创建: {test_file}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: 上传文件
        print("\n[1/5] 上传文件...")
        url = f"{base_url}/files"
        
        with open(test_file, 'rb') as f:
            files = {"file": (test_file.name, f, "application/jsonl")}
            data = {"purpose": "batch"}
            headers = {"Authorization": f"Bearer {api_key}"}
            
            response = await client.post(url, headers=headers, files=files, data=data)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ 错误: {response.text}")
                return
            
            result = response.json()
            file_id = result["id"]
            print(f"   ✅ file_id: {file_id}")
        
        # Step 2: 创建批处理任务
        print("\n[2/5] 创建批处理任务...")
        url = f"{base_url}/batches"
        
        payload = {
            "input_file_id": file_id,
            "endpoint": "/v4/chat/completions",
            "auto_delete_input_file": False
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = await client.post(url, headers=headers, json=payload)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ 错误: {response.text}")
            return
        
        result = response.json()
        batch_id = result["id"]
        print(f"   ✅ batch_id: {batch_id}")
        print(f"   状态: {result.get('status')}")
        
        # Step 3: 轮询状态
        print("\n[3/5] 等待任务完成...")
        
        for i in range(30):  # 最多等待 5 分钟
            url = f"{base_url}/batches/{batch_id}"
            response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            result = response.json()
            
            status = result.get("status")
            completed = result.get("completed", 0)
            total = result.get("total", 0)
            
            print(f"   [{i+1}/30] 状态: {status}, 进度: {completed}/{total}")
            
            if status == "completed":
                print(f"   ✅ 任务完成！")
                
                # 下载结果
                output_file_id = result.get("output_file_id")
                if output_file_id:
                    url = f"{base_url}/files/{output_file_id}/content"
                    response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                    
                    output_path = Path(f"tests/data/batch_result_{batch_id}.jsonl")
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"   ✅ 结果已保存: {output_path}")
                    
                    # 显示结果
                    with open(output_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            r = json.loads(line)
                            print(f"\n   custom_id: {r.get('custom_id')}")
                            resp = r.get('response', {})
                            if resp.get('status_code') == 200:
                                body = resp.get('body', {})
                                content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
                                print(f"   回答: {content}")
                            else:
                                print(f"   ❌ 错误: {resp}")
                
                break
            elif status in ["failed", "expired", "cancelled"]:
                print(f"   ❌ 任务失败: {status}")
                print(f"   详情: {result}")
                break
            
            await asyncio.sleep(10)
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_batch_api())
