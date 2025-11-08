import httpx
from app.config import NOTION_API_KEY, NOTION_DATABASE_ID

NOTION_API_BASE = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"

async def create_slack_message_row(
    author: str,
    text: str,
    brain: int,
    bulb: int,
    footprints: int,
    comments: str,
    message_url: str,
    slide_url: str | None = None,
    date: str | None = None,
):
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

    props = {
        "Message": {
            "title": [{"text": {"content": text[:100] or "Slack message"}}]
        },
        "Author": {"rich_text": [{"text": {"content": author}}]},
        "Brain": {"number": brain},
        "Bulb": {"number": bulb},
        "Footprints": {"number": footprints},
        "Comments": {"rich_text": [{"text": {"content": comments}}]},
        "Message URL": {"url": message_url},
    }

    if slide_url:
        props["Slide URL"] = {"url": slide_url}
    if date:
        props["日付"] = {"date": {"start": date}}

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": props,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(NOTION_API_BASE, headers=headers, json=data)
        if r.status_code != 200:
            # ★ここで中身を見る
            print("Notion error:", r.status_code, r.text)
        r.raise_for_status()
        return r.json()