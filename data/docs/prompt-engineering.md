# Prompt Engineering 速查

## 角色设定

```
你是一个资深 Python 后端工程师，擅长 FastAPI 和 LangChain。
回答问题时请给出可运行的代码示例，并解释关键设计决策。
如果问题超出你的知识范围，请明确说明。
```

## Few-shot 示例

```
请将以下英文技术术语翻译为中文，保持专业准确：

示例1:
输入: rate limiting
输出: 速率限制

示例2:
输入: connection pooling
输出: 连接池

现在请翻译:
输入: circuit breaker
```

## Chain of Thought

```
问题: 一个 API 服务每秒收到 1000 个请求，每个请求耗时 50ms，
需要多少并发线程才能保证平均响应时间不超过 200ms？

请逐步推理:
1. 首先分析单线程的吞吐量
2. 然后计算需要的并发数
3. 最后考虑排队论中的等待时间
4. 给出最终答案
```

## RAG 专用模板

```
你是一个技术文档问答助手。请根据以下参考文档回答用户问题。

## 参考文档
{context}

## 用户问题
{question}

## 回答要求
1. 优先使用参考文档中的内容
2. 如果文档中有代码示例，请引用
3. 如果文档不足以回答问题，请说"根据现有资料无法确定"
4. 回答末尾列出引用的文档来源

## 回答
```

## 结构化输出

```
请分析以下代码的复杂度，以 JSON 格式输出：

{
  "time_complexity": "O(n log n)",
  "space_complexity": "O(n)",
  "is_stable": true,
  "bottlenecks": ["递归调用", "数组拷贝"],
  "suggestions": ["使用迭代替代递归", "原地排序减少内存"]
}
```

## System Prompt 设计原则

1. **明确角色** — 定义 AI 的身份和专业领域
2. **设定边界** — 说明什么能做、什么不能做
3. **输出格式** — 要求特定格式（JSON、Markdown、表格）
4. **示例驱动** — 用 few-shot 引导输出风格
5. **分步推理** — 复杂任务要求 Chain of Thought

## 调试技巧

- Token 超限：缩短 context 或使用 `RecursiveCharacterTextSplitter` 分块
- 回答跑题：强化 System Prompt 中的边界设定
- 格式不稳定：使用结构化输出 + `StrOutputParser`
- 引用不准：在 prompt 中要求标注来源文件名
