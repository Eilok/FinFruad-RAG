# FinFraud-RAG

金融诈骗风险治理系统（前后端分离，持续积累诈骗知识）。

## 阶段进度

- [x] 阶段01：项目初始化与骨架搭建
- [x] 阶段02：离线知识库构建流水线
- [x] 阶段03：在线双检索与判别服务
- [x] 阶段04：前端页面与交互集成
- [x] 阶段05：自动化评估与实验日志
- [ ] 阶段06：统一交付与可运维性完善

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
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`
- `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` / `EMBEDDING_MODEL`
- `CHROMA_PERSIST_DIR` / `CHROMA_COLLECTION_NAME`
- `EVAL_COLLECTION_PREFIX`（实验隔离collection前缀）
- `NEXT_PUBLIC_API_BASE_URL`（前端请求后端地址）

## 启动服务

### 启动后端

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 启动前端

```bash
cd webui
npm run dev
```

## 检索通道优化

- 词法检索通道使用 **BM25**。
- BM25 query 来自用户输入分词。
- BM25 document 为每条知识的拼接文本：`summary + patterns + risk_keywords`。

## 阶段05：自动化评估与实验日志

### 实验隔离模式（默认启用）

评估脚本默认不会使用线上 `CHROMA_COLLECTION_NAME`，而是自动创建独立 collection：

- 自动命名：`{EVAL_COLLECTION_PREFIX}_{run_id}`
- 示例：`scam_knowledge_eval_20260513_170501`

这意味着：
- 实验重置/写入不会污染线上collection
- 前端在线检索仍使用线上 `CHROMA_COLLECTION_NAME`

### 全量评估命令

```bash
uv run python -m backend.scripts.run_eval --test-limit 500 --keyword-top-k 3 --vector-top-k 3
```

可选参数：
- `--test-limit`：每个数据集测试样本数（默认 500）
- `--train-positive-limit`：每个数据集用于离线构建的正样本数量；`0` 表示使用全部（默认 0）
- `--keyword-top-k`：BM25 召回 top-k
- `--vector-top-k`：向量召回 top-k
- `--collection-name`：手动指定实验 collection 名（不传则自动生成隔离名）
- `--output-dir`：指定输出目录

### 快速冒烟测试入口（1-5条）

```bash
uv run python -m backend.scripts.run_eval_smoke --test-limit 2 --train-positive-limit 3
```

建议范围：
- `--test-limit`：1~5
- `--train-positive-limit`：1~5

支持可选隔离名覆盖：

```bash
uv run python -m backend.scripts.run_eval_smoke --test-limit 2 --train-positive-limit 3 --collection-name my_eval_sandbox
```

### 输出产物

默认目录：`backend/outputs/eval/{run_id}/`

文件说明：
- `no_rag_logs.jsonl`：NoRAG逐条日志（实时落盘）
- `rag_logs.jsonl`：RAG逐条日志（实时落盘）
- `summary.json`：汇总指标与构建统计（含 `collection_name`）

逐条日志字段包含：
- `text`
- `label`
- `model_answer`
- `prediction`
- `is_correct`
- `mode`
- `time`
- `retrieved_evidence`（RAG模式）

## 当前依赖

后端依赖：
- `fastapi`
- `uvicorn[standard]`
- `pydantic-settings`
- `openai`
- `httpx`
- `chromadb`

前端依赖：
- `next`
- `react`
- `react-dom`
- `tailwindcss`
- `typescript`

## 下一阶段

进入阶段06：统一交付与可运维性完善。
