"""
Logging configuration for Sales Lead Discovery System.
日志配置。
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    retention_days: int = 30
) -> structlog.stdlib.BoundLogger:
    """
    配置结构化日志
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        retention_days: 日志保留天数
        
    Returns:
        配置好的 logger
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 清理旧日志
    cleanup_old_logs(log_path, retention_days)
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # 文件处理器
    log_file = log_path / f"sleads_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logging.root.addHandler(file_handler)
    
    return structlog.get_logger()


def cleanup_old_logs(log_path: Path, retention_days: int):
    """清理超过保留期的日志文件"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    for log_file in log_path.glob("sleads_*.log"):
        try:
            file_date_str = log_file.stem.replace("sleads_", "")
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
            if file_date < cutoff:
                log_file.unlink()
        except (ValueError, OSError):
            pass  # 忽略解析错误


# 全局 logger
logger: Optional[structlog.stdlib.BoundLogger] = None


def get_logger() -> structlog.stdlib.BoundLogger:
    """获取 logger 实例"""
    global logger
    if logger is None:
        logger = setup_logging()
    return logger
