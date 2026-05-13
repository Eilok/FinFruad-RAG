import json

from openai import OpenAI

from backend.core.settings import settings
from backend.models.knowledge import ScamAnalysis

PROMPT = """
你是一个金融反诈知识抽取系统。

你的任务是：
从输入文本中提取诈骗相关知识，以JSON对象返回结果，用于构建金融诈骗风险知识库。

## 字段定义

`summary`:
- 使用1~3句完整自然语言句子
- 提炼诈骗核心内容
- 必须保留关键诈骗语义
- 用于后续向量检索
- 不要简单复制原文
- 不要遗漏关键诈骗行为

`category`:
诈骗类型。

只能从以下类别中选择最接近的一项：

- 投资诈骗
- 招聘诈骗
- 虚假贷款
- 冒充金融机构
- 电信诈骗
- 刷单诈骗
- 虚假中奖
- 冒充客服
- 钓鱼诈骗
- 加密货币诈骗
- 网络交友诈骗
- 其他诈骗

`patterns`:
诈骗套路列表。

要求：
- 必须是字符串数组
- 每项是简洁短语
- 不超过10个字
- 总结诈骗手法
- 不要使用完整句子

示例：
[
  "高收益承诺",
  "导师带单",
  "紧急转账",
  "冒充客服"
]

`risk_keywords`:
风险关键词列表。

要求：
- 必须是字符串数组
- 每项是高风险词语
- 用于后续关键词匹配
- 优先提取：
  - 高收益词
  - 金融承诺词
  - 诱导性词语
  - 转账相关词语
  - 招聘诱导词

示例：
[
  "稳赚不赔",
  "保本收益",
  "无需经验",
  "日赚500",
  "立即转账"
]


## 输出要求

必须严格输出JSON对象如下：

{
  "summary": "...",
  "category": "...",
  "patterns": [],
  "risk_keywords": []
}

禁止输出：
- markdown
- 注释
- 解释
- 多余文本
- ```json
- 换行说明

如果某字段无法提取：
- 字符串字段返回 "未知"
- 数组字段返回 []

最终输出必须能够被 Python json.loads() 正确解析。
"""

class LLMAnalyzer:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url or None)

    def analyze(self, text: str) -> ScamAnalysis:
        prompt = PROMPT.strip()
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_analysis(content, original_text=text)

    @staticmethod
    def _parse_analysis(content: str, original_text: str) -> ScamAnalysis:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = {}

        summary = str(payload.get("summary") or "").strip() or original_text[:180]
        category = str(payload.get("category") or "未知").strip() or "未知"

        patterns_raw = payload.get("patterns") or []
        keywords_raw = payload.get("risk_keywords") or []

        patterns = [str(x).strip() for x in patterns_raw if str(x).strip()] if isinstance(patterns_raw, list) else []
        risk_keywords = [str(x).strip() for x in keywords_raw if str(x).strip()] if isinstance(keywords_raw, list) else []

        return ScamAnalysis(
            summary=summary,
            category=category,
            patterns=patterns,
            risk_keywords=risk_keywords,
        )
