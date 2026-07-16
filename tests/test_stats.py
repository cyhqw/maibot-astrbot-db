"""tests.test_stats — 统计聚合表测试"""

import time

import pytest


@pytest.mark.asyncio
async def test_platform_stat_incr(db_instance):
    """平台消息统计应能原子自增。"""

    now = int(time.time())

    # 同一时间桶自增 3 次
    await db_instance.incr_platform_stat(now, "aiocqhttp", "GroupMessage")
    await db_instance.incr_platform_stat(now, "aiocqhttp", "GroupMessage")
    await db_instance.incr_platform_stat(now, "aiocqhttp", "GroupMessage", count=5)

    count = await db_instance.count_rows("platform_stats")
    assert count == 1  # 同一桶只有一行

    # 读出来验证 count
    from sqlalchemy import text
    async with db_instance.get_db() as session:
        result = await session.execute(text("SELECT count FROM platform_stats"))
        row = result.fetchone()
        assert row[0] == 7  # 1 + 1 + 5


@pytest.mark.asyncio
async def test_platform_stat_different_buckets(db_instance):
    """不同时间桶 / 不同平台应是独立行。"""

    now = int(time.time())
    await db_instance.incr_platform_stat(now, "aiocqhttp", "GroupMessage")
    await db_instance.incr_platform_stat(now + 60, "aiocqhttp", "GroupMessage")
    await db_instance.incr_platform_stat(now, "webchat", "FriendMessage")

    count = await db_instance.count_rows("platform_stats")
    assert count == 3


@pytest.mark.asyncio
async def test_provider_stat(db_instance):
    """LLM Provider 调用统计。"""

    stat = await db_instance.record_provider_stat(
        umo="aiocqhttp:GroupMessage:111",
        provider_id="openai",
        provider_model="gpt-4",
        status="success",
        request_type="chat",
        time_cost=1.23,
        timestamp=int(time.time()),
        token_input=100,
        token_output=50,
    )
    assert stat.id is not None
    assert stat.token_input == 100

    count = await db_instance.count_rows("provider_stats")
    assert count == 1
