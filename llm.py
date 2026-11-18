import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI


# 明确读取当前项目目录中的 .env
load_dotenv(Path(__file__).parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise RuntimeError("请先在 .env 中配置 DEEPSEEK_API_KEY")


client = AsyncOpenAI(
    api_key=api_key,
    base_url=os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
    ),
    timeout=60.0,
    max_retries=0,
)

SYSTEM_PROMPT = """
你是企业 IT 服务台助手，帮助员工处理：
1. 电脑、手机、打印机等设备故障；
2. 系统账号与权限申请；
3. 网络、Wi-Fi 和 VPN 问题；
4. 办公软件安装与更新。

回答要求：
- 使用中文，简洁清楚。
- 信息不足时，先问最关键的一个问题。
- 排障从低风险步骤开始。
- 不索取密码、验证码或密钥。
- 不编造企业政策、审批地址或处理时限。
- 当前没有接入资产、权限和工单系统，
  不要声称已经查询资产、开通权限或创建工单。
"""


async def ask_llm(
    message: str,
    role_prompt: str = "",
    history: list = None,
) -> str:
    response = await client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\n\n" + role_prompt,
            },
            *(history or []),
            {
                "role": "user",
                "content": message,
            },
        ],
        max_tokens=1000,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("模型没有返回回答内容")

    return content