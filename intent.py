from enum import Enum


class IntentCategory(str, Enum):
    DEVICE_FAILURE = "device_failure"
    PERMISSION_REQUEST = "permission_request"
    NETWORK_ISSUE = "network_issue"
    SOFTWARE_INSTALL = "software_install"
    IT_ESCALATION = "it_escalation"
    OTHER = "other"


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def recognize_intent(message: str) -> IntentCategory:
    text = message.lower().strip()

    # 1. 明确要求提交 IT 工单
    wants_ticket = contains_any(
        text,
        ("创建工单", "创建 it 工单", "提交工单", "转 it", "转it"),
    )
    cancels_ticket = contains_any(
        text,
        ("不要", "不用", "取消", "暂不", "如何", "怎么"),
    )

    if wants_ticket and not cancels_ticket:
        return IntentCategory.IT_ESCALATION

    # 2. 安装或更新软件
    software_action = contains_any(text, ("安装", "更新", "升级"))
    software_target = contains_any(
        text,
        ("软件", "office", "vpn", "客户端", "驱动"),
    )

    if software_action and software_target:
        return IntentCategory.SOFTWARE_INSTALL

    # 3. 账号或权限申请
    permission_action = contains_any(text, ("申请", "开通", "授权"))
    permission_target = contains_any(
        text,
        ("权限", "账号", "账户", "vpn", "系统", "数据库"),
    )

    if permission_action and permission_target:
        return IntentCategory.PERMISSION_REQUEST

    # 4. 网络与 VPN 问题
    if contains_any(
        text,
        ("网络", "断网", "wi-fi", "wifi", "无线网", "vpn"),
    ):
        return IntentCategory.NETWORK_ISSUE

    # 5. 硬件设备问题
    device = contains_any(
        text,
        ("电脑", "笔记本", "打印机", "手机", "显示器"),
    )
    failure = contains_any(
        text,
        ("故障", "坏了", "无法开机", "开不了机", "黑屏", "蓝屏", "卡纸"),
    )

    if device and failure:
        return IntentCategory.DEVICE_FAILURE

    return IntentCategory.OTHER