"""
Feishu notification client with signature support.
飞书通知客户端，支持签名校验。
"""

import base64
import hashlib
import hmac
import time
from datetime import datetime
from typing import Optional

import httpx

from src.config import config
from src.logging_config import get_logger


class FeishuNotifier:
    """
    飞书机器人通知
    
    使用 Webhook 发送消息到飞书群
    支持签名校验
    """
    
    def __init__(self, webhook_url: Optional[str] = None, secret: Optional[str] = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人 Webhook URL
            secret: 飞书机器人签名密钥
        """
        self.webhook_url = webhook_url or getattr(config, 'feishu_webhook', None)
        self.secret = secret or getattr(config, 'feishu_secret', None)
        self.logger = get_logger()
        self._client = httpx.AsyncClient(timeout=10.0)
    
    def _generate_sign(self, timestamp: int) -> str:
        """
        生成签名
        
        飞书签名算法：
        string_to_sign = timestamp + "\n" + secret
        sign = Base64(HmacSHA256(string_to_sign, ""))
        
        Args:
            timestamp: 时间戳（秒）
            
        Returns:
            Base64 编码的签名
        """
        if not self.secret:
            return ""
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        # 飞书签名算法：sign = Base64(HmacSHA256(string_to_sign, ""))
        # 注意：密钥是 string_to_sign，消息是空字符串
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),  # 密钥是 string_to_sign
            b"",  # 消息是空字符串
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")
    
    def _build_payload(self, msg_type: str, content: dict) -> dict:
        """
        构建请求体（包含签名）
        
        Args:
            msg_type: 消息类型
            content: 消息内容
            
        Returns:
            完整的请求体
        """
        payload = {
            "msg_type": msg_type,
            "content": content
        }
        
        # 添加签名
        if self.secret:
            timestamp = int(time.time())
            payload["timestamp"] = str(timestamp)
            payload["sign"] = self._generate_sign(timestamp)
        
        return payload
    
    async def send_text(self, text: str) -> bool:
        """
        发送文本消息
        
        Args:
            text: 消息内容
            
        Returns:
            是否成功
        """
        if not self.webhook_url:
            self.logger.warning("飞书 Webhook 未配置")
            return False
        
        payload = self._build_payload("text", {"text": text})
        
        try:
            response = await self._client.post(
                self.webhook_url,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("StatusCode") == 0:
                self.logger.info("飞书通知发送成功")
                return True
            else:
                self.logger.error(f"飞书通知发送失败: {result}")
                return False
        except Exception as e:
            self.logger.error(f"飞书通知发送失败: {e}")
            return False
    
    async def send_daily_summary(self, stats: dict) -> bool:
        """
        发送每日任务摘要
        
        Args:
            stats: {
                'papers_found': int,
                'papers_processed': int,
                'tenders_found': int,
                'leads_exported': int,
                'duration_seconds': float
            }
        """
        duration = stats.get('duration_seconds', 0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        text = f"""📊 每日线索采集完成

📄 论文: 发现 {stats.get('papers_found', 0)} 篇，处理 {stats.get('papers_processed', 0)} 篇
📋 招标: 发现 {stats.get('tenders_found', 0)} 条
📤 导出: {stats.get('leads_exported', 0)} 条线索
⏱️ 耗时: {minutes} 分 {seconds} 秒

时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        return await self.send_text(text)
    
    async def send_error_alert(self, error: str, context: Optional[str] = None) -> bool:
        """
        发送错误告警
        
        Args:
            error: 错误信息
            context: 上下文信息
        """
        text = f"""🚨 系统错误告警

错误: {error[:500]}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        if context:
            text += f"\n\n上下文: {context[:200]}"
        
        return await self.send_text(text)
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
