from pathlib import Path
from fastapi.responses import FileResponse

from fastapi import FastAPI, HTTPException
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from typing import Literal
from tools import update_ticket_status
from pydantic import BaseModel, Field
from tools import get_ticket
from agents import run_agent
from intent import recognize_intent
from entities import extract_entities
from uuid import uuid4
from typing import Optional

from intent import IntentCategory
from memory import get_conversation, save_conversation

app = FastAPI(title="IT Support Agent")

class TicketStatusRequest(BaseModel):
    status: Literal["open", "in_progress", "resolved"]

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="消息不能为空",
        )


    conversation_id = request.conversation_id or uuid4().hex
    state = get_conversation(conversation_id)

    current_intent = recognize_intent(message)
    current_entities = extract_entities(message)

    # 本轮没有识别到明确意图，沿用之前的处理类型
    intent = current_intent

    if current_intent == IntentCategory.OTHER:
        previous_intent = state["intent"]

        # 不自动沿用工单升级意图
        if previous_intent not in (
                None,
                IntentCategory.IT_ESCALATION,
        ):
            intent = previous_intent


    # 转工单需要保留之前的问题背景
    if current_intent not in (
            IntentCategory.OTHER,
            IntentCategory.IT_ESCALATION,
    ):
        if state["intent"] not in (None, current_intent):
            state = {
                "history": [],
                "entities": {},
                "intent": None,
            }

    entities = dict(state["entities"])

    # 换设备后，清除旧设备编号和系统版本
    new_device_id = current_entities.get("device_id")
    old_device_id = entities.get("device_id")

    if (
            new_device_id
            and old_device_id
            and new_device_id.upper() != old_device_id.upper()
    ):
        entities.pop("device_id", None)
        entities.pop("os_version", None)
        state["history"] = []

    # 本轮明确提供的新值优先
    for key, value in current_entities.items():
        if value is not None:
            entities[key] = value

    # 普通对话更新后，下次升级重新整理问题描述
    if current_intent != IntentCategory.IT_ESCALATION:
        state.pop("ticket_description", None)

    ticket_description = state.get("ticket_description", "")

    if intent == IntentCategory.IT_ESCALATION:
        if not ticket_description:
            problem_messages = [
                item["content"]
                for item in state["history"]
                if item["role"] == "user"
                and recognize_intent(
                    item["content"]
                ) != IntentCategory.IT_ESCALATION
            ]

            ticket_description = "\n".join(problem_messages)

        if ticket_description:
            state["ticket_description"] = ticket_description
    tool_calls = []

    try:
        agent_name, reply = await run_agent(
            message,
            intent,
            tool_calls=tool_calls,
            history=state["history"],
            entities=entities,
            conversation_id=conversation_id,
            ticket_description=ticket_description,
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=502,
            detail="模型认证失败，请检查 API Key",
        ) from None

    except RateLimitError:
        raise HTTPException(
            status_code=503,
            detail="模型请求受限，请检查额度或稍后重试",
        ) from None

    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="模型响应超时，请稍后重试",
        ) from None

    except APIConnectionError:
        raise HTTPException(
            status_code=502,
            detail="无法连接模型服务，请检查网络和接口地址",
        ) from None

    except APIStatusError:
        raise HTTPException(
            status_code=502,
            detail="模型服务返回错误，请检查模型名称与服务状态",
        ) from None

    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="模型未返回有效回答",
        ) from None


    # 工单升级是一个动作，不覆盖原来的故障类型
    if intent != IntentCategory.IT_ESCALATION:
        state["intent"] = intent
    state["entities"] = entities

    save_conversation(
        conversation_id,
        state,
        message,
        reply,
    )

    return {
        "conversation_id": conversation_id,
        "intent": intent.value,
        "agent": agent_name,
        "entities": {
            "device_id": entities.get("device_id"),
            "employee_id": entities.get("employee_id"),
            "os_version": entities.get("os_version"),
        },
        "tool_calls": tool_calls,
        "reply": reply,
    }

@app.get("/debug/intent")
def debug_intent(message: str = "我要申请开通 VPN 权限"):
    return {
        "version": "intent-v2",
        "file": __file__,
        "intent": recognize_intent(message).value,
    }
@app.get("/tickets/{ticket_id}")
def query_ticket(ticket_id: str):
    result = get_ticket(ticket_id)

    if not result["success"]:
        status_code = (
            404
            if result["error_code"] == "not_found"
            else 500
        )

        raise HTTPException(
            status_code=status_code,
            detail=result["error"],
        )

    return result

@app.get("/", response_class=FileResponse)
def home():
    page_path = Path(__file__).parent / "index.html"

    if not page_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="项目根目录下没有找到 index.html",
        )

    return FileResponse(
        page_path,
        media_type="text/html",
    )


@app.patch("/tickets/{ticket_id}/status")
def change_ticket_status(
    ticket_id: str,
    request: TicketStatusRequest,
):
    result = update_ticket_status(
        ticket_id,
        request.status,
    )

    if not result["success"]:
        status_codes = {
            "not_found": 404,
            "invalid_status": 400,
            "invalid_transition": 409,
            "conflict": 409,
            "storage_error": 500,
        }

        raise HTTPException(
            status_code=status_codes.get(
                result["error_code"],
                500,
            ),
            detail=result["error"],
        )

    return result