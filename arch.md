# 技术架构说明（arch.md）

## 1. 架构总览

本项目采用“前后端分离 + 向量检索增强 + 脚本化评估”的技术架构，核心由以下几层构成：

1. 前端展示与交互层：`Next.js`（React）
2. 后端 API 与编排层：`FastAPI`
3. 模型调用与向量化适配层：`OpenAI SDK` + `HTTPX`（硅基流动 Embedding）
4. 向量存储与检索层：`Chroma`（本地持久化）
5. 离线构建与实验评估层：Python 脚本（`backend/scripts`）
6. 配置与运维层：`.env` + `pydantic-settings` + PowerShell 统一脚本入口

该架构在工程层面强调：
- 低耦合分层（接口层与业务层严格分离）
- 可替换的模型/嵌入供应商适配
- 可复现实验与线上服务隔离
- 前后端独立演进

---

## 2. 前端技术架构（Next.js）

### 2.1 框架与运行时

- 使用 `Next.js`（App Router 模式）构建前端。
- UI 基于 `React` 函数组件和 Hook 状态管理。
- 前端作为独立应用运行，默认端口 `3000`。

### 2.2 工程组织

典型结构：
- `webui/app/`：页面与布局
- `webui/lib/`：前端 API 调用封装
- `webui/types/`：与后端协议同步的 TypeScript 类型定义

这种组织方式有两个技术收益：
1. API 协议与页面逻辑解耦
2. 类型收敛，减少接口联调错误

### 2.3 前后端通信

- 前端通过 `fetch` 调用后端 REST 接口。
- 后端地址由 `NEXT_PUBLIC_API_BASE_URL` 注入，支持环境切换（本地/测试/生产）。
- 所有请求走统一封装层，便于后续扩展重试、鉴权、埋点。

---

## 3. 后端技术架构（FastAPI）

### 3.1 框架选型与特点

- 使用 `FastAPI` 作为 HTTP 服务框架。
- 优势：
  - 类型提示友好（Pydantic）
  - JSON API 开发效率高
  - 对结构化输入输出天然支持

### 3.2 分层设计（技术边界）

后端按“协议层/业务层/基础设施层”拆分：

- `backend/service/`：仅接口层（路由、请求响应模型绑定）
- `backend/core/`：业务编排（入库、检索、评估流程）
- `backend/providers/`：外部模型服务适配
- `backend/storage/`：向量库访问封装
- `backend/models/`：Pydantic 数据模型

该分层使得：
- 业务逻辑不依赖 FastAPI 路由细节
- 供应商切换只需改 provider 层
- 存储后端切换可局部改造 storage 层

### 3.3 中间件与跨域

- 后端启用 `CORSMiddleware`。
- 跨域白名单由 `CORS_ORIGINS` 环境变量控制。
- 解决浏览器 `OPTIONS` 预检请求问题，支持前端独立部署访问。

---

## 4. 模型与推理接入架构

### 4.1 LLM 接入（OpenAI SDK）

