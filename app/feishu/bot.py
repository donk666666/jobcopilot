import json
import logging

from lark_oapi import Client
from lark_oapi.api.im.v1 import ReplyMessageRequest, ReplyMessageRequestBody

from app.config import settings
from app.agent.graph import run_agent

logger = logging.getLogger(__name__)

_session_store: dict[str, list[dict]] = {}


def handle_event(body: bytes, headers: dict) -> dict:
    """处理飞书事件回调，返回响应 JSON"""
    body_dict = json.loads(body)

    # URL 验证
    if body_dict.get("type") == "url_verification":
        challenge = body_dict.get("challenge", "")
        return {"challenge": challenge}

    # 消息事件
    event = body_dict.get("event", {})
    msg_type = event.get("message", {}).get("message_type", "")

    if msg_type == "text":
        content = json.loads(event.get("message", {}).get("content", "{}"))
        user_text = content.get("text", "")
        chat_id = event.get("message", {}).get("chat_id", "")
        msg_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")

        if user_text:
            session_id = f"feishu_{chat_id}"
            history = _session_store.get(session_id, [])

            result = run_agent(user_text, history=history)

            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": result["answer"]})
            _session_store[session_id] = history[-10:]

            # 异步回复
            try:
                _reply_message(msg_id, result["answer"])
            except Exception as e:
                logger.error(f"飞书回复失败: {e}")

    return {}


def _reply_message(msg_id: str, content: str):
    """通过飞书 API 回复消息"""
    client = Client.builder() \
        .app_id(settings.feishu_app_id) \
        .app_secret(settings.feishu_app_secret) \
        .build()

    body = ReplyMessageRequestBody()
    body.content = json.dumps({"text": content})
    body.msg_type = "text"

    request = ReplyMessageRequest()
    request.message_id = msg_id
    request.request_body = body

    client.im.v1.message.reply(request)
