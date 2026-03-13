"""
处理批处理任务结果
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from datetime import datetime

from src.llm.batch_client import ZhiPuBatchClient
from src.processors.batch_result_parser import BatchResultParser
from src.db.models import PaperLead
from src.db.utils import get_session
from src.logging_config import get_logger
from sqlalchemy import update


async def process_batch_results():
    """处理批处理任务结果"""
    logger = get_logger()
    
    batch_id = "batch_2032437832023674880"
    
    print(f"\n{'='*60}")
    print(f"📊 处理批处理任务结果")
    print(f"{'='*60}")
    print(f"  批次 ID: {batch_id}")
    
    async with ZhiPuBatchClient() as client:
        # Step 1: 获取任务信息
        print(f"\n📝 Step 1: 获取任务信息...")
        batch = await client.get_batch(batch_id)
        
        status = batch.get('status')
        if status != 'completed':
            print(f"❌ 任务未完成: status={status}")
            return
        
        print(f"✅ 任务状态: {status}")
        print(f"  总数: {batch.get('request_counts', {}).get('total', 0)}")
        print(f"  完成: {batch.get('request_counts', {}).get('completed', 0)}")
        print(f"  失败: {batch.get('request_counts', {}).get('failed', 0)}")
        
        # Step 2: 下载结果文件
        print(f"\n📥 Step 2: 下载结果文件...")
        output_file_id = batch.get('output_file_id')
        
        if not output_file_id:
            print(f"❌ 没有输出文件")
            return
        
        output_path = Path(f"tmp/batch/results_{batch_id}.jsonl")
        await client.download_result(output_file_id, output_path)
        
        print(f"✅ 结果文件已下载: {output_path}")
        print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")
        
        # Step 3: 解析结果
        print(f"\n🔍 Step 3: 解析结果...")
        parser = BatchResultParser()
        results = parser.parse_result_file(output_path)
        
        success_count = sum(1 for r in results if r.get('status') == 'success')
        failed_count = sum(1 for r in results if r.get('status') != 'success')
        
        print(f"✅ 解析完成")
        print(f"  成功: {success_count}")
        print(f"  失败: {failed_count}")
        
        # Step 4: 更新数据库
        print(f"\n💾 Step 4: 更新数据库...")
        
        updated_count = 0
        failed_to_update = 0
        
        for result in results:
            doi = result.get('doi')
            status = result.get('status')
            
            if not doi:
                logger.warning(f"结果缺少 DOI: {result}")
                failed_to_update += 1
                continue
            
            if status == 'success':
                # 提取数据
                data = result.get('data', {})
                corr_author = data.get('corresponding_author', {})
                
                try:
                    # 转换日期格式
                    published_at_str = data.get('published_at')
                    published_at = None
                    if published_at_str:
                        try:
                            from datetime import datetime as dt
                            published_at = dt.strptime(published_at_str, '%Y-%m-%d').date()
                        except:
                            logger.warning(f"日期格式错误: {published_at_str}")
                    
                    # 更新或创建 paper_leads 记录
                    async with get_session() as session:
                        # 检查记录是否存在
                        from sqlalchemy import select
                        stmt = select(PaperLead).where(PaperLead.doi == doi)
                        result_query = await session.execute(stmt)
                        existing_lead = result_query.scalar_one_or_none()
                        
                        if existing_lead:
                            # 更新现有记录
                            stmt = (
                                update(PaperLead)
                                .where(PaperLead.doi == doi)
                                .values(
                                    title=data.get('title'),
                                    published_at=published_at,
                                    name=corr_author.get('name'),
                                    email=corr_author.get('email'),
                                    phone=corr_author.get('phone'),
                                    address=corr_author.get('address'),
                                    address_cn=corr_author.get('address_cn'),
                                    all_authors_info=json.dumps(data.get('all_authors_info'), ensure_ascii=False),
                                    all_authors_info_cn=json.dumps(data.get('all_authors_info_cn'), ensure_ascii=False),
                                    updated_at=datetime.utcnow()
                                )
                            )
                            await session.execute(stmt)
                            await session.commit()
                            updated_count += 1
                            logger.info(f"✅ 更新成功: DOI={doi}, 作者={corr_author.get('name')}")
                        else:
                            # 创建新记录（包含所有必填字段）
                            new_lead = PaperLead(
                                doi=doi,
                                title=data.get('title') or '',
                                published_at=published_at,
                                source_url=f"https://doi.org/{doi}",
                                article_url=f"https://doi.org/{doi}",
                                source='PubMed',
                                name=corr_author.get('name') or '',
                                email=corr_author.get('email') or '',
                                phone=corr_author.get('phone') or '',
                                address=corr_author.get('address') or '',
                                address_cn=corr_author.get('address_cn'),
                                all_authors_info=json.dumps(data.get('all_authors_info'), ensure_ascii=False) if data.get('all_authors_info') else None,
                                all_authors_info_cn=json.dumps(data.get('all_authors_info_cn'), ensure_ascii=False) if data.get('all_authors_info_cn') else None,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow()
                            )
                            session.add(new_lead)
                            await session.commit()
                            updated_count += 1
                            logger.info(f"✅ 创建成功: DOI={doi}, 作者={corr_author.get('name')}")
                
                except Exception as e:
                    logger.error(f"❌ 更新/创建失败: DOI={doi}, 错误={str(e)}")
                    failed_to_update += 1
            
            else:
                # 标记为失败
                error = result.get('error', 'Unknown error')
                logger.warning(f"提取失败: DOI={doi}, 错误={error}")
                failed_to_update += 1
        
        # Step 5: 统计
        print(f"\n{'='*60}")
        print(f"📊 处理完成统计")
        print(f"{'='*60}")
        print(f"  总数: {len(results)}")
        print(f"  更新成功: {updated_count}")
        print(f"  更新失败: {failed_to_update}")
        print(f"  成功率: {updated_count / len(results) * 100:.1f}%")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(process_batch_results())
