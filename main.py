from fastapi import FastAPI, Request, HTTPException
from app.slack_verifier import verify_slack_request
from app.notion_client import create_slack_message_row
import os
import httpx
import re

app = FastAPI()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_API_BASE = "https://slack.com/api"

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    json_body = await request.json()

    # SlackのURL確認用
    if json_body.get("type") == "url_verification":
        return {"challenge": json_body["challenge"]}

    # 署名検証（ローカルテスト時はスキップOK）
    if timestamp and signature:
        if not verify_slack_request(timestamp, signature, body):
            raise HTTPException(status_code=403, detail="invalid signature")

    event = json_body.get("event", {})
    if event.get("type") == "reaction_added":
        reaction = event.get("reaction")
        if reaction == "notebook_with_decorative_cover":
            channel = event["item"]["channel"]
            ts = event["item"]["ts"]

            # --- ここから本番処理 ---
            headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}

            # test：ダミー値でOK（Notionに入るかテストするため）
            # await create_slack_message_row(
            #     author="dummy",
            #     text="dummy message",
            #     brain=0,
            #     bulb=0,
            #     footprints=0,
            #     comments="",
            #     message_url=f"https://your-workspace.slack.com/archives/{channel}/p{ts.replace('.', '')}",
            #     slide_url=None,
            # )

            async with httpx.AsyncClient() as client:
                # メッセージ内容を取得
                history_resp = await client.get(
                    f"{SLACK_API_BASE}/conversations.history",
                    params={"channel": channel, "latest": ts, "limit": 1, "inclusive": True},
                    headers=headers,
                )
                message = history_resp.json()["messages"][0]
                text = message.get("text", "")
                author_id = message.get("user", "")

                # 投稿者名を取得
                user_resp = await client.get(
                    f"{SLACK_API_BASE}/users.info",
                    params={"user": author_id},
                    headers=headers,
                )
                author_name = user_resp.json()["user"]["real_name"]

                # メッセージのパーマリンクを取得
                link_resp = await client.get(
                    f"{SLACK_API_BASE}/chat.getPermalink",
                    params={"channel": channel, "message_ts": ts},
                    headers=headers,
                )
                message_url = link_resp.json().get("permalink")

                # GoogleスライドURL抽出
                slide_url = _extract_slide_url(text)

            # Notionへ送信
            await create_slack_message_row(
                author=author_name,
                text=text,
                brain=0,
                bulb=0,
                footprints=0,
                comments="",
                message_url=message_url,
                slide_url=None,
            )

    return {"ok": True}

# GoogleスライドURLを抽出する関数
def _extract_slide_url(text: str):
    pattern = r"(https?://docs\.google\.com/presentation/[^\s>]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None