# FinFraud-RAG

金融诈骗风险治理系统（RAG），支持：
- 离线知识库构建（LLM结构化抽取 + 向量入库）
- 在线双检索判别（BM25 + 向量）
- 前端交互（检测 + 新文本入库）
- 自动化对比评估（RAG vs NoRAG）

## 项目结构

```text
.
├─ backend/
│  ├─ service/                  # 仅接口层代码
│  ├─ core/                     # 核心业务流程
│  ├─ providers/                # LLM/Embedding适配
│  ├─ storage/                  # Chroma封装
│  ├─ scripts/                  # 后端脚本入口
│  └─ outputs/eval/             # 评估产物目录
├─ webui/                       # Next.js 前端
├─ data/                        # 数据集
├─ scripts/                     # Windows统一命令入口
├─ SPECS/                       # 阶段规格文档
└─ AGENTS.md                    # 开发规范
```

## 环境要求

1. Python 3.12+
2. Node.js 18+
3. `uv`

## 安装与配置

### 1) 安装依赖

后端：

```bash
uv sync
```

前端：

```bash
cd webui
npm install
```

### 2) 配置环境变量

```bash
cp .env.example .env
```

关键变量说明：
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`：LLM配置
- `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` / `EMBEDDING_MODEL`：嵌入模型配置
- `CHROMA_PERSIST_DIR`：向量库存储目录
- `CHROMA_COLLECTION_NAME`：线上默认collection（前端/在线检测使用）
- `EVAL_COLLECTION_PREFIX`：评估隔离collection前缀
- `REQUEST_TIMEOUT_SECONDS`：外部请求超时（秒）
- `CORS_ORIGINS`：允许跨域来源，逗号分隔
- `NEXT_PUBLIC_API_BASE_URL`：前端请求后端地址

## 统一命令入口（Windows）

在项目根目录执行：

- 启动后端：

```powershell
./scripts/start_backend.ps1
```

- 启动前端：

```powershell
./scripts/start_webui.ps1
```

- 导入单条诈骗文本：

```powershell
./scripts/ingest_one.ps1 -Text "Limited-time investment plan, guaranteed 20% daily return" -Source manual
```

- 运行全量评估：

```powershell
./scripts/run_eval.ps1 -TestLimit 500 -TrainPositiveLimit 0 -KeywordTopK 3 -VectorTopK 3
```

- 运行快速冒烟评估（1~5条）：

```powershell
./scripts/run_eval_smoke.ps1 -TestLimit 2 -TrainPositiveLimit 3
```

## 快速开始（端到端）

1. 启动后端：`./scripts/start_backend.ps1`
2. 启动前端：`./scripts/start_webui.ps1`
3. 前端访问：`http://localhost:3000`
4. 在前端先做 `Knowledge Ingestion`（输入或上传文本）
5. 再在检测区执行 `Run Detection`

后端健康检查：

```bash
curl http://localhost:8000/healthz
```

## 离线知识库构建

### API方式

`POST /kb/ingest`

请求示例：

```json
{
  "items": [
    {
      "text": "No experience needed, earn high commission daily, pay deposit first.",
      "source": "manual"
    }
  ],
  "retry_times": 2
}
```

### CLI方式

- 单条：

```bash
uv run python -m backend.scripts.ingest_kb --text "High return, instant transfer required" --source manual
```

- 批量（txt/jsonl）：

```bash
uv run python -m backend.scripts.ingest_kb --input-file data/sample_ingest.jsonl --source dataset --retry-times 2
```

## 在线检测（BM25 + 向量）

`POST /detect`

请求示例：

```json
{
  "text": "Support asks me to transfer money now to avoid subscription charges.",
  "keyword_top_k": 3,
  "vector_top_k": 3,
  "return_evidence": true
}
```

返回：
- `keyword_hits`（BM25通道）
- `vector_hits`
- `fused_hits`
- `detection`（`is_scam/confidence/reason/evidence_refs`）

说明：
- Prompt中证据引用已使用短编号（`ref_id=1,2,3...`）以节省token。
- 最终返回给用户的 `evidence_refs` 会映射回真实 `record_id`。

## 前端功能说明

前端页面支持：
1. 新诈骗文本入库
- 单条输入入库
- `.txt/.jsonl` 文件上传批量入库
2. 在线检测
- BM25 top-k / vector top-k 参数配置
- 检测结果与三路证据展示
3. 交互
- `Retry / Clear / Copy JSON`

## 自动化评估与实验隔离

### 数据导入

下载[difraud](https://huggingface.co/datasets/difraud/difraud)数据集中的`job_scams`与`sms`两个子集，放置于 `data/` 目录下。

### 默认隔离策略

`run_eval` 默认使用隔离collection，不污染线上collection：

- 自动命名：`{EVAL_COLLECTION_PREFIX}_{run_id}`
- 可手动指定：`--collection-name`

### 全量评估

```bash
uv run python -m backend.scripts.run_eval --test-limit 500 --train-positive-limit 0 --keyword-top-k 3 --vector-top-k 3
```

### 冒烟评估（推荐先跑）

```bash
uv run python -m backend.scripts.run_eval_smoke --test-limit 2 --train-positive-limit 3
```

### 实时日志保证

评估时日志为逐条实时落盘（非结束后一次性写入）：
- `no_rag_logs.jsonl`
- `rag_logs.jsonl`

即使中断，也能保留已完成样本记录。

## 输出目录说明

- 向量库目录：`backend/.chroma/`
- 运行日志：`backend/logs/`
- 评估产物：`backend/outputs/eval/{run_id}/`
  - `no_rag_logs.jsonl`
  - `rag_logs.jsonl`
  - `summary.json`

## 常见问题

1. 前端请求 `OPTIONS /detect` 返回 405
- 检查 `CORS_ORIGINS` 是否包含前端域名。

2. `Collection ... does not exist`
- 已做自愈重绑；若仍出现，请确认没有并发运行多个重置同名collection任务。

3. 无召回结果
- 先确认已完成入库，并检查当前服务使用的 collection 是否正确。

4. 模型调用失败
- 检查 API key、base URL、model 名称、网络可达性。

## 发布前最小检查清单

1. `uv sync` 成功且依赖一致。
2. `.env` 必填项已配置。
3. 后端 `healthz` 正常。
4. 前端可完成一次入库 + 一次检测。
5. 冒烟评估可跑通并生成 `summary.json`。
6. 实验collection与线上collection隔离验证通过。