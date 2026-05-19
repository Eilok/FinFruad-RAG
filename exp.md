# 实验说明（exp.md）

## 1. 实验目标

本项目实验用于验证检索增强（RAG）在金融诈骗文本判别任务上的有效性，核心关注：

1. 与无检索增强（NoRAG）相比，RAG 是否提升分类性能；
2. 离线知识构建策略（结构化抽取 + 过滤入库）是否能形成有效证据库；
3. 在不同数据集上的泛化表现是否稳定。

---

## 2. 数据集与样本划分

实验使用 `data/` 目录下两套数据集：

1. `job_scams`
2. `sms`

每套数据均包含：
- `train.jsonl`
- `validation.jsonl`
- `test.jsonl`

数据字段以当前代码实现为准：
- `text`：样本文本
- `label`：二分类标签（`1` 为诈骗，`0` 为非诈骗）

### 2.1 离线构建语料选择

用于知识库构建的数据来自两套训练集：
- 从 `job_scams/train.jsonl` 筛选 `label=1`
- 从 `sms/train.jsonl` 筛选 `label=1`

即仅使用诈骗正样本构建知识库。

### 2.2 测试集选择

评估集来自两套测试集：
- `job_scams/test.jsonl` 前 `N` 条
- `sms/test.jsonl` 前 `N` 条

其中 `N` 由参数 `--test-limit` 控制：
- 全量实验常用 `N=500`
- 冒烟实验常用 `N=1~5`

---

## 3. 实验流程设计

实验采用“先构建、后评估”的两阶段流程。

### 3.1 阶段A：离线知识库构建

对训练正样本逐条执行：

1. LLM 结构化抽取：
   - `summary`
   - `category`
   - `patterns`
   - `risk_keywords`
2. 入库过滤：
   - 若 `risk_keywords` 为空列表，则该条样本跳过（不入库）
3. 向量化：
   - 对 `summary` 生成 embedding
4. Chroma 写入：
   - `document = summary`
   - `metadata = category/patterns/risk_keywords/original_text/source/created_at`

该阶段输出构建统计：
- `total_input`
- `success`
- `failed`
- `skipped`
- `chroma_count`

### 3.2 阶段B：测试集评估

对每条测试样本（`text`, `label`）进行判别，并记录日志。

根据脚本入口不同，支持三类实验：

1. **NoRAG + RAG 对比实验**（`run_eval.py`）
   - NoRAG：仅依赖 LLM 判别
   - RAG：BM25 + 向量双检索后再判别

2. **RAG-only 实验**（`run_rag_eval.py`）
   - 只评估“train 入库 + RAG 判别”
   - 不执行 NoRAG 分支

3. **NoRAG-only 实验**（`run_no_rag_eval.py`）
   - 只评估 LLM 直判
   - 不依赖知识库

---

## 4. RAG 方法在实验中的具体实现

### 4.1 双通道召回

- 词法通道：BM25
  - query：测试文本分词
  - document：`summary + patterns + risk_keywords` 拼接文本
- 向量通道：Chroma 相似度检索
  - query embedding：测试文本向量
  - target：知识库 `summary` 向量

### 4.2 结果融合

按 `record_id` 去重后进行加权融合：

`fused_score = 0.4 * bm25_score + 0.6 * vector_score`

再按分数降序作为模型证据上下文。

### 4.3 证据压缩策略

为降低 token 开销，证据上下文使用短编号：
- 按排序重编号 `ref_id=1,2,3...`
- 模型返回短编号后再映射回真实 `record_id`

---

## 5. 实验隔离机制

为避免污染线上知识库，评估默认使用隔离 collection：

- 默认命名：`{EVAL_COLLECTION_PREFIX}_{run_id}`
- 可通过 `--collection-name` 显式指定

线上前端/服务继续使用 `CHROMA_COLLECTION_NAME`，与实验集合隔离。

---

## 6. 日志与产物

### 6.1 输出目录

不同实验脚本对应目录：

- 对比实验：`backend/outputs/eval/{run_id}/`
- RAG-only：`backend/outputs/rag_eval/{run_id}/`
- NoRAG-only：`backend/outputs/no_rag_eval/{run_id}/`

### 6.2 日志文件

可能包含：
- `no_rag_logs.jsonl`
- `rag_logs.jsonl`
- `summary.json`

### 6.3 逐条日志字段

逐条记录至少包含：
- `time`
- `dataset`
- `sample_index`
- `mode`（NoRAG / RAG）
- `text`
- `label`
- `model_answer`（`is_scam/confidence/reason/evidence_refs`）
- `prediction`
- `is_correct`
- `retrieved_evidence`（RAG 模式）

### 6.4 实时落盘

评估日志采用“逐条样本完成即写入”策略：
- 进程中断时仍保留已完成样本结果
- 降低长时实验丢失风险

---

## 7. 评估指标

项目统一输出二分类指标：

1. `accuracy`
2. `precision`
3. `recall`
4. `f1`
5. 混淆矩阵要素：
   - `tp`
   - `tn`
   - `fp`
   - `fn`

并按两层粒度汇总：
- `overall`：全数据总体
- `by_dataset`：`job_scams` 与 `sms` 分别统计

---

## 8. 指标计算定义

设正类为诈骗（label=1）：

- `TP`：真实为1且预测为1
- `TN`：真实为0且预测为0
- `FP`：真实为0但预测为1
- `FN`：真实为1但预测为0

指标公式：

- `Accuracy = (TP + TN) / (TP + TN + FP + FN)`
- `Precision = TP / (TP + FP)`
- `Recall = TP / (TP + FN)`
- `F1 = 2 * Precision * Recall / (Precision + Recall)`

当分母为0时，代码中按 `0.0` 处理。

---

## 9. 复现实验命令

### 9.1 对比实验（NoRAG vs RAG）

```bash
uv run python -m backend.scripts.run_eval --test-limit 500 --train-positive-limit 0 --keyword-top-k 3 --vector-top-k 3
```

### 9.2 RAG-only 实验

```bash
uv run python -m backend.scripts.run_rag_eval --test-limit 500 --train-positive-limit 0 --keyword-top-k 3 --vector-top-k 3
```

### 9.3 NoRAG-only 实验

```bash
uv run python -m backend.scripts.run_no_rag_eval --test-limit 500
```

### 9.4 冒烟实验（快速检查）

```bash
uv run python -m backend.scripts.run_eval_smoke --test-limit 2 --train-positive-limit 3
```

---

## 10. 实验结果解读建议

1. 先比较 `overall`：观察 RAG 相比 NoRAG 是否有稳定增益；
2. 再看 `by_dataset`：判断不同语料域（招聘诈骗/SMS）是否存在表现差异；
3. 关注 `FP/FN` 结构：
   - `FP` 高：误报较多
   - `FN` 高：漏报较多
4. 结合 `rag_logs.jsonl` 中 `retrieved_evidence` 分析：
   - 是否召回了语义相关证据
   - 证据是否能支持模型判别理由
5. 结合构建统计中的 `skipped`：
   - 过滤比例过高可能导致知识覆盖不足
   - 过滤比例过低可能引入噪声知识

---

## 11. 方法与实验一致性说明

本项目实验与线上方法链路一致：
- 同一入库流水线（含过滤）
- 同一检索与融合逻辑
- 同一判别输出结构

因此实验指标可直接用于指导线上策略调整（如 top-k、融合权重、过滤阈值、提示词策略等）。
