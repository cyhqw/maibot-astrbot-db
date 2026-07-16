"""tests.conftest — pytest 共享 fixture"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# 让 tests 能找到 astrdb 包
sys.path.insert(0, str(Path(__file__).parent.parent))

# 让 tests 能找到 maibot_sdk（如果环境里没装）
_SDK_PATH = Path("/home/z/my-project/research/maibot_plugin_sdk-2.7.0")
if _SDK_PATH.exists():
    sys.path.insert(0, str(_SDK_PATH))


@pytest_asyncio.fixture
async def db_instance():
    """提供一个初始化好的临时数据库实例（含迁移）。"""

    tmpdir = tempfile.mkdtemp(prefix="astrdb_test_")
    db_path = os.path.join(tmpdir, "test.db")

    from astrdb import AstrBotDatabase, run_migrations
    db = AstrBotDatabase(db_path)
    await db.initialize()
    # 跑迁移，让 preferences 表中有 initial_schema_v1 标记
    await run_migrations(db)
    yield db
    await db.close()
