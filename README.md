# MaiBot AstrBot DB Port Plugin

把 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的数据库设计**整体移植**到 MaiBot 插件运行时，并扩展了独立的 **知识库 RAG 模块**（通用文本向量化作为 LLM 外置知识库）。

> 解决的核心痛点：
>
> 1. **MaiBot 插件 SDK 无存储抽象** — 只允许插件通过 `self.ctx.db.*` 操作 host 预定义的 22 张表，不允许注册自己的表。本插件用 AstrBot 经过生产验证的方案（SQLModel + 异步 DAO + 万能 KV 表）作为独立 SQLite 文件填这个空缺。
>
> 2. **A_memorix 不适合做结构化知识库** — 它是为聊天机器人记忆设计的：滑动窗口硬切、LLM 自由抽取关系导致混乱、`chat_scope` 过滤让脚本导入的内容对所有聊天不可见。本插件的 KB 模块完全重写：按 markdown 标题语义切分、不抽取关系只存原文、混合检索（向量 + BM25 + RRF）。

## 两个核心模块

### 模块一：AstrBot 数据库移植（v1.0）

- 18 张表（含 `conversations` / `preferences` 万能 KV / `personas` / `cron_jobs` 等）
- 异步 DAO + 三层 KV API + 自研幂等迁移
- 15 个 `@API` 供其他插件调用

### 模块二：知识库 RAG（v2.0 新增）★

把任意 markdown / txt 文档（小说、游戏设定、世界观、技术文档）向量化，作为 LLM 的外置知识库。

- **Markdown 语义切分**：按 `#`/`##`/`###` 标题层级切分，保留章节路径，不做字符数硬切
- **混合检索**：向量（numpy cosine）+ BM25（SQLite FTS5 trigram）+ RRF 融合
- **零外部依赖**：纯 numpy + SQLite，不需要 FAISS / Chroma / Qdrant
- **8 个 KB API** + **1 个 LLM Tool** `knowledge_search`（让 Bot 在对话中主动检索）
- **增量更新**：基于 `file_hash` 自动跳过未变更文件
- **多种 embedding 后端**：MaiBot 自带 / OpenAI 兼容 / 哑元（测试）

> **真实知识库验证**：用 55 个原神设定文件（982 KB）测试，全部成功导入为 1211 个 chunks，12 个测试查询（"法涅斯"/"尼伯龙根"/"世界树"/"降临者"/"桑多涅"等）全部能检索到相关段落。详见 [验证脚本](tests/verify_genshin_kb.py)

## 设计来源

| 来源 | 用途 |
|---|---|
| AstrBot `astrbot/core/db/po.py` | 17 张表的结构（含 TimestampMixin、UMO 字符串、双 ID 设计） |
| AstrBot `astrbot/core/db/sqlite.py` | 异步 DAO 类、PRAGMA 调优套餐、`_ensure_xxx_column` 幂等列补齐 |
| AstrBot `astrbot/core/utils/shared_preferences.py` | 三层 KV API（global / umo / plugin scope） |
| AstrBot `astrbot/core/db/migration/` | 自研迁移机制（用 preferences 表自身记录迁移状态） |
| MaiBot Plugin SDK 2.x | `MaiBotPlugin` 基类、`@API` / `@Command` 装饰器、`PluginPaths` |

## 功能概览

- ✅ **18 张表**（移植自 AstrBot 17 张 + 自增 1 个迁移标记），完整 SQLModel 定义
- ✅ **异步 DAO**：基于 SQLAlchemy[asyncio] + aiosqlite，单文件 SQLite + WAL + 完整 PRAGMA 调优
- ✅ **三层 KV**：`global` / `umo`(会话级) / `plugin`(插件私有) 三个 scope，自动 upsert
- ✅ **自研迁移**：装饰器注册迁移函数，幂等执行，迁移状态存到 preferences 表自身
- ✅ **15 个公开 API**：通过 `self.ctx.api.call('astrdb.kv.put', ...)` 供其他插件调用
- ✅ **管理命令** `/adb`：stats / tables / backup / export
- ✅ **AstrBot 数据导入器**：一键从 `data_v4.db` 迁移历史数据
- ✅ **27 个单元测试 + 集成测试**：覆盖 CRUD / KV 三层 scope / 迁移幂等 / API 端到端调用

