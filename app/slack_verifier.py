import hmac
import hashlib
import time

from app.config import SLACK_SIGNING_SECRET

def verify_slack_request(timestamp: str, signature: str, body: bytes) -> bool:
    # リプレイ攻撃防止（5分より古かったら弾く）
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:{body.decode()}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)