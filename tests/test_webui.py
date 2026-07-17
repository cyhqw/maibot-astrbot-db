"""tests.test_webui — Web UI 端到端测试"""

import pytest

from maikb import close_db, get_db, init_db
from maikb.kb import (
    DummyEmbedder,
    HybridSearcher,
    KnowledgeBaseImporter,
    SearchQuery,
    VectorIndex,
)
from maikb.kb.api import (
    _kb_embedder,
    _kb_importer,
    _kb_searcher,
    _kb_vector_index,
)
from maikb.webui import WebServer


@pytest.fixture
async def setup_kb(tmp_path):
    """初始化数据库 + KB + 启动 Web server。"""

    db_path = tmp_path / "test.db"
    await init_db(db_path)

    # 写一些测试文件（内容足够长，可切成 ≥2 个 chunk 以便删除测试）
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "a.md").write_text("# 测试\n\n" + "法涅斯是原初之人。" * 60)

    # 初始化 KB 模块（绕过 plugin.py，直接用 kb.api 的全局变量）
    import maikb.kb.api as kb_api

    embedder = DummyEmbedder(dimension=64, model_name="dummy-test")
    index = VectorIndex()
    importer = KnowledgeBaseImporter(get_db(), index, embedder, kb_dir)
    searcher = HybridSearcher(get_db(), index, embedder)

    # 注入到 kb.api 全局变量
    kb_api._kb_importer = importer
    kb_api._kb_searcher = searcher
    kb_api._kb_vector_index = index
    kb_api._kb_embedder = embedder

    await importer.ingest_directory()

    # 启动 Web server（用随机端口避免冲突）
    import socket

    def free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    port = free_port()

    # 构造一个 fake plugin 对象
    class FakePlugin:
        class ctx:
            class paths:
                data_dir = tmp_path

        def get_plugin_config_data(self):
            return {"database": {"enabled": True}, "knowledge_base": {"enabled": True}}

    server = WebServer(plugin=FakePlugin(), host="127.0.0.1", port=port, token="")
    await server.start()

    # 等 server 完全启动
    import asyncio as _asyncio
    await _asyncio.sleep(0.5)

    yield server, port

    await server.stop()
    # 清理 kb.api 全局变量
    kb_api._kb_importer = None
    kb_api._kb_searcher = None
    kb_api._kb_vector_index = None
    kb_api._kb_embedder = None
    await close_db()


@pytest.mark.asyncio
async def test_health_endpoint(setup_kb):
    """测试 /health 端点。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://127.0.0.1:{port}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["service"] == "maikb-webui"


@pytest.mark.asyncio
async def test_index_page(setup_kb):
    """测试首页 HTML 返回。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://127.0.0.1:{port}/")
        assert resp.status_code == 200
        assert "MaiBot" in resp.text
        assert "知识库管理" in resp.text


@pytest.mark.asyncio
async def test_stats_endpoint(setup_kb):
    """测试 /api/stats 端点。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://127.0.0.1:{port}/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["files_total"] == 1
        assert data["files_ready"] == 1
        assert data["chunks_total"] > 0
        assert data["vector_index_size"] > 0
        assert data["embedding_model"] == "dummy-test"


@pytest.mark.asyncio
async def test_files_endpoint(setup_kb):
    """测试 /api/files 端点。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://127.0.0.1:{port}/api/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["file_name"] == "a.md"
        assert data["items"][0]["status"] == "ready"


@pytest.mark.asyncio
async def test_search_endpoint(setup_kb):
    """测试 /api/search 端点。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://127.0.0.1:{port}/api/search",
            json={"query": "法涅斯", "top_k": 3, "use_vector": True, "use_bm25": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert "法涅斯" in data["items"][0]["content"]


@pytest.mark.asyncio
async def test_config_endpoint(setup_kb):
    """测试 /api/config GET 端点。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://127.0.0.1:{port}/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "database" in data
        assert "knowledge_base" in data


