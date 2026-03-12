"""
Feishu notification client.
飞书通知客户端。
"""

from datetime import datetime
from typing import Optional

import httpx

from src.config import config
from src.logging_config import get_logger


class FeishuNotifier:
    """
    飞书机器人通知
    
    使用 Webhook 发送消息到飞书群
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人 Webhook URL
        """
        self.webhook_url = webhook_url or getattr(config, 'feishu_webhook', None)
        self.logger = get_logger()
        self._client = httpx.AsyncClient(timeout=10.0)
    
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
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        try:
            response = await self._client.post(
                self.webhook_url,
                json=payload
            )
            response.raise_for_status()
            self.logger.info("飞书通知发送成功")
            return True
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
    
    async def send_card(self, title: str, content: str) -> bool:
        """
        发送卡片消息
        
        Args:
            title: 卡片标题
            content: 卡片内容
        """
        if not self.webhook_url:
            self.logger.warning("飞书 Webhook 未配置")
            return False
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": content
                        }
                    }
                ]
            }
        }
        
        try:
            response = await self._client.post(
                self.webhook_url,
                json=payload
            )
            response.raise_for_status()
            self.logger.info("飞书卡片消息发送成功")
            return True
        except Exception as e:
            self.logger.error(f"飞书卡片消息发送失败: {e}")
            return False
    
    async def close(self):
        await self._client.aclose()
