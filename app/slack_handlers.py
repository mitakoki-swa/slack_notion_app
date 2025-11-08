import httpx

TARGET_REACTION = "notebook_with_decorative_cover"
COUNT_REACTIONS = {
    "brain": "🧠:brain: リアクション",
    "bulb": "💡:bulb: リアクション",
    "footprints": "🚶:footprints: リアクション",
}

async def fetch_message(token: str, channel: str, ts: str):
    url = "https://slack.com/api/conversations.replies"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"channel": channel, "ts": ts}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, params=params)
        data = r.json()
        return data  # messagesのリストが返る
