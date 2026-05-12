# FinFraud-RAG

金融诈骗风险治理系统（前后端分离，持续积累诈骗知识）。

## 阶段进度

- [x] 阶段01：项目初始化与骨架搭建
- [ ] 阶段02：离线知识库构建流水线
- [ ] 阶段03：在线双检索与判别服务
- [ ] 阶段04：前端页面与交互集成
- [ ] 阶段05：自动化评估与实验日志
- [ ] 阶段06：统一交付与可运维性完善

## 当前项目结构（阶段01）

```text
.
├─ backend/
│  ├─ app.py
│  ├─ core/
│  │  ├─ health.py
│  │  └─ settings.py
│  ├─ models/
│  ├─ providers/
│  ├─ scripts/
│  ├─ service/
│  │  └─ health.py
│  └─ storage/
├─ data/
├─ webui/
│  ├─ app/
│  │  ├─ globals.css
│  │  ├─ layout.tsx
│  │  └─ page.tsx
│  ├─ package.json
│  └─ tsconfig.json
├─ AGENTS.md
├─ SPECS/
├─ pyproject.toml
└─ .env.example
```

说明：`backend/service` 只放接口层代码，业务逻辑放在 `backend/core` 等模块。

## 环境准备

1. Python 3.12+
2. Node.js 18+
3. `uv`（Python 包管理）

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

## 启动方式

### 启动后端（FastAPI）

```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 启动前端（Next.js）

```bash
cd webui
npm run dev
```

默认访问：
- 前端：http://localhost:3000
- 后端健康检查：http://localhost:8000/healthz

## 阶段01功能测试方法

### 测试1：目录边界

检查以下目录存在：
- `backend/service`
- `backend/core`
- `backend/storage`
- `backend/models`
- `backend/providers`
- `backend/scripts`
- `webui`

并确认 `backend/service` 中仅有 API 相关代码。

### 测试2：后端健康检查接口

启动后端后执行：

```bash
curl http://localhost:8000/healthz
```

预期返回：

```json
{"status":"ok"}
```

### 测试3：前端骨架页面

启动前端后访问 `http://localhost:3000`，应看到 `FinFraud-RAG` 标题和“前端骨架已完成”提示。

## 当前依赖（阶段01）

后端 Python 依赖：
- `fastapi`
- `uvicorn[standard]`
- `pydantic-settings`

前端 Node 依赖：
- `next`
- `react`
- `react-dom`
- `typescript`

## 下一阶段

进入阶段02：离线知识库构建流水线（LLM 结构化抽取、摘要向量化、Chroma 入库）。
