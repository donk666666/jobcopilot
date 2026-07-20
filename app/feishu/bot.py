import json
import logging
import threading

from lark_oapi import Client
from lark_oapi.api.im.v1 import (
    ReplyMessageRequest,
    ReplyMessageRequestBody,
    CreateMessageRequest,
    CreateMessageRequestBody,
)

from app.config import settings
from app.agent.graph import run_agent
from app.session_store import SessionStore
from app.memory import build_context

logger = logging.getLogger(__name__)

_store = SessionStore()


def handle_event(body: bytes, headers: dict) -> dict:
    """处理飞书事件回调，返回响应 JSON（同步部分仅做校验和快速响应）"""
    body_dict = json.loads(body)

    if body_dict.get("type") == "url_verification":
        challenge = body_dict.get("challenge", "")
        return {"challenge": challenge}

    event = body_dict.get("event", {})
    msg_type = event.get("message", {}).get("message_type", "")

    if msg_type == "text":
        content = json.loads(event.get("message", {}).get("content", "{}"))
        user_text = content.get("text", "")
        chat_id = event.get("message", {}).get("chat_id", "")
        msg_id = event.get("message", {}).get("message_id", "")
        root_id = event.get("message", {}).get("root_id", "")
        thread_id = msg_id if not root_id else root_id

        if user_text and msg_id and chat_id:
            threading.Thread(
                target=_process_and_reply,
                args=(user_text, chat_id, msg_id, thread_id),
                daemon=True,
            ).start()

    return {}


def _process_and_reply(user_text: str, chat_id: str, msg_id: str, thread_id: str):
    """后台线程：先发"处理中"，再跑 Agent + 回复答案"""
    logger.info(f"收到飞书消息: chat_id={chat_id}, text={user_text[:50]}...")

    _reply_message(msg_id, "处理中，请稍候...")

    try:
        session_id = f"feishu_{chat_id}"
        history = _store.get_history(session_id)

        if not history:
            title = user_text[:20].replace("\n", " ")
            _store.create_session(session_id, title)

        context_msgs, _ = build_context(session_id, _store, history)
        result = run_agent(user_text, context=context_msgs)

        _store.add_message(session_id, "user", user_text)
        _store.add_message(session_id, "assistant", result["answer"])

        if thread_id and thread_id != msg_id:
            _reply_message(thread_id, result["answer"])
        else:
            _send_message(chat_id, result["answer"])
    except Exception as e:
        logger.error(f"飞书消息处理失败: {e}")
        _send_message(chat_id, f"处理失败: {str(e)[:100]}")


def _reply_message(msg_id: str, content: str):
    logger.info(f"回复消息 msg_id={msg_id}, content_len={len(content)}")
    try:
        client = Client.builder() \
            .app_id(settings.feishu_app_id) \
            .app_secret(settings.feishu_app_secret) \
            .build()

        body = ReplyMessageRequestBody()
        body.content = json.dumps({"text": content})
        body.msg_type = "text"

        request = ReplyMessageRequest.builder() \
            .message_id(msg_id) \
            .request_body(body) \
            .build()

        response = client.im.v1.message.reply(request)
        logger.info(f"回复成功: code={response.code}")
    except Exception as e:
        logger.error(f"回复失败: {e}", exc_info=True)


def _send_message(chat_id: str, content: str):
    logger.info(f"发送消息 chat_id={chat_id}, content_len={len(content)}")
    try:
        client = Client.builder() \
            .app_id(settings.feishu_app_id) \
            .app_secret(settings.feishu_app_secret) \
            .build()

        body = CreateMessageRequestBody()
        body.content = json.dumps({"text": content})
        body.msg_type = "text"
        body.receive_id = chat_id

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(body) \
            .build()

        response = client.im.v1.message.create(request)
        logger.info(f"发送成功: code={response.code}")
    except Exception as e:
        logger.error(f"发送失败: {e}", exc_info=True)
