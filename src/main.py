"""
Main entry point for Sales Lead Discovery System.
销售线索发现系统主入口。
"""

import asyncio

from src.config import config
from src.logging_config import setup_logging, get_logger


async def main():
    """主函数"""
    # 初始化日志
    setup_logging(log_level=config.log_level)
    logger = get_logger()
    
    logger.info("销售线索发现系统启动")
    logger.info("配置加载完成", 
                database_url=config.database_url.split('@')[-1],  # 隐藏敏感信息
                log_level=config.log_level)
    
    # TODO: 实现主流程
    # 1. 搜索新 URL
    # 2. 过滤已爬取 URL
    # 3. 抓取页面内容
    # 4. 提取结构化字段
    # 5. 入库
    # 6. 评分
    # 7. 导出 CSV
    
    logger.info("销售线索发现系统运行完成")


def run():
    """运行入口"""
    asyncio.run(main())


if __name__ == "__main__":
    run()
