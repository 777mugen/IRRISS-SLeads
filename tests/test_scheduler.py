#!/usr/bin/env python3
"""Test scheduler implementation."""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.scheduler.scheduler import TaskScheduler
from src.logging_config import setup_logging

setup_logging(log_level='INFO')


async def test_daily_task():
    print("Testing run_daily_task...")
    scheduler = TaskScheduler()
    await scheduler.run_daily_task()
    print("Daily task completed!")


async def test_full_export():
    print("Testing run_full_export...")
    scheduler = TaskScheduler()
    await scheduler.run_full_export()
    print("Full export completed!")


async def main():
    print("Testing scheduler implementation...")
    await test_daily_task()
    await test_full_export()
    print("All scheduler tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
