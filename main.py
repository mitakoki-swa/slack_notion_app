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

                # スタンプの数取得
                brain, bulb, footprints = await _get_reaction_counts(client, channel, ts, headers)

                # GoogleスライドURL抽出
                slide_url = _extract_slide_url(text)

                # コメントを抽出
                comments = await _get_thread_comments(client, channel, ts, headers)

            # Notionへ送信
            await create_slack_message_row(
                author=author_name,
                text=text,
                brain=brain,
                bulb=bulb,
                footprints=footprints,
                comments=comments,
                message_url=message_url,
                slide_url=slide_url,
            )

    return {"ok": True}

# GoogleスライドURLを抽出する関数
def _extract_slide_url(text: str):
    pattern = r"(https?://docs\.google\.com/presentation/[^\s>]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None

# スタンプの数を取ってくる関数
async def _get_reaction_counts(client: httpx.AsyncClient, channel: str, ts: str, headers: dict):
    """
    指定メッセージのリアクション一覧をSlackから取得して
    brain / bulb / footprints の数だけ返す
    """
    resp = await client.get(
        f"{SLACK_API_BASE}/reactions.get",
        params={"channel": channel, "timestamp": ts},
        headers=headers,
    )
    data = resp.json()

    brain = bulb = footprints = 0

    # reactions.get に成功していれば message.reactions がある
    if data.get("ok") and "message" in data and "reactions" in data["message"]:
        for r in data["message"]["reactions"]:
            name = r.get("name")
            count = r.get("count", 0)
            if name == "brain":
                brain = count
            elif name == "bulb":
                bulb = count
            elif name == "footprints":
                footprints = count

    return brain, bulb, footprints

async def _get_thread_comments(
    client: httpx.AsyncClient, channel: str, ts: str, headers: dict
) -> str:
    """
    特定メッセージのスレッド内コメントを取得し、
    「ユーザー名: コメント内容」を改行区切りで連結して返す
    """
    comments_text = []

    # スレッド（リプライ）を取得
    resp = await client.get(
        f"{SLACK_API_BASE}/conversations.replies",
        params={"channel": channel, "ts": ts},
        headers=headers,
    )
    data = resp.json()

    if not data.get("ok"):
        return ""

    messages = data.get("messages", [])
    if len(messages) <= 1:
        # 親メッセージしかない（コメントなし）
        return ""

    # 親メッセージ以外（2つ目以降）がコメント
    for msg in messages[1:]:
        user_id = msg.get("user")
        text = msg.get("text", "").strip()

        # 投稿者名を取得
        user_name = None
        if user_id:
            user_resp = await client.get(
                f"{SLACK_API_BASE}/users.info",
                params={"user": user_id},
                headers=headers,
            )
            if user_resp.json().get("ok"):
                user_name = user_resp.json()["user"]["real_name"]

        if user_name and text:
            comments_text.append(f"{user_name}: {text}")
        elif text:
            comments_text.append(text)

    # 改行でつなげる
    return "\n".join(comments_text)