- 使用 `openai` Python SDK 统一封装 LLM 调用。
- 关键参数外置：
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`

技术意义：
- 兼容 OpenAI 协议的多供应商服务
- 避免代码与单一模型平台强绑定

### 4.2 Embedding 接入（HTTPX）

- 使用 `httpx` 直连 Embedding API（硅基流动兼容接口）。
- 参数外置：
  - `SILICONFLOW_API_KEY`
  - `SILICONFLOW_BASE_URL`
  - `EMBEDDING_MODEL`
- 超时可配置：`REQUEST_TIMEOUT_SECONDS`

技术意义：
- 独立于 LLM 通道，可按成本/效果单独优化嵌入模型
- 可对接任意标准化 embedding endpoint

### 4.3 输出结构化

- 模型输出采用 JSON 结构化解析。
- 通过 Pydantic 统一约束返回结构。
- 支持回退逻辑（fallback）与错误容错。

---

## 5. 向量数据库架构（Chroma）

### 5.1 存储引擎

- 使用 `Chroma` 作为本地向量数据库。
- 持久化路径：`CHROMA_PERSIST_DIR`（默认 `backend/.chroma`）。
- 默认集合名：`CHROMA_COLLECTION_NAME`。

### 5.2 访问封装

- 通过 `ChromaKnowledgeStore` 封装集合创建、写入、查询、统计与重置。
- 增加“重绑自愈”（rebind）机制，降低 collection 句柄失效风险。

### 5.3 集合隔离策略

项目实现了“实验隔离模式”：
- 线上服务使用固定 collection
- 评估脚本默认使用独立 collection（前缀 + run_id）

技术意义：
- 评估过程不污染线上知识库
- 保证实验可复现与可追踪

---

## 6. 检索技术架构

### 6.1 双通道检索

当前检索层采用“词法 + 向量”并行召回：
1. 词法通道：`BM25`
2. 向量通道：Embedding 相似度检索（Chroma）

### 6.2 BM25 实现方式

- Chroma 不原生提供 BM25。
- 项目在 `core` 层实现了自定义 BM25 索引与打分逻辑。

技术收益：
- 提升关键词/术语显式匹配能力
- 与语义向量召回互补，降低单路召回偏差

### 6.3 融合机制

- 双通道结果按规则融合并排序。
- 为控制上下文 token，证据引用采用短编号映射策略（内部映射回真实记录 ID）。

---

## 7. 评估与实验架构

### 7.1 脚本化评估

评估流程全部脚本化，支持：
- 全量评估
- 冒烟评估（1~5条）
- NoRAG 单独评估
- RAG-only 评估

入口脚本位于 `backend/scripts`，典型包括：
- `run_eval.py`
- `run_eval_smoke.py`
- `run_no_rag_eval.py`
- `run_rag_eval.py`

### 7.2 日志与产物

- 逐条样本实时落盘（避免中断丢失结果）。
- 产物统一落地至 `backend/outputs/...`。
- 汇总指标包含 accuracy/precision/recall/F1 与混淆矩阵元素。

### 7.3 实验与线上解耦

- 评估默认隔离 collection。
- 汇总文件记录 collection 名，便于追溯与回放。

---

## 8. 配置中心与环境管理

### 8.1 配置框架

- 使用 `pydantic-settings` 从 `.env` 加载配置。
- 配置集中定义于 `settings` 模块。

### 8.2 配置分层

典型配置域：
- 服务配置（host/port/env）
- 模型配置（LLM/Embedding）
- 存储配置（Chroma 路径与集合）
- 检索参数（默认 top-k）
- 运维配置（超时、日志目录、CORS）

技术意义：
- 环境无关代码（dev/test/prod）
- 降低硬编码与泄露风险

---

## 9. 依赖与包管理架构

### 9.1 Python 侧

- 使用 `uv` 作为依赖管理与运行入口。
- 依赖定义于 `pyproject.toml`，包括：
  - `fastapi`
  - `uvicorn[standard]`
  - `openai`
  - `httpx`
  - `chromadb`
  - `pydantic-settings`

### 9.2 前端侧

- Node 依赖由 `npm` 管理。
- 以 `next/react/typescript/tailwindcss` 为核心。

---

## 10. 运维与发布架构

### 10.1 统一命令入口

项目根目录 `scripts/` 提供 PowerShell 聚合入口：
- 启动后端
- 启动前端
- 单条入库
- 全量/冒烟评估

技术意义：
- 降低操作门槛
- 统一开发、测试与交付流程

### 10.2 可观测性基础

- 入库、评估等关键环节有结构化日志。
- 实验过程实时写日志，支持中断后定位。
- 产物目录结构固定，便于自动化收集。

### 10.3 容错与鲁棒性

- 向量库访问有集合重绑自愈。
- 模型调用具备异常回退路径。
- 前后端跨域策略可配置，减少环境差异问题。

---

## 11. 技术架构优势总结

从工程技术角度，本项目的架构优势主要体现在：

1. 分层清晰：接口、流程、存储、模型适配职责明确。
2. 组件可替换：LLM、Embedding、检索策略可局部替换。
3. 实验友好：评估脚本体系完善，支持隔离与快速冒烟。
4. 线上安全：实验与线上 collection 分离，降低误污染风险。
5. 交付可用：前后端与脚本入口统一，便于部署与演示。
6. 运维可控：配置集中、日志结构化、异常可追踪。

该技术架构具备较好的可扩展性，能够支撑后续在模型、检索算法、评估体系和部署方式上的持续迭代。
