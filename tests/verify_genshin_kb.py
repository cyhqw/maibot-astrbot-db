"""端到端验证：用真实原神知识库测试 KB 模块

直接运行：python tests/verify_genshin_kb.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# 让脚本能找到 astrdb 包
sys.path.insert(0, str(Path(__file__).parent.parent))

from astrdb import close_db, get_db, init_db
from astrdb.kb import (
    DummyEmbedder,
    HybridSearcher,
    KnowledgeBaseImporter,
    SearchQuery,
    VectorIndex,
)


KB_DIR = Path(__file__).parent / "kb_data"


async def main():
    print("=" * 70)
    print("原神知识库 RAG 端到端验证")
    print("=" * 70)
    print(f"知识库目录: {KB_DIR}")
    print(f"文件数: {len(list(KB_DIR.glob('*.md')))}")
    print(f"总大小: {sum(f.stat().st_size for f in KB_DIR.glob('*.md')) / 1024:.1f} KB")
    print()

    # 初始化数据库（临时文件）
    tmpdir = tempfile.mkdtemp(prefix="astrdb_genshin_")
    db_path = os.path.join(tmpdir, "genshin.db")
    print(f"数据库: {db_path}")
    await init_db(db_path)
    db = get_db()

    # 初始化 KB（用 DummyEmbedder，256 维）
    # 注意：真实使用时应配置 MaiBot embedder 或 OpenAI 兼容 embedder
    # DummyEmbedder 用哈希生成确定性向量，能演示流程但语义检索质量较差
    embedder = DummyEmbedder(dimension=256, model_name="dummy-test")
    index = VectorIndex()
    importer = KnowledgeBaseImporter(
        db, index, embedder, KB_DIR,
        target_chars=500,
        max_chars=1500,
        min_chars=80,
        default_category="genshin",
    )

    print("\n[1/3] 导入知识库...")
    result = await importer.ingest_directory()
    print(f"  扫描: {result.scanned} 个文件")
    print(f"  新增: {result.new}")
    print(f"  更新: {result.updated}")
    print(f"  跳过: {result.unchanged}")
    print(f"  失败: {result.failed}")
    print(f"  总 chunks: {result.chunks}")
    print(f"  内存索引大小: {index.size}")
    if result.failures:
        print("  失败详情:")
        for fp, err in result.failures[:5]:
            print(f"    {fp}: {err}")

    print("\n[2/3] 验证检索...")
    searcher = HybridSearcher(db, index, embedder)

    test_queries = [
        "法涅斯是谁",
        "尼伯龙根",
        "提瓦特七国",
        "温迪",
        "钟离",
        "雷电将军",
        "500年前的漆黑灾祸",
        "世界树",
        "降临者",
        "魔神战争",
        "坎瑞亚",
        "桑多涅",
    ]

    for q in test_queries:
        hits = await searcher.search(SearchQuery(query=q, top_k=3))
        print(f"\n  查询: {q!r}")
        print(f"  结果: {len(hits)} 条")
        for i, h in enumerate(hits, 1):
            title_path = " > ".join(h.title_path) if h.title_path else "<无标题>"
            print(f"    {i}. [{h.source_name}] {title_path}")
            print(f"       score={h.score:.4f} vec={h.vector_score:.4f} bm25={h.bm25_score:.4f}")
            # 截取前 100 字
            preview = h.content[:100].replace("\n", " ")
            print(f"       内容: {preview}...")

    print("\n[3/3] 统计...")
    stats_files = await db.list_kb_files()
    ready = [f for f in stats_files if f.status == "ready"]
    failed = [f for f in stats_files if f.status == "failed"]
    total_chunks = sum(f.chunk_count for f in ready)
    total_tokens = sum(f.total_tokens for f in ready)
    print(f"  文件总数: {len(stats_files)}")
    print(f"  成功: {len(ready)}, 失败: {len(failed)}")
    print(f"  chunks: {total_chunks}")
    print(f"  tokens (估算): {total_tokens}")
    print(f"  向量索引: {index.size} 个 {embedder.dimension} 维向量")

    await close_db()
    print("\n✅ 验证完成")


if __name__ == "__main__":
    asyncio.run(main())
