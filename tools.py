import hashlib
import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# 本地演示资产，不代表真实企业数据
DEMO_ASSETS = {
    "PC-2026-001": {
        "device_id": "PC-2026-001",
        "device_type": "笔记本电脑",
        "model": "演示型号 A",
        "os_version": "Windows 11",
        "warranty_status": "演示：保修期内",
    },
    "PR-2026-001": {
        "device_id": "PR-2026-001",
        "device_type": "打印机",
        "model": "演示型号 B",
        "os_version": None,
        "warranty_status": "演示：保修状态未知",
    },
}


def lookup_asset(device_id: str) -> dict:
    normalized_id = device_id.strip().upper()
    asset = DEMO_ASSETS.get(normalized_id)

    if asset is None:
        return {
            "success": False,
            "source": "local_demo",
            "error": "本地演示资产表中没有这个设备编号",
        }

    return {
        "success": True,
        "source": "local_demo",
        "asset": dict(asset),
    }

TICKET_DB = Path(__file__).parent / "tickets.db"


def create_ticket(
    conversation_id: str,
    description: str,
    entities: dict,
) -> dict:
    description = description.strip()

    if not description:
        return {
            "success": False,
            "source": "local_demo_ticket",
            "error": "缺少问题描述，未创建演示工单",
        }

    # 同会话、同描述、同实体的重复提交复用原工单
    request_data = json.dumps(
        {
            "conversation_id": conversation_id,
            "description": description,
            "entities": entities,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    request_key = hashlib.sha256(
        request_data.encode("utf-8")
    ).hexdigest()

    ticket_id = "DEMO-" + uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(TICKET_DB, timeout=10) as connection:
            connection.row_factory = sqlite3.Row

            connection.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    request_key TEXT NOT NULL UNIQUE,
                    conversation_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    entities_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            connection.execute(
                """
                INSERT OR IGNORE INTO tickets (
                    ticket_id,
                    request_key,
                    conversation_id,
                    description,
                    entities_json,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    request_key,
                    conversation_id,
                    description,
                    json.dumps(entities, ensure_ascii=False),
                    "open",
                    created_at,
                ),
            )

            row = connection.execute(
                """
                SELECT ticket_id, status, created_at
                FROM tickets
                WHERE request_key = ?
                """,
                (request_key,),
            ).fetchone()

            result = dict(row)

        return {
            "success": True,
            "source": "local_demo_ticket",
            "ticket_id": result["ticket_id"],
            "status": result["status"],
            "created_at": result["created_at"],
            "reused": result["ticket_id"] != ticket_id,
        }

    except sqlite3.Error:
        return {
            "success": False,
            "source": "local_demo_ticket",
            "error": "本地工单数据库操作失败，请检查目录写入权限",
        }

def get_ticket(ticket_id: str) -> dict:
    ticket_id = ticket_id.strip()

    if not TICKET_DB.exists():
        return {
            "success": False,
            "source": "local_demo_ticket",
            "error_code": "not_found",
            "error": "尚无本地工单记录",
        }

    try:
        with sqlite3.connect(TICKET_DB, timeout=10) as connection:
            connection.row_factory = sqlite3.Row

            row = connection.execute(
                """
                SELECT
                    ticket_id,
                    conversation_id,
                    description,
                    entities_json,
                    status,
                    created_at
                FROM tickets
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            ).fetchone()

        if row is None:
            return {
                "success": False,
                "source": "local_demo_ticket",
                "error_code": "not_found",
                "error": "没有找到对应的本地演示工单",
            }

        ticket = dict(row)

        # 数据库存的是 JSON 字符串，返回时转换成字典
        ticket["entities"] = json.loads(
            ticket.pop("entities_json")
        )

        return {
            "success": True,
            "source": "local_demo_ticket",
            "ticket": ticket,
        }

    except (sqlite3.Error, json.JSONDecodeError):
        return {
            "success": False,
            "source": "local_demo_ticket",
            "error_code": "storage_error",
            "error": "本地工单读取失败，请检查数据库",
        }



def update_ticket_status(
    ticket_id: str,
    new_status: str,
) -> dict:
    ticket_id = ticket_id.strip()

    allowed_transitions = {
        "open": "in_progress",
        "in_progress": "resolved",
    }

    if new_status not in ("open", "in_progress", "resolved"):
        return {
            "success": False,
            "error_code": "invalid_status",
            "error": "不支持的工单状态",
        }

    if not TICKET_DB.exists():
        return {
            "success": False,
            "error_code": "not_found",
            "error": "尚无本地工单记录",
        }

    try:
        with sqlite3.connect(TICKET_DB, timeout=10) as connection:
            row = connection.execute(
                "SELECT status FROM tickets WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()

            if row is None:
                return {
                    "success": False,
                    "error_code": "not_found",
                    "error": "没有找到对应的本地演示工单",
                }

            old_status = row[0]

            # 重复提交相同状态，不重复更新
            if old_status == new_status:
                return {
                    "success": True,
                    "source": "local_demo_ticket",
                    "ticket_id": ticket_id,
                    "previous_status": old_status,
                    "status": new_status,
                    "changed": False,
                }

            if allowed_transitions.get(old_status) != new_status:
                return {
                    "success": False,
                    "error_code": "invalid_transition",
                    "error": (
                        f"不允许从 {old_status} 更新为 {new_status}，"
                        "请按 open → in_progress → resolved 的顺序操作"
                    ),
                }

            # 只有状态仍与刚才读取的一致，才执行更新
            cursor = connection.execute(
                """
                UPDATE tickets
                SET status = ?
                WHERE ticket_id = ? AND status = ?
                """,
                (new_status, ticket_id, old_status),
            )

            if cursor.rowcount != 1:
                return {
                    "success": False,
                    "error_code": "conflict",
                    "error": "工单状态已被其他请求修改，请重新查询",
                }

        # 离开 with 后，数据库修改已提交
        return {
            "success": True,
            "source": "local_demo_ticket",
            "ticket_id": ticket_id,
            "previous_status": old_status,
            "status": new_status,
            "changed": True,
        }

    except sqlite3.Error:
        return {
            "success": False,
            "error_code": "storage_error",
            "error": "工单状态更新失败，请检查数据库",
        }