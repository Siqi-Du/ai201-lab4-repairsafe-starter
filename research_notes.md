# 📝 学习笔记与技术分析：AI 安全分类器设计

本笔记详细整理了在 **Milestone 1** 阶段关于思维链（CoT）、正则表达式匹配和 LLM 接口调用设计方面的发现与探讨，供后续开发及复习参考。

---

## 1. 哪里体现了 CoT（思维链）？

在我们的设计中，主要通过以下两处机制引导并强制大模型进行思维链推理：

### 第一处：明确的格式指令（强制约束）
在提示词的最后（对应 [safety.py](file:///Users/dusiqi/Desktop/CodePath%20AI/CodePath%20AI%20projects/Week%204-AI%20Safety%20&%20Guardrails/lab/ai201-lab4-repairsafe-starter/safety.py) 中的格式规定）：
```text
You must output exactly in the following format:
Reasoning: <one-sentence reasoning explaining the classification>
Tier: <safe | caution | refuse>
```
* **为什么这能强制它进行 CoT？**  
  因为大模型生成回复是一个字一个字从流（Stream）中输出，从左往右、从上预判生成的。当它看到我们的指令要求第一行必须输出 `Reasoning:` 时，它在输出最终的 `Tier` 标签前，被迫先在脑海中进行逻辑推演并把这句推理写出来。如果它不推理直接写 `Tier: refuse`，就违反了我们规定的格式约束。

### 第二处：少样本示例（Few-Shot Examples）示范
在提示词的中部（对应 [safety.py](file:///Users/dusiqi/Desktop/CodePath%20AI/CodePath%20AI%20projects/Week%204-AI%20Safety%20&%20Guardrails/lab/ai201-lab4-repairsafe-starter/safety.py) 中的示例部分）：
```text
Few-Shot Examples:
- User Question: "How do I paint my kitchen cabinets?"
  Reasoning: Painting cabinets is a cosmetic, low-risk project with no risk of fire, flood, or injury.
  Tier: safe
```
* **示范的原理**：  
  大模型具有极强的“上下文学习”（In-Context Learning）能力。通过给它展示这三个具体的问答范例，它会自发模仿范例中**“先给出分析依据（Reasoning），后给出判定分类（Tier）”**的解题模板。

---

## 2. 多次 LLM 调用 vs 单次长文本调用（CoT）

在架构设计上，为了应对“如果不确定是否安全，再发起推理”的需求，我们对比了两次调用与一次 CoT 调用的成本和耗时：

| 维度 | 单次调用（带 CoT 推理） | 多次调用（按需二阶段调用） |
| :--- | :--- | :--- |
| **网络耗时 (Latency)** | **短（推荐）**：只需一次网络请求与云端排队，即使多生成 20 Token 也只需约 100ms。 | **长**：网络往返时间（RTT）和服务器握手排队开销翻倍。 |
| **系统与下游服务开销 (System Overhead)** | **低（推荐）**：只触发一次 API 网关，避免了重复调用带来的系统资源占用。 | **高**：每次请求都必须重新走一遍云端的**下游服务链条**（如 **API 身份验证 (Authentication)**、**权限校验 (Authorization)**、**流量限制 (Rate Limiting)**、**安全审计安全过滤** 等），导致累积延迟极高。 |
| **计费成本 (Cost)** | **低（推荐）**：大模型按 Token 计费。原问题（通常最长）只被发送了一次。 | **高**：由于在第二步需要把原问题和错误分类重新发回，最长的提问文本被计费了两次。 |
| **代码复杂度** | **低（推荐）**：只需一套 System Prompt，线性代码逻辑，易于调试。 | **高**：需要处理复杂的 Python 控制流、状态管理以及多套 Prompt 切换。 |

**结论**：在实际生产中，**“在单次调用中强制大模型先推理后给出分类结论”**是目前性能与准确度平衡的最佳策略。

---

## 3. 正则表达式解析（Regex Matching）拆解

我们在 `safety.py` 中使用了 `re` 模块来解析大模型返回的内容。具体规则解析如下：

### A. 匹配分类行
```python
re.match(r'(?i)^tier\s*:\s*', line_stripped)
```
* `(?i)`：忽略大小写（兼容 `Tier`、`tier`、`TIER`）。
* `^`：匹配行首（表示必须是行开头起第一个单词）。
* `tier`：匹配字面字符。
* `\s*`：匹配零个或多个空白字符（兼容冒号前后的多余空格）。
* `:`：匹配字面冒号。

### B. 提取标签值
```python
re.sub(r'(?i)^tier\s*:\s*', '', line_stripped).strip()
```
* 将匹配到的前缀部分（如 `Tier: `）用空字符串 `''` 替换，从而剥离出纯净的标签，并使用 `.strip()` 清理首尾空格。

### C. 匹配推理行（兼容 reason 和 reasoning）
```python
re.match(r'(?i)^reason(?:ing)?\s*:\s*', line_stripped)
```
* `(?:ing)?`：可选的非捕获组。表示匹配 `reason` 或 `reasoning`，两者皆可识别。

### D. 单词边界匹配（Fallback 备用匹配）
```python
re.search(rf'(?i)\b{t}\b', response_text)
```
* `\b`：单词边界（Word Boundary）。确保匹配的是完整单词（如 `safe`），而不会匹配到部分子串（如 `safely` 或 `unsafe`），防止分类误判。
