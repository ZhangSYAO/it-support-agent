import json
from pathlib import Path


KNOWLEDGE_PATH = Path(__file__).parent / "knowledge.json"


def search_knowledge_base(query: str, top_k: int = 2) -> dict:
    with KNOWLEDGE_PATH.open("r", encoding="utf-8") as file:
        documents = json.load(file)

    query = query.lower()
    matches = []

    for document in documents:
        # 每命中一个关键词，得一分
        score = sum(
            1
            for keyword in document["keywords"]
            if keyword.lower() in query
        )

        if score > 0:
            matches.append({
                "id": document["id"],
                "title": document["title"],
                "content": document["content"],
                "score": score,
            })

    matches.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return {
        "success": True,
        "source": "local_demo_knowledge",
        "results": matches[:top_k],
    }