## 目录结构

```
maibot-astrbot-db/
├── _manifest.json          # MaiBot 插件清单
├── plugin.py               # 插件入口：on_load/on_unload/@API/@Command
├── requirements.txt        # 依赖：sqlmodel + aiosqlite + sqlalchemy
├── pytest.ini              # 测试配置
├── astrdb/                 # 核心数据库模块
│   ├── __init__.py         # 全局单例 init_db/get_db/sp
│   ├── models.py           # 18 张 SQLModel 表定义
│   ├── database.py         # AstrBotDatabase 异步 DAO 类
│   ├── preferences.py      # SharedPreferences 三层 KV
│   └── migrations/
│       ├── __init__.py
│       └── manager.py      # 迁移注册与执行
├── commands/               # 命令处理（占位，实际在 plugin.py）
├── importers/
│   └── astrbot_importer.py # 从 AstrBot data_v4.db 导入
└── tests/                  # 27 个 pytest 测试
    ├── conftest.py
    ├── test_models.py
    ├── test_kv.py
    ├── test_conversations.py
    ├── test_migrations.py
    ├── test_stats.py
    └── test_integration.py
```

## 安装

### 1. 复制插件到 MaiBot plugins 目录

```bash
cp -r maibot-astrbot-db /path/to/MaiBot/plugins/
```

### 2. 安装 Python 依赖

```bash
pip install sqlmodel>=0.0.24 aiosqlite>=0.21.0 'sqlalchemy[asyncio]>=2.0.41'
```

或者依赖 MaiBot 的 `pyproject.toml` 自动安装（`_manifest.json` 已声明 `dependencies`）。

### 3. 启动 MaiBot

启动后插件会自动：
- 在 `data/plugins/maibot-team.astrbot-db-port/astrbot.db` 创建数据库
- 跑幂等迁移
- 暴露 15 个 API 给其他插件

## 配置

插件配置在 `data/plugins/maibot-team.astrbot-db-port/config.toml`：

```toml
[database]
config_version = "1.0.0"
enabled = true
db_filename = "astrbot.db"
auto_backup_on_start = false

[admin]
config_version = "1.0.0"
admin_users = ["aiocqhttp:123456789"]  # 允许使用 /adb 命令的用户
```

## 数据库表清单

| 表名 | 用途 | 来源 |
|---|---|---|
| `conversations` | LLM 对话历史（OpenAI 消息数组） | AstrBot ConversationV2 |
| `preferences` ★ | **万能 KV 表** (scope, scope_id, key, value:JSON) | AstrBot Preference |
| `platform_message_history` | 平台消息历史 | AstrBot PlatformMessageHistory |
| `platform_sessions` | 平台会话 | AstrBot PlatformSession |
| `personas` / `persona_folders` | LLM 人格定义与文件夹 | AstrBot Persona |
| `cron_jobs` | 定时任务 | AstrBot CronJob |
| `platform_stats` | 平台消息统计（按时间桶） | AstrBot PlatformStat |
| `provider_stats` | LLM Provider 调用统计（token 用量） | AstrBot ProviderStat |
| `umo_aliases` | UMO 字符串到友好名映射 | AstrBot UmoAlias |
| `attachments` | 文件附件元数据 | AstrBot Attachment |
| `api_keys` / `dashboard_trusted_devices` | API Key 与可信设备 | AstrBot |
| `chatui_projects` / `session_project_relations` | ChatUI 项目 | AstrBot |
| `command_configs` / `command_conflicts` | 命令注册与冲突 | AstrBot |
| `webchat_threads` | WebChat 线程 | AstrBot |

## 对外 API

其他插件通过 MaiBot SDK 调用：

```python
# 写入 KV
await self.ctx.api.call(
    "astrdb.kv.put",
    version="1",
    scope="plugin",
    scope_id="my-plugin-id",
    key="counter",
    value=42,
)

# 读取 KV
val = await self.ctx.api.call(
    "astrdb.kv.get",
    version="1",
    scope="plugin",
    scope_id="my-plugin-id",
    key="counter",
    default=0,
)

# 创建对话
result = await self.ctx.api.call(
    "astrdb.conv.create",
    version="1",
    platform="aiocqhttp",
    message_type="GroupMessage",
    session_id="123456",
    title="技术讨论",
)
# → {"conversation_id": "...", "user_id": "aiocqhttp:GroupMessage:123456", ...}
```

### API 完整列表

| API 名称 | 描述 |
|---|---|
| `astrdb.kv.get` | 读取 KV（支持 default 参数） |
| `astrdb.kv.put` | 写入 KV（upsert） |
| `astrdb.kv.delete` | 删除 KV |
| `astrdb.kv.list` | 列出某 scope 下所有 KV（支持前缀过滤） |
| `astrdb.conv.create` | 创建对话 |
| `astrdb.conv.get` | 按 ID 获取对话 |
| `astrdb.conv.list` | 按 UMO 列出对话 |
| `astrdb.conv.update_content` | 更新对话内容 |
| `astrdb.conv.delete` | 删除对话 |
| `astrdb.persona.list` | 列出人格 |
| `astrdb.persona.get` | 获取人格详情 |
| `astrdb.msg.add` | 追加消息历史 |
| `astrdb.msg.list` | 列出消息历史 |
| `astrdb.stats.count` | 统计表行数 |
| `astrdb.stats.incr_platform` | 自增平台消息统计 |

## 管理命令

```
/adb                  显示帮助
/adb stats            显示各表行数
/adb tables           列出所有表名
/adb backup           手动备份数据库
/adb export <table>   导出某张表前 100 行为 JSON
```

需要在 `config.toml` 的 `[admin].admin_users` 中配置 `platform:user_id` 才能使用。

## 从 AstrBot 导入历史数据

如果你之前在用 AstrBot，想把 `data_v4.db` 的数据搬到本插件：

```bash
cd /path/to/MaiBot/plugins/maibot-astrbot-db
python -m importers.astrbot_importer \
    --src /path/to/AstrBot/data/data_v4.db \
    --dst /path/to/MaiBot/data/plugins/maibot-team.astrbot-db-port/astrbot.db
```

支持的表：`platform_stats`、`provider_stats`、`conversations`、`persona_folders`、`personas`、`cron_jobs`、`preferences`、`platform_message_history`、`webchat_threads`、`platform_sessions`、`umo_aliases`、`attachments`、`command_configs`、`command_conflicts`。

字段对齐策略：源库可能缺本插件新增的列，按交集导入；自增主键会被跳过，避免冲突。

## 关键设计模式（移植自 AstrBot）

### 1. UMO 字符串作为跨平台身份

```python
from astrdb import build_umo, parse_umo

umo = build_umo("aiocqhttp", "GroupMessage", "123456789")
# → "aiocqhttp:GroupMessage:123456789"

platform, msg_type, session_id = parse_umo(umo)
```

不维护独立的用户表，所有跨平台身份都用 `platform:type:session_id` 字符串表达。

### 2. 万能 KV 表

```python
class Preference:
    scope: str       # 'global' | 'umo' | 'plugin' | 'migration'
    scope_id: str    # 'global' | UMO | plugin_id
    key: str
    value: dict      # JSON，业务值放在 value["val"]
    # UNIQUE (scope, scope_id, key)
```

一张表搞定全局配置、会话配置、插件数据、迁移标记。

### 3. 双 ID 设计

```python
class ConversationV2:
    inner_conversation_id: int   # 自增 int 主键，便于内部索引
    conversation_id: str         # UUID 字符串，对外稳定
```

### 4. SQLite PRAGMA 调优套餐

```python
PRAGMA journal_mode=WAL         # 多读单写不阻塞
PRAGMA busy_timeout=30000       # 30s 锁等待
PRAGMA synchronous=NORMAL
PRAGMA cache_size=20000         # ~80MB
PRAGMA temp_store=MEMORY
PRAGMA mmap_size=134217728      # 128MB
PRAGMA optimize
```

### 5. 幂等列补齐

每次启动都跑 `PRAGMA table_info` → 缺列就 `ALTER TABLE ADD COLUMN`，和迁移脚本形成双保险。

### 6. 用 preferences 表自身做迁移日志

迁移完成标记存到 `preferences(scope='migration', scope_id='global', key='migration_done_xxx', value={"val": true})`，无需单独的 `schema_migrations` 表。

## 测试

```bash
cd maibot-astrbot-db
pip install sqlmodel aiosqlite 'sqlalchemy[asyncio]' pytest pytest-asyncio
pytest -v
```

预期输出：`27 passed`。

测试覆盖：
- `test_models.py` — UMO 构造/解析/往返、模型默认值
- `test_kv.py` — 三层 scope KV、upsert 幂等、复杂 JSON 值、迁移标记
- `test_conversations.py` — 对话 CRUD、按 UMO 隔离
- `test_migrations.py` — 迁移注册、幂等执行、列补齐
- `test_stats.py` — 平台统计原子自增、不同桶隔离
- `test_integration.py` — 端到端：通过模拟 API 调用走完插件链路

## 示例调用插件

仓库 `maibot-astrbot-db-demo/` 提供了一个最小示例插件，演示：

- `/demo kv <key> [value]` — 读写 KV
- `/demo conv create <title>` — 创建对话
- `/demo conv list` — 列出当前用户的所有对话
- `/demo stats` — 查看数据库统计

直接作为 MaiBot 插件放到 `plugins/` 下即可运行。

## 许可证

GPL-v3.0-or-later（与 MaiBot 主仓库一致）。

---

# 知识库 RAG 模块使用指南

## 快速开始

### 1. 准备知识库源文件

把你的 markdown / txt 文件放到插件 `data_dir` 下的 `knowledge_base/` 目录：

```
data/plugins/maibot-team.astrbot-db-port/
├── astrbot.db              # 数据库文件（自动创建）
├── config.toml             # 插件配置
└── knowledge_base/         # ← 把 .md/.txt 文件放这里
    ├── 00_提瓦特总史.md
    ├── 01c_蒙德_第二幕_月宫与葬火.md
    ├── ...
    └── 桑多涅角色设定_完整.md
```

支持嵌套子目录。所有 `.md` / `.markdown` / `.txt` 文件都会被自动扫描。

### 2. 配置 embedding 服务

编辑 `config.toml`，在 `[knowledge_base]` section 选一种 embedding 提供方：

```toml
[knowledge_base]
enabled = true
knowledge_dir = "knowledge_base"
auto_ingest_on_start = true

# 方式 A（推荐）：用 MaiBot 自己的 embedding 服务
embedding_provider = "maibot"
embedding_model = "text-embedding-3-small"  # 取决于 MaiBot 配置
embedding_dimension = 1536                    # 必须与模型实际维度一致

# 方式 B：用 OpenAI 兼容接口
# embedding_provider = "openai"
# embedding_model = "text-embedding-3-small"
# embedding_dimension = 1536
# embedding_api_key = "sk-..."
# embedding_base_url = "https://api.openai.com/v1"  # 可换 DeepSeek/Moonshot/智谱

# 方式 C：哑元（仅测试，检索质量很差）
# embedding_provider = "dummy"
# embedding_dimension = 256

target_chars = 500   # 目标 chunk 字符数
max_chars = 1500     # 单 chunk 最大字符数
min_chars = 80       # 最小 chunk 字符数
default_category = "genshin"  # 给所有文件打 category 标签
```

### 3. 启动 MaiBot

启动时插件会自动：
1. 创建数据库 + FTS5 表
2. 从数据库加载已有向量到内存索引
3. 扫描 `knowledge_base/` 目录
4. 增量导入新文件：切分 → embedding → 入库 → 加入内存索引

之后 MaiBot 在对话中会自动调用 `knowledge_search` tool 检索知识库。

## 检索 API

其他插件或 MaiBot 主程序通过 `self.ctx.api.call(...)` 调用：

```python
# 混合检索（推荐）
result = await self.ctx.api.call(
    "astrdb.kb.search",
    version="1",
    query="法涅斯是谁",
    top_k=5,
)
# → {
#     "success": true,
#     "query": "法涅斯是谁",
#     "count": 5,
#     "items": [
#       {
#         "chunk_id": "...",
#         "score": 0.0317,
#         "content": "法涅斯是原初之人之一...",
#         "heading": "法涅斯的诞生",
#         "title_path": ["蒙德", "第二幕", "月宫与葬火", "法涅斯的诞生"],
#         "file_id": "...",
#         "source_name": "01c_蒙德_第二幕_月宫与葬火.md",
#         "vector_score": 0.21,
#         "bm25_score": 1.12,
#       },
#       ...
#     ]
#   }

# 仅向量检索（语义相似）
result = await self.ctx.api.call(
    "astrdb.kb.search_vector",
    version="1",
    query="提瓦特创世神话",
    top_k=5,
)

# 仅 BM25 检索（关键词命中）
result = await self.ctx.api.call(
    "astrdb.kb.search_bm25",
    version="1",
    query="尼伯龙根",
    top_k=5,
)

# 按 category 过滤
result = await self.ctx.api.call(
    "astrdb.kb.search",
    version="1",
    query="钟离的过去",
    category="genshin",
    top_k=5,
)
```

## LLM Tool: knowledge_search

插件自动注册了一个 LLM Tool `knowledge_search`，MaiBot 的 LLM 在对话中可以主动调用：

```
用户: 法涅斯是谁？
MaiBot LLM: [调用 knowledge_search(query="法涅斯是谁")]
KB 模块: 返回 5 条最相关的段落（含来源、章节路径、相关度）
MaiBot LLM: 根据检索结果回答："法涅斯是原神世界观中的原初之人..."
```

Tool 描述已配置为"当用户询问世界观、剧情、角色、设定相关问题时调用"。

## 管理 API

```python
# 列出所有已入库文件
await self.ctx.api.call("astrdb.kb.list_files", version="1")

# 仅列出失败的
await self.ctx.api.call("astrdb.kb.list_files", version="1", status="failed")

# 知识库统计
await self.ctx.api.call("astrdb.kb.stats", version="1")
# → {"files_total": 55, "files_ready": 55, "chunks_total": 1211, "tokens_total": 289576, ...}

# 手动触发增量导入
await self.ctx.api.call("astrdb.kb.ingest_directory", version="1")

# 强制全量重建
await self.ctx.api.call(
    "astrdb.kb.ingest_directory", version="1", force_rebuild=True
)

# 删除某文件及其 chunks
await self.ctx.api.call(
    "astrdb.kb.delete_file", version="1", file_id="..."
)

# 重新加载内存索引
await self.ctx.api.call("astrdb.kb.reload_index", version="1")
```

## 切分策略

与 A_memorix 的滑动窗口硬切完全不同：

| 维度 | A_memorix | 本插件 |
|---|---|---|
| 切分单位 | 1600 字符滑动窗口 | markdown 标题章节 |
| 标题感知 | 仅识别 `#` 作为场景分隔 | 完整保留 `#`/`##`/`###` 层级路径 |
| 段落边界 | 不感知，硬切 | 按双换行分段，累积到目标大小输出 |
| 重叠 | 400 字符重叠（重复存储） | 不重叠，仅在超长段落硬切时考虑句号 |
| 关系抽取 | LLM 自由生成三元组（混乱） | 不抽取，直接存原文 |
| 检索过滤 | chat_scope 过滤（导入数据不可见） | 无过滤，全局可见 |

### chunk 示例

原始 markdown：

```markdown
# 蒙德

## 第二幕 月宫与葬火

法涅斯是原初之人之一。他降临提瓦特，创造了人类。

### 法涅斯的诞生

法涅斯从蛋中诞生，是第一个原初之人。
```