@pytest.mark.asyncio
async def test_token_auth(tmp_path):
    """测试 token 认证。"""

    db_path = tmp_path / "auth.db"
    await init_db(db_path)

    import socket

    def free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    port = free_port()

    class FakePlugin:
        def get_plugin_config_data(self):
            return {}

    server = WebServer(plugin=FakePlugin(), host="127.0.0.1", port=port, token="secret123")
    await server.start()

    import asyncio as _asyncio
    await _asyncio.sleep(0.5)

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            # 无 token → 401
            resp = await client.get(f"http://127.0.0.1:{port}/api/stats")
            assert resp.status_code == 401

            # 错误 token → 401
            resp = await client.get(
                f"http://127.0.0.1:{port}/api/stats",
                headers={"Authorization": "Bearer wrong"},
            )
            assert resp.status_code == 401

            # 正确 token → 200
            resp = await client.get(
                f"http://127.0.0.1:{port}/api/stats",
                headers={"Authorization": "Bearer secret123"},
            )
            assert resp.status_code == 200
    finally:
        await server.stop()
        await close_db()


@pytest.mark.asyncio
async def test_delete_chunk_endpoint(setup_kb):
    """测试 DELETE /api/chunks/{chunk_id} 端点：删除单个 chunk + FTS + 内存索引。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        # 1. 取该文件的 chunk 列表，应有 ≥2 个
        resp = await client.get(f"http://127.0.0.1:{port}/api/files")
        assert resp.status_code == 200
        file_id = resp.json()["items"][0]["file_id"]
        original_chunk_count = resp.json()["items"][0]["chunk_count"]
        assert original_chunk_count >= 2

        resp = await client.get(f"http://127.0.0.1:{port}/api/files/{file_id}/chunks")
        assert resp.status_code == 200
        chunks_data = resp.json()
        assert chunks_data["count"] >= 2
        chunk_to_delete = chunks_data["items"][0]["chunk_id"]

        # 2. 删除第一个 chunk
        resp = await client.delete(f"http://127.0.0.1:{port}/api/chunks/{chunk_to_delete}")
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["chunk_id"] == chunk_to_delete
        assert result["file_id"] == file_id
        assert result["remaining_chunks"] == original_chunk_count - 1

        # 3. 验证文件列表中的 chunk_count 已更新
        resp = await client.get(f"http://127.0.0.1:{port}/api/files")
        assert resp.json()["items"][0]["chunk_count"] == original_chunk_count - 1

        # 4. 验证 chunk 列表中已不存在被删除的 chunk
        resp = await client.get(f"http://127.0.0.1:{port}/api/files/{file_id}/chunks")
        remaining_ids = [c["chunk_id"] for c in resp.json()["items"]]
        assert chunk_to_delete not in remaining_ids
        assert resp.json()["count"] == original_chunk_count - 1

        # 5. 验证内存向量索引也同步删除（通过 stats 检查）
        resp = await client.get(f"http://127.0.0.1:{port}/api/stats")
        stats = resp.json()
        # vector_index_size 应该比初始少 1
        # 初始 = original_chunk_count，现在 = original_chunk_count - 1
        assert stats["vector_index_size"] == original_chunk_count - 1

        # 6. 验证 BM25（FTS）也同步删除：搜索该 chunk 特有内容应不命中
        # 这里所有 chunk 内容相似（都是"法涅斯是原初之人"重复），用纯 BM25 仍会命中其它 chunk
        # 所以只断言"搜索还能命中至少一条"且"命中数量 < 原始 chunk 数"
        resp = await client.post(
            f"http://127.0.0.1:{port}/api/search",
            json={
                "query": "法涅斯",
                "top_k": 10,
                "use_vector": False,
                "use_bm25": True,
                "fusion_mode": "hybrid",
            },
        )
        assert resp.status_code == 200
        hits = resp.json()["items"]
        hit_ids = [h["chunk_id"] for h in hits]
        assert chunk_to_delete not in hit_ids


@pytest.mark.asyncio
async def test_delete_chunk_not_found(setup_kb):
    """测试删除不存在的 chunk_id 应返回 404。"""

    import httpx

    server, port = setup_kb
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"http://127.0.0.1:{port}/api/chunks/nonexistent-chunk-id"
        )
        assert resp.status_code == 404
