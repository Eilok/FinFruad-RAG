## 单独测试 NoRAG 准确率（新增）

支持仅评估 LLM（不使用RAG）在测试集前 n 条样本上的准确率：

```bash
uv run python -m backend.scripts.run_no_rag_eval --test-limit 5
```

可选参数：
- `--test-limit`：每个数据集取前 n 条（默认 50）
- `--output-dir`：指定输出目录

默认输出目录：`backend/outputs/no_rag_eval/{run_id}/`

输出文件：
- `no_rag_logs.jsonl`：逐条日志（实时写入）
- `summary.json`：总体与分数据集指标

## 入库过滤规则（新增）

统一规则：当 LLM 抽取结果的 `risk_keywords` 为空列表时，该条文本**不会入库**。

- 后端会返回 `skipped` 计数与 `skipped_messages`
- 前端会提示 `no scam information extracted`
- 实验构建（train入库）同样执行该过滤规则，避免噪声知识进入向量库

## 仅测试 RAG 性能（新增脚本）

如果只想评估“train入库 + RAG检测”而不跑NoRAG，可使用：

```bash
uv run python -m backend.scripts.run_rag_eval --test-limit 500 --train-positive-limit 0 --keyword-top-k 2 --vector-top-k 2
```

可选参数：
- `--collection-name`：指定隔离collection名（不传则自动生成）
- `--output-dir`：指定输出目录（默认 `backend/outputs/rag_eval/{run_id}`）

输出文件：
- `rag_logs.jsonl`
- `summary.json`
