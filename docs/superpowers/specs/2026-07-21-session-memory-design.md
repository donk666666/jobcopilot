# 智能文档助手 — 分层记忆与上下文管理

## 问题现状

当前项目的上下文管理存在结构性缺陷：

1. **前后端"脑裂"**：前端 `session_id` 硬编码为 `'web'`，页面刷新后聊天区空白，但后端仍持有旧历史，用户看不到上文但 Agent 收到全文
2. **粗暴截断**：历史管理仅为 `history[-20:]` / `history[-10:]`，无智能遗忘机制
3. **无新对话能力**：前端无可用的新建/切换会话入口
4. **内存存储**：服务重启后所有会话丢失

## 目标

- **一期**：解决串味 + 遗忘 + 会话可管理，采用滑动窗口 + LLM 摘要压缩
- **二期**：扩展为完整四层记忆体系（语义记忆 / 情景记忆 / 程序记忆 / 线上兜底），与本 spec 保持兼容

## 整体架构

```
前端 (SPA)
  ├── 会话列表 sidebar（可切换/删除/新建）
  ├── 聊天区（历史消息可回显）
  └── 新对话按钮
         │
         │ POST /api/chat  { message, session_id }
         ▼
FastAPI 后端
  ├── 会话管理模块（新建/列表/删除/获取历史）
  ├── 记忆压缩模块（滑动窗口 + LLM 摘要）
  └── Agent 引擎（使用压缩后的上下文）
         │
         ▼
   SQLite（会话持久化）
   - sessions 表：id, title, created_at, updated_at
   - messages 表：id, session_id, role, content, created_at
   - summaries 表：session_id, summary_text, last_message_idx
```

## 会话管理

### 前端

- 页面加载时生成 `session_id = crypto.randomUUID()` 存入 localStorage
- 左侧 sidebar 调用 `GET /api/sessions` 获取会话列表
- 点击"新对话" → 新 UUID → 新建标签页
- 点击已有会话 → 切换到对应 session，拉取历史消息回显
- 每轮聊天完成后刷新 sidebar 列表

### 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sessions` | 返回所有会话列表（id, title, first_message, updated_at） |
| `GET` | `/api/sessions/{id}` | 返回该会话的完整消息历史 |
| `DELETE` | `/api/sessions/{id}` | 删除会话及其所有消息 |
| `POST` | `/api/chat` | 不变，额外返回 session 摘要 |

会话标题自动生成：取用户第一条消息的前 20 个字作为 title。

## 记忆压缩

### 第 1 层：滑动窗口

消息进入会话后逐条追加。不做硬截断，改为：

- **活跃窗口**：最近 **10 轮**（20 条消息）完整保留，直接作为 Agent 的 `messages` 字段传入
- **超出窗口**：旧消息不丢弃，交给第 2 层

### 第 2 层：LLM 摘要压缩

当会话消息超过 10 轮时触发压缩：

1. 取超出窗口的旧消息，调用 LLM 生成一段摘要（≤300 字）
2. 摘要包含：关键话题、重要结论、待办事项
3. 摘要作为 system prompt 的前缀注入到后续每轮对话中

**增量策略**：每次新消息进来时，只对新增的超出部分做增量压缩（追加到已有摘要末尾），避免每次都重跑全文。

### Agent 收到的最终上下文结构

```
[system prompt]
[历史摘要（≤300字）]
[活跃窗口内 10 轮完整消息]
[当前用户消息]
```

## 线上兜底（一期简化版）

| 场景 | 策略 |
|------|------|
| 摘要 + 窗口总 token 超过模型上下文限制 | 缩减窗口至 5 轮，压缩已有摘要为更短版本 |
| 会话超过 30 天未活动 | 摘要保留，完整消息历史归档 |

## 数据模型

### 新增 `app/session_store.py`

```python
# SQLite 持久化层
# 替代现有内存 dict，提供 SessionStore 类
# - create(session_id) → session
# - add_message(session_id, role, content) → message_id
# - get_history(session_id) → list[dict]
# - get_summary(session_id) → str | None
# - save_summary(session_id, summary_text, last_idx)
# - list_sessions() → list[dict]
# - delete(session_id)
# - get_last_msg_index(session_id) → int
```

### 新增 `app/memory.py`

```python
# 记忆压缩模块
# - compress_history(messages: list[dict], existing_summary: str) → str
# - build_context(session_id: str) → list[dict]
#   组装最终传给 Agent 的消息列表：summary_prompt + 窗口消息
```

## 改动范围

| 文件 | 改动 |
|------|------|
| `app/session_store.py` | 新增，SQLite 持久化 |
| `app/memory.py` | 新增，压缩 + 上下文构建 |
| `app/main.py` | 替换内存 dict 为 SessionStore，新增 /api/sessions 路由 |
| `app/agent/graph.py` | `run_agent` 适配新上下文结构 |
| `app/agent/nodes.py` | 移除冗余的历史截取逻辑（交给 memory 模块） |
| `app/web/static/index.html` | 前端重构：sidebar + session 管理 + 历史回显 |
| `app/feishu/bot.py` | 替换内存 dict 为 SessionStore（可延迟到一期后半） |
