# Changelog

## 2.0.0 (2026-07-16)

**重大升级**：新增独立的知识库 RAG 模块 — 通用文本（小说/游戏/世界观设定）向量化作为 LLM 外置知识库。

针对 A_memorix 在结构化知识库场景的三大痛点（滑动窗口硬切、LLM 自由抽取关系混乱、chat_scope 过滤导致检索失败），本模块完全重写：

- **按 markdown 标题语义切分** — 保留 `#`/`##`/`###` 标题层级路径，不做字符数硬切
- **不抽取关系** — 直接存原文 chunks + embedding，避免 LLM 自由抽取的混乱
- **无 chat_scope 过滤** — 知识库就是全局可见的，导入即可被任何会话检索到
- **混合检索** — 向量（numpy cosine）+ BM25（SQLite FTS5 trigram）+ RRF 融合

### 新增功能

- **数据模型**（2 张新表）
  - `kb_files` — 文件元数据（路径、hash、状态、chunk 数、tokens）
  - `kb_chunks` — 切块原文 + embedding（BLOB numpy float32）+ 标题路径

- **FTS5 全文检索**
  - 使用 `trigram` 分词器（SQLite 3.34+），对中文友好
  - 短查询（< 3 字符）回退 LIKE 兜底
  - BM25 分数排序

- **Markdown 语义切分器** `kb/chunker.py`
  - 按 `#` 标题切分章节，保留层级路径
  - 章节内按段落（双换行）累积到目标大小
  - 单段落超长按句号硬切
  - 短尾部 chunk 自动合并到上一个

- **Embedding 抽象层** `kb/embedder.py`
  - `MaiBotEmbedder` — 走 MaiBot `self.ctx.llm.embed`（推荐，零配置）
  - `OpenAICompatibleEmbedder` — 兼容 OpenAI / DeepSeek / Moonshot / 智谱
  - `DummyEmbedder` — 哈希伪随机向量，仅测试用

- **内存向量索引** `kb/vector_store.py`
  - 基于 numpy 矩阵乘法的 cosine 检索
  - 启动时从 SQLite BLOB 加载到内存
  - 增量更新（add/remove）
  - 1 万 chunk × 1024 维 ≈ 40MB 内存

- **混合检索** `kb/search.py`
  - 向量检索 + BM25 检索并行
  - RRF（Reciprocal Rank Fusion）融合两路结果
  - 可分别控制 use_vector / use_bm25
  - 支持 category / file_ids 过滤

- **批量导入器** `kb/importer.py`
  - 扫描目录所有 .md / .txt 文件
  - 增量更新：基于 file_hash 判断变更
  - 自动切分 + embedding + 入库 + 内存索引同步
  - `force_rebuild=True` 强制全量重建

- **8 个 KB 公开 API**
  - `astrdb.kb.ingest_directory` — 批量扫描目录导入
  - `astrdb.kb.ingest_file` — 单文件导入
  - `astrdb.kb.search` — 混合检索（推荐）
  - `astrdb.kb.search_vector` — 仅向量检索
  - `astrdb.kb.search_bm25` — 仅 BM25 检索
  - `astrdb.kb.list_files` — 列出已入库文件
  - `astrdb.kb.delete_file` — 删除某文件及其 chunks
  - `astrdb.kb.stats` — 知识库统计
  - `astrdb.kb.reload_index` — 重载内存索引

- **LLM Tool** `knowledge_search`
  - 让 MaiBot 在对话中主动调用知识库检索
  - 当用户询问世界观/剧情/角色/设定时自动触发
  - 返回格式化文本供 LLM 引用

- **配置**
  - `[knowledge_base]` section 控制：启用、目录、切分参数、embedding 提供方
  - 启动时自动增量导入新文件（可关闭）

### 端到端验证

用真实原神知识库（55 个 markdown 文件，982 KB）验证：
- 导入：55 个文件全部成功，切分出 1211 个 chunks，约 29 万 tokens
- 检索：12 个测试查询全部能找到相关结果
  - "法涅斯是谁" → 命中提瓦特总史第三幕
  - "尼伯龙根" → 命中祷歌 + 总史"提瓦特最初的主人"
  - "世界树" → BM25 分数 8.42 命中基础设定文件
  - "降临者" → BM25 分数 8.73 命中降临者一览表
  - "桑多涅" → 命中至冬第六幕"木偶加入愚人众，成为桑多涅"

### 测试

- **47 个 pytest 测试全部通过**（27 原有 + 20 KB 新增）
  - test_kb_chunker.py — 切分逻辑（10 个测试）
  - test_kb.py — 端到端集成（10 个测试）

---

## 1.0.0 (2026-07-16)

首次发布 — 完整移植 AstrBot 数据库设计到 MaiBot 插件运行时。

### 新增

- **18 张表**：移植自 AstrBot `astrbot/core/db/po.py`
  - `conversations`、`preferences`、`platform_message_history`、`platform_sessions`
  - `personas`、`persona_folders`、`cron_jobs`
  - `platform_stats`、`provider_stats`
  - `umo_aliases`、`attachments`、`api_keys`、`dashboard_trusted_devices`
  - `chatui_projects`、`session_project_relations`
  - `command_configs`、`command_conflicts`、`webchat_threads`

- **异步 DAO** `AstrBotDatabase` 类
  - 基于 SQLAlchemy[asyncio] + aiosqlite
  - 完整 PRAGMA 调优套餐（WAL / busy_timeout / mmap_size 等）
  - `get_db()` 上下文管理器 + `_run_in_tx` 事务包装
  - 幂等 `_ensure_xxx_column` 列补齐

- **SharedPreferences 三层 KV API**
  - `global_get/put/remove` — 全局配置
  - `session_get/put/remove` — 按 UMO 隔离的会话配置
  - `plugin_get/put/remove/list` — 插件私有数据
  - `is_migration_done/mark_migration_done` — 迁移标记

- **自研幂等迁移框架**
  - `@register_migration` 装饰器
  - `run_migrations` 自动跳过已完成的迁移
  - 迁移状态存到 `preferences` 表自身

- **15 个公开 API**（通过 `@API` 装饰器暴露）
  - `astrdb.kv.{get,put,delete,list}`
  - `astrdb.conv.{create,get,list,update_content,delete}`
  - `astrdb.persona.{list,get}`
  - `astrdb.msg.{add,list}`
  - `astrdb.stats.{count,incr_platform}`

- **管理命令** `/adb`
  - `stats` — 显示各表行数
  - `tables` — 列出所有表名
  - `backup` — 手动备份
  - `export <table>` — 导出某张表前 100 行为 JSON

- **AstrBot 数据导入器**
  - `python -m importers.astrbot_importer --src ... --dst ...`
  - 支持从 AstrBot `data_v4.db` 一键迁移 14 张表

- **示例调用插件** `maibot-astrbot-db-demo`
  - 演示如何通过 `self.ctx.api.call(...)` 调用本插件

- **测试覆盖**
  - 27 个 pytest 测试（含 3 个端到端集成测试）
  - 全部通过
