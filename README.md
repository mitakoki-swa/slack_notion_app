# 本アプリ概要
SlackとNotionを連携するアプリ。
Slackの投稿に`:notebook_with_decorative_cover:`スタンプを押すと下記要素がNotionに格納されるようになっている。
- 投稿者名
- 日付
- リアクションとその数
- コメント
- メッセージURL
- スライドURL

# 起動方法
- Slackのプライベートチャネルにて`/invite @genri_rikai_bot`でbotを招待
- ターミナルAで`uvicorn main:app --reload`を起動
- ターミナルBで`lt --port 8000`を起動
-- 上記によってローカルのFastAPIを外部から見れるようにしている
- `Slack APP > Event Subscriptions > Enable Events > Request URL`　を`lt --port 8000で出るURL/slack/events`に変更