切分结果：

```
Chunk 0:
  heading: "第二幕 月宫与葬火"
  title_path: ["蒙德", "第二幕", "月宫与葬火"]
  content: "法涅斯是原初之人之一。他降临提瓦特，创造了人类。"

Chunk 1:
  heading: "法涅斯的诞生"
  title_path: ["蒙德", "第二幕", "月宫与葬火", "法涅斯的诞生"]
  content: "法涅斯从蛋中诞生，是第一个原初之人。"
```

`title_path` 在检索结果中返回，LLM 可以引用"这条信息来自《蒙德》第二幕《月宫与葬火》的法涅斯的诞生小节"，提高回答可信度。

## 检索算法

### 向量检索

- 模型：用户配置（默认 `text-embedding-3-small` 1536 维）
- 存储：SQLite BLOB 字段（`numpy.float32.tobytes()`）
- 索引：启动时全部加载到内存（1 万 chunk × 1024 维 ≈ 40MB）
- 检索：numpy 矩阵乘法（cosine similarity），暴力但极快
- 归一化：查询向量和库向量都归一化，dot product 即 cosine

### BM25 检索

- 引擎：SQLite FTS5（虚拟表 `kb_chunks_fts`）
- 分词器：`trigram`（SQLite 3.34+ 自带，对中文友好）
  - 把文本按 3-gram 切分，可以匹配任意 ≥3 字符的子串
  - 例如 "法涅斯" 会建立 ["法涅斯", "涅斯"] 等三元组
- 短查询兜底：查询 < 3 字符时回退 `LIKE '%query%'`
- 排序：BM25 分数（越小越好，取负数转成越大越好）

### RRF 融合

```
score(d) = sum( 1 / (k + rank_i(d)) )  for each retriever i
```

- `k = 60`（标准值）
- 只用排名，不用原始分数（避免两路分数尺度不一致）
- 同时被两路检索召回的文档得分更高

## 性能参考

基于真实原神知识库（55 文件 / 1211 chunks / 256 维 dummy embedding）：

| 操作 | 耗时 |
|---|---|
| 首次导入（切分 + 哈希 embedding + 入库） | ~5 秒 |
| 启动时加载索引到内存 | < 1 秒 |
| 单次混合检索 | < 50 ms |
| 增量扫描（无变更） | < 100 ms |

真实 embedding 服务（OpenAI / MaiBot）的耗时取决于 API 调用，55 文件 1211 chunks 按 16 batch 大约需要 1-3 分钟。

## 常见问题

### Q: 用 MaiBot embedding 报错 "无法获取 self.ctx.llm.embed"

A: MaiBot 插件 SDK 2.0+ 才有 `llm.embed` 能力。请检查 `_manifest.json` 的 `sdk.min_version` 和 `capabilities` 是否包含 `llm.embed`。本插件的 manifest 已经声明了。

### Q: 检索结果不相关

A: 检查 `astrdb.kb.stats` API 返回的 `embedding_model` 和 `embedding_dimension`：
- 如果是 `dummy` 模型，检索质量必然很差（哈希伪随机向量没有语义能力）
- 必须配置 `embedding_provider = "maibot"` 或 `"openai"` 使用真实 embedding 服务

### Q: 中文短查询（2 字以下）检索不到

A: trigram 分词器要求查询 ≥ 3 字符。短查询会自动回退 `LIKE` 兜底，但只能精确匹配。建议查询时多写几个字（"温迪" → "温迪的故事"）。

### Q: 文件更新后没重新导入

A: 增量导入基于 `file_hash`。确认文件确实改了内容（不只是 mtime）。也可以手动调 `astrdb.kb.ingest_directory` API 强制扫描，或 `force_rebuild=True` 全量重建。

### Q: embedding 失败但 chunks 入库了

A: 这是设计行为 — chunks 入库后即使 embedding 失败也能被 BM25 检索到。文件状态会标记为 `failed`，可以在 `astrdb.kb.list_files` 里看到错误信息。修复 embedding 服务后调 `force_rebuild=True` 重新嵌入。

