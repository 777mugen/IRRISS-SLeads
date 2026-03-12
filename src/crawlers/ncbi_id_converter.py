"""
NCBI ID Converter API Client
NCBI ID 转换 API 客户端

Official documentation: https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
"""

import asyncio
from typing import Dict, List, Optional

import httpx

from src.logging_config import get_logger


class NCBIIDConverter:
    """
    NCBI ID Converter API 客户端
    
    批量转换 PMID → DOI
    这是最快、最准确的 DOI 获取工具
    """
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    def __init__(self):
        self.logger = get_logger()
        self._http = httpx.AsyncClient(timeout=30.0)
        self._last_request_time = 0
        self._rate_limit = 0.5  # 2 requests/second
    
    async def close(self):
        """关闭客户端"""
        await self._http.aclose()
    
    async def _rate_limit_wait(self):
        """等待速率限制"""
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._rate_limit:
            await asyncio.sleep(self._rate_limit - elapsed)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def convert_pmids_to_dois(
        self,
        pmids: List[str],
        batch_size: int = 200
    ) -> Dict[str, Optional[str]]:
        """
        批量转换 PMID → DOI
        
        Args:
            pmids: PMID 列表
            batch_size: 每批数量（API 限制 100-200）
            
        Returns:
            {pmid: doi, ...} (无 DOI 的 PMID 值为 None)
            
        Example:
            >>> converter = NCBIIDConverter()
            >>> result = await converter.convert_pmids_to_dois(
            ...     ['37105494', '32301585', '29553498']
            ... )
            >>> result
            {
                '37105494': '10.1016/j.modpat.2023.100197',
                '32301585': '10.1002/cac2.12023',
                '29553498': '10.3791/56606'
            }
        """
        if not pmids:
            return {}
        
        result = {}
        
        # 分批处理
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            batch_result = await self._convert_batch(batch)
            result.update(batch_result)
        
        return result
    
    async def _convert_batch(self, pmids: List[str]) -> Dict[str, Optional[str]]:
        """
        转换一批 PMID
        
        Args:
            pmids: PMID 列表（最多 200 个）
            
        Returns:
            {pmid: doi, ...}
        """
        await self._rate_limit_wait()
        
        params = {
            "ids": ",".join(pmids),
            "format": "json"
        }
        
        self.logger.info(f"转换 PMID → DOI: {len(pmids)} 个")
        
        try:
            response = await self._http.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            result = {}
            
            for record in data.get("records", []):
                pmid = record.get("pmid")
                doi = record.get("doi")
                status = record.get("status")
                
                if pmid:
                    # 记录状态
                    if status and status != "success":
                        self.logger.debug(f"PMID {pmid} 状态: {status}")
                    
                    # 添加到结果（无 DOI 时为 None）
                    result[pmid] = doi if doi else None
            
            # 统计转换成功率
            success_count = sum(1 for doi in result.values() if doi)
            self.logger.info(
                f"转换完成: {success_count}/{len(pmids)} "
                f"({success_count/len(pmids)*100:.1f}%)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"DOI 转换失败: {e}")
            # 返回空结果，所有 PMID 都标记为 None
            return {pmid: None for pmid in pmids}
    
    async def convert_single(self, pmid: str) -> Optional[str]:
        """
        转换单个 PMID
        
        Args:
            pmid: PMID
            
        Returns:
            DOI（如果存在）
        """
        result = await self.convert_pmids_to_dois([pmid])
        return result.get(pmid)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
