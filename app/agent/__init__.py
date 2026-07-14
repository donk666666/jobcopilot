from typing_extensions import TypedDict
from typing import Annotated


class RetrievedDoc(TypedDict):
    content: str
    source: str
    score: float


class AgentState(TypedDict):
    messages: Annotated[list, "对话历史"]
    intent: str
    rewritten_query: str
    retrieved_docs: list[RetrievedDoc]
    final_answer: str
    need_clarify: bool
