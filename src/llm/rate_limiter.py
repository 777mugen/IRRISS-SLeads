"""
LLM Rate Limiter for GLM-5 API.
GLM-5 API 速率限制器。
"""

import asyncio
import time
from datetime import datetime, time as dt_time
from typing import Optional
from src.logging_config import get_logger


class GLMRateLimiter:
    """
    GLM-5 速率限制器
    
    根据时段自动调整请求间隔：
    - 高峰期 (14:00-18:00): 30 秒/请求
    - 非高峰期: 20 秒/请求
    
    参考: https://docs.bigmodel.cn/cn/coding-plan/overview
    高峰期消耗 3x，非高峰期 2x
    """
    
    # 时段配置
    PEAK_START = dt_time(14, 0)   # 高峰期开始
    PEAK_END = dt_time(18, 0)     # 高峰期结束
    
    # 间隔配置
    PEAK_INTERVAL = 30.0          # 高峰期间隔（秒）
    OFF_PEAK_INTERVAL = 20.0      # 非高峰期间隔（秒）
    
    def __init__(self):
        self.logger = get_logger()
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
        self._request_count: int = 0
    
    def _is_peak_hour(self) -> bool:
        """检查当前是否为高峰期"""
        now = datetime.now().time()
        return self.PEAK_START <= now <= self.PEAK_END
    
    def _get_interval(self) -> float:
        """获取当前应使用的间隔"""
        return self.PEAK_INTERVAL if self._is_peak_hour() else self.OFF_PEAK_INTERVAL
    
    async def acquire(self):
        """
        获取请求许可
        
        会自动等待直到满足速率限制
        """
        async with self._lock:
            interval = self._get_interval()
            elapsed = time.time() - self._last_request_time
            
            if elapsed < interval and self._last_request_time > 0:
                wait_time = interval - elapsed
                self.logger.debug(
                    f"速率限制: 等待 {wait_time:.1f} 秒 "
                    f"(高峰期={'是' if self._is_peak_hour() else '否'})"
                )
                await asyncio.sleep(wait_time)
            
            self._last_request_time = time.time()
            self._request_count += 1
    
    def get_stats(self) -> dict:
        """获取速率限制器状态"""
        return {
            'is_peak_hour': self._is_peak_hour(),
            'current_interval': self._get_interval(),
            'last_request': self._last_request_time,
            'seconds_since_last': time.time() - self._last_request_time if self._last_request_time > 0 else 0,
            'total_requests': self._request_count
        }
    
    def reset(self):
        """重置状态"""
        self._last_request_time = 0
        self._request_count = 0


# 全局单例
_rate_limiter: Optional[GLMRateLimiter] = None


def get_rate_limiter() -> GLMRateLimiter:
    """获取全局速率限制器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = GLMRateLimiter()
    return _rate_limiter
