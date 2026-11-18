import re


def first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return None


def extract_entities(message: str) -> dict[str, str | None]:
    device_id = first_match(
        r"(?:设备编号|设备号|资产编号|资产号)"
        r"\s*[:：]?\s*([A-Za-z0-9_-]{2,64})",
        message,
    )

    employee_id = first_match(
        r"(?:工号|员工编号)"
        r"\s*[:：]?\s*([A-Za-z0-9_-]{2,32})",
        message,
    )

    os_version = first_match(
        r"\b("
        r"Windows\s*(?:10|11)(?:\s+\d{2}H[12])?"
        r"|macOS\s*\d+(?:\.\d+){0,2}"
        r"|Ubuntu\s*\d+\.\d+(?:\.\d+)?"
        r"|Android\s*\d+(?:\.\d+){0,2}"
        r"|iOS\s*\d+(?:\.\d+){0,2}"
        r")\b",
        message,
    )

    return {
        "device_id": device_id,
        "employee_id": employee_id,
        "os_version": os_version,
    }