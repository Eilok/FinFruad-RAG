# FinFraud-RAG

金融诈骗风险治理系统（前后端分离，持续积累诈骗知识）。

## 阶段进度

- [x] 阶段01：项目初始化与骨架搭建
- [x] 阶段02：离线知识库构建流水线
- [x] 阶段03：在线双检索与判别服务
- [ ] 阶段04：前端页面与交互集成
- [ ] 阶段05：自动化评估与实验日志
- [ ] 阶段06：统一交付与可运维性完善

## 当前项目结构（阶段03）

```text
.
├─ backend/
│  ├─ app.py
│  ├─ core/
│  │  ├─ detect.py
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
│  │  ├─ detect.py
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

说明：`backend/service` 仅放接口层代码；检索、融合与判别流程在 `backend/core`。

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

### A. API 导入

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

### B. CLI 导入

```bash
uv run python -m backend.scripts.ingest_kb --text "高薪兼职无需经验，先交保证金" --source manual
```

## 阶段03：在线双检索与判别

接口：`POST /detect`

请求示例：

```json
{
  "text": "平台客服说我开通了会员，每月自动扣费，让我马上转账取消。",
  "keyword_top_k": 3,
  "vector_top_k": 3,
  "return_evidence": true
}
```

返回字段：
- `keyword_hits`：关键词通道召回结果（含匹配关键词与分数）
- `vector_hits`：向量通道召回结果（含相似度分数）
- `fused_hits`：融合排序结果
- `detection`：最终判别
  - `is_scam`：是否诈骗
  - `confidence`：置信度（0~1）
  - `reason`：判别原因
  - `evidence_refs`：引用证据的 `record_id`

## 阶段03测试方法

### 测试1：双通道召回

1. 先通过 `POST /kb/ingest` 导入若干诈骗样本。
2. 调用 `POST /detect`。
3. 检查 `keyword_hits` 与 `vector_hits` 是否都返回结果（若库中有可匹配内容）。

### 测试2：融合结果与结构化判别

1. 检查 `fused_hits` 是否按 `score` 降序。
2. 检查 `detection` 是否包含 `is_scam/confidence/reason/evidence_refs`。

### 测试3：失败场景

1. 提交空文本，预期 HTTP 400。
2. 模型不可用时，预期接口仍返回结构化结果（`detection.reason` 含 fallback 说明）。

## 常见报错排查（阶段03）

1. `Input text cannot be empty`
- 检查请求体 `text` 是否为空。

2. `Detection pipeline failed: ...`
- 检查向量服务与 LLM 配置，确认 API Key、Base URL、Model 可用。

3. 无召回结果
- 先确认已执行离线入库，且 `CHROMA_PERSIST_DIR` 指向同一向量库目录。

## 当前依赖

后端依赖：
- `fastapi`
- `uvicorn[standard]`
- `pydantic-settings`
- `openai`
- `httpx`
- `chromadb`

## 下一阶段

进入阶段04：前端页面与交互集成。
