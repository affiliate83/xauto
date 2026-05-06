"""
GitHub Actions 용 단건 트윗 발행 스크립트
KST 시간 기준으로 니치 자동 선택 후 큐에서 한 건 발행
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytz
import db
import poster.x_api as x_api
from utils import logger

KST = pytz.timezone('Asia/Seoul')
MONTHLY_LIMIT = 1400

HOUR_TO_NICHE = {
    7:  'parenting',
    10: 'welfare',
    12: 'finance',
    19: 'health',
    22: None,
}


def main():
    if not x_api.verify_credentials():
        logger.error("[중단] X API 인증 실패")
        sys.exit(1)

    monthly = db.monthly_post_count()
    if monthly >= MONTHLY_LIMIT:
        logger.warning(f"[월간 한도 초과] {monthly}/{MONTHLY_LIMIT} — 발행 중단")
        return

    now_kst = datetime.now(KST)
    hour = now_kst.hour
    preferred_niche = HOUR_TO_NICHE.get(hour)
    logger.info(f"[발행] KST {hour:02d}시 → 선호 니치: {preferred_niche or '없음'}")

    tweets = db.get_pending_tweets(limit=1, preferred_niche=preferred_niche)
    if not tweets:
        logger.info("[큐 비어있음] 발행할 트윗 없음")
        return

    tweet = tweets[0]
    tweet_id = x_api.post_tweet(tweet['tweet_text'])

    if tweet_id:
        db.mark_content_posted(tweet['tweet_text'])
        logger.info(f"[발행 성공] id={tweet_id}")
    else:
        db.mark_queue_status(tweet['id'], 'failed')
        logger.error(f"[발행 실패] row_id={tweet['id']}")


if __name__ == "__main__":
    main()
