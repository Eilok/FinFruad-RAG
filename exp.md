# 实验说明（exp.md）

## 1. 实验目标

本项目实验用于验证检索增强（RAG）在金融诈骗文本判别任务上的有效性，核心关注：

1. 与无检索增强（NoRAG）相比，RAG 是否提升分类性能；
2. 离线知识构建策略（结构化抽取 + 过滤入库）是否能形成有效证据库；
3. 在不同数据集上的泛化表现是否稳定。

---

## 2. 数据集与样本划分

### DIFrauD数据集介绍
DIFrauD - Domain Independent Fraud Detection Benchmark
Domain Independent Fraud Detection Benchmark is a labeled corpus containing over 95,854 samples of deceitful and truthful texts from a number of independent domains and tasks. Deception, however, can be different -- in this corpus we made sure to gather strictly real examples of deception that are intentionally malicious and cause real harm, despite them often having very little in common. Covering seven domains, this benchmark is designed to serve as a representative slice of the various security challenges that remain open problems today.

DATASET
The entire dataset contains 95854 samples, 37282 are deceptive and 58572 non-deceptive.

There are 7 independent domains in the dataset.

Each task is (or has been converted to) a binary classification problem where y is an indicator of deception.

Phishing (2020 Email phishing benchmark with manually labeled emails)

- total: 15272 deceptive: 6074 non-deceptive: 9198

Fake News (News Articles)

- total: 20456 deceptive: 8832 non-deceptive: 11624

Political Statements (Claims and statements by politicians and other entities, made from Politifact by relabeling LIAR)

- total: 12497 deceptive: 8042 non-deceptive: 4455

Product Reviews (Amazon product reviews)

- total: 20971 deceptive: 10492 non-deceptive: 10479

Job Scams (Job postings on an online board)

- total: 14295 deceptive: 599 non-deceptive: 13696

SMS (combination of SMS Spam from UCI repository and SMS Phishing datasets)

- total: 6574 deceptive: 1274 non-deceptive: 5300

Twitter Rumours (Collection of rumours from PHEME dataset, covers multiple topics)

- total: 5789 deceptive: 1969 non-deceptive: 3820

Each one was constructed from one or more datasets. Some tasks were not initially binary and had to be relabeled. The inputs vary wildly both stylistically and syntactically, as well as in terms of the goal of deception (or absence of thereof) being performed in the context of each dataset. Nonetheless, all seven datasets contain a significant fraction of texts that are meant to deceive the person reading them one way or another.

Each subdirectory/config contains the domain/individual dataset split into three files:

train.jsonl, test.jsonl, and validation.jsonl

that contain train, test, and validation sets, respectively.

The splits are:

-- train=80%

-- test=10%

-- valid=10%

The sampling process was random with seed=42. It was stratified with respect to y (label) for each domain.

Fields
Each jsonl file has two fields (columns): text (string) and label (integer)

text contains a statement or a claim that is either deceptive or thruthful. It is guaranteed to be valid unicode, less than 1 million characters, and contains no empty entries or non-values.

label answers the question whether text is deceptive: 1 means yes, it is deceptive, 0 means no, the text is not deceptive (it is truthful).

Processing and Cleaning
Each dataset has been cleaned using Cleanlab. Non-english entries, erroneous (parser error) entries, empty entries, duplicate entries, entries of length less than 2 characters or exceeding 1000000 characters were all removed.

Labels were manually curated and corrected in cases of clear error.

Whitespace, quotes, bulletpoints, unicode is normalized.

### 处理

实验使用 `DIFrauD` 数据集下两套数据集：

1. `job scams`
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

## 5. 评估指标

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

## 6. 指标计算定义

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

