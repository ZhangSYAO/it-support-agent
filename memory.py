from copy import deepcopy


# 本地内存：服务重启后清空
CONVERSATIONS = {}

# 最多保留最近 6 轮对话，即 12 条消息
MAX_MESSAGES = 12


def get_conversation(conversation_id: str) -> dict:
    state = CONVERSATIONS.get(conversation_id)

    if state is None:
        return {
            "history": [],
            "entities": {},
            "intent": None,
        }

    # 返回副本，本轮失败时不修改原记录
    return deepcopy(state)


def save_conversation(
    conversation_id: str,
    state: dict,
    message: str,
    reply: str,
) -> None:
    state["history"].extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ])

    state["history"] = state["history"][-MAX_MESSAGES:]

    CONVERSATIONS[conversation_id] = deepcopy(state)