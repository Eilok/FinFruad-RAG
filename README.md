# FinFraud-RAG

金融诈骗风险治理系统（前后端分离，持续积累诈骗知识）。

## 阶段进度

- [x] 阶段01：项目初始化与骨架搭建
- [x] 阶段02：离线知识库构建流水线
- [ ] 阶段03：在线双检索与判别服务
- [ ] 阶段04：前端页面与交互集成
- [ ] 阶段05：自动化评估与实验日志
- [ ] 阶段06：统一交付与可运维性完善

## 当前项目结构（阶段02）

```text
.
├─ backend/
│  ├─ app.py
│  ├─ core/
│  │  ├─ health.py
│  │  ├─ ingest.py
│  │  ├─ logging_utils.py
│  │  └─ settings.py
│  ├─ models/
│  │  ├─ api.py
│  │  └─ knowledge.py
│  ├─ providers/
│  │  ├─ embedding_client.py
│  │  └─ llm_client.py
│  ├─ scripts/
│  │  └─ ingest_kb.py
│  ├─ service/
│  │  ├─ health.py
│  │  └─ kb.py
│  └─ storage/
│     └─ chroma_store.py
├─ data/
├─ webui/
├─ AGENTS.md
├─ SPECS/
├─ pyproject.toml
└─ .env.example
```

说明：`backend/service` 仅放接口层代码，离线构建流程在 `backend/core`。

## 环境准备

1. Python 3.12+
2. Node.js 18+
3. `uv`

## 安装依赖

### 后端（uv）

```bash
uv sync
```

### 前端（npm）

```bash
cd webui
npm install
```

## 配置环境变量

复制并填写：

```bash
cp .env.example .env
```

关键变量：
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`（OpenAI SDK 兼容）
- `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` / `EMBEDDING_MODEL`（硅基流动 embedding）
- `CHROMA_PERSIST_DIR` / `CHROMA_COLLECTION_NAME`

## 启动后端

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

健康检查：

```bash
curl http://localhost:8000/healthz
```

## 阶段02：离线知识库构建

### A. API 方式导入

接口：`POST /kb/ingest`

请求示例：

```json
{
  "items": [
    {
      "text": "兼职刷单日赚千元，无需经验，先垫付后返还。",
      "source": "manual"
    }
  ],
  "retry_times": 2
}
```

返回示例：

```json
{
  "total": 1,
  "success": 1,
  "failed": 0,
  "results": [
    {
      "record_id": "uuid",
      "source": "manual",
      "summary": "...",
      "category": "招聘诈骗",
      "risk_keywords": ["刷单", "垫付", "高收益"]
    }
  ],
  "errors": []
}
```

### B. CLI 方式导入

单条文本：

```bash
uv run python -m backend.scripts.ingest_kb --text "高薪兼职无需经验，先交保证金" --source manual
```

批量文件（jsonl 或纯文本逐行）：

```bash
uv run python -m backend.scripts.ingest_kb --input-file data/sample_ingest.jsonl --source dataset --retry-times 2
```

jsonl 行格式示例：

```json
{"text":"高收益理财稳赚不赔，立即转账抢名额","source":"job_scams"}
```

## 阶段02测试方法

### 测试1：结构化抽取字段完整性

- 调用 `POST /kb/ingest` 导入单条诈骗文本。
- 检查返回 `summary/category/risk_keywords` 是否存在。

### 测试2：摘要向量化与入库

- 导入后检查目录 `CHROMA_PERSIST_DIR` 已产生数据文件。
- 再次导入不同文本，确认 `record_id` 不同且成功数增长。

### 测试3：构建日志

- 检查 `LOG_DIR/ingest.jsonl`。
- 每次导入应追加一条 `success` 或 `failed` 记录，包含时间、来源与结果信息。

## 常见报错排查（阶段02）

1. `SILICONFLOW_API_KEY 未配置`
- 补齐 `.env` 中 `SILICONFLOW_API_KEY`。

2. LLM 调用失败（401/404）
- 检查 `LLM_BASE_URL`、`LLM_MODEL`、`LLM_API_KEY` 是否与服务商兼容。

3. Chroma 初始化失败
- 检查 `CHROMA_PERSIST_DIR` 路径权限。

## 当前依赖

后端新增依赖：
- `openai`
- `httpx`
- `chromadb`

已有依赖：
- `fastapi`
- `uvicorn[standard]`
- `pydantic-settings`

## 下一阶段

进入阶段03：在线双检索与判别服务。
