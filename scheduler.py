"""
X Auto — 스케줄러 데몬
큐에서 트윗을 꺼내 KST 지정 시간에 자동 발행.
실행: python scheduler.py
종료: Ctrl+C
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import db
import main as pipeline
import poster.x_api as x_api
import image_maker.card as card_maker
from utils import logger

KST = pytz.timezone('Asia/Seoul')
MONTHLY_LIMIT = 1400  # X 무료 플랜 1,500건 중 100건 버퍼

# 발행 슬롯: 시간(KST) + 선호 니치
POSTING_SCHEDULE = [
    {'hour': 7,  'minute': 0,  'niche': 'parenting'},
    {'hour': 10, 'minute': 0,  'niche': 'welfare'},   # 복지혜택 — 오전 정보 탐색 시간대
    {'hour': 12, 'minute': 0,  'niche': 'finance'},
    {'hour': 19, 'minute': 0,  'niche': 'health'},
    {'hour': 22, 'minute': 0,  'niche': None},
]


def post_job(preferred_niche: str = None):
    logger.info(f"[스케줄] 발행 시도 (선호 니치: {preferred_niche or '없음'})")

    # 월간 한도 체크
    monthly = db.monthly_post_count()
    if monthly >= MONTHLY_LIMIT:
        logger.warning(f"[월간 한도 초과] {monthly}/{MONTHLY_LIMIT} — 발행 중단")
        return

    tweets = db.get_pending_tweets(limit=1, preferred_niche=preferred_niche)
    if not tweets:
        logger.info("  [큐 비어있음] 발행할 트윗 없음")
        return

    tweet = tweets[0]

    # 이미지 카드 생성
    card_path = None
    try:
        card_path = card_maker.make_card(
            niche=tweet['niche'],
            tweet_text=tweet['tweet_text'],
            card_id=str(tweet['id']),
        )
        logger.info(f"  [카드 생성] {card_path.name}")
    except Exception as e:
        logger.warning(f"  [카드 생성 실패, 텍스트만 발행] {e}")

    tweet_id = x_api.post_tweet(tweet['tweet_text'], image_path=card_path)

    if tweet_id:
        db.mark_content_posted(tweet['tweet_text'])
        logger.info(f"  [발행 성공] id={tweet_id}")
    else:
        db.mark_queue_status(tweet['id'], 'failed')
        logger.error(f"  [발행 실패] row_id={tweet['id']}")


def refill_job():
    logger.info("[스케줄] 큐 보충 시작")
    pipeline.run()


def start():
    if not x_api.verify_credentials():
        logger.error("[중단] X API 인증 실패 — .env의 X API 키를 확인하세요.")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=KST)

    for slot in POSTING_SCHEDULE:
        scheduler.add_job(
            post_job,
            CronTrigger(hour=slot['hour'], minute=slot['minute'], timezone=KST),
            kwargs={'preferred_niche': slot['niche']},
            id=f"post_{slot['hour']}h",
        )

    # 매일 06:00 KST 큐 보충
    scheduler.add_job(
        refill_job,
        CronTrigger(hour=6, minute=0, timezone=KST),
        id='pipeline_refill',
    )

    logger.info("스케줄러 시작 — 발행 슬롯: 07:00 / 12:00 / 19:00 / 22:00 KST")
    logger.info("종료하려면 Ctrl+C 를 누르세요.")
    scheduler.start()


if __name__ == "__main__":
    start()