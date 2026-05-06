"""
X Auto — 콘텐츠 파이프라인
기사/복지 수집 → 트윗 생성 → 큐 저장 (발행은 scheduler.py 담당)
실행: python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db
import sources.parenting as parenting
import sources.finance as finance
import sources.health as health
import sources.welfare as welfare
import generator.writer as writer
from utils import logger

MIN_QUEUE = 8
MAX_QUEUE = 25


def run():
    logger.info("=" * 50)
    logger.info("X Auto — 콘텐츠 파이프라인 시작")
    logger.info("=" * 50)

    depth = db.queue_depth()
    logger.info(f"현재 큐: {depth}개 대기 중")

    if depth >= MAX_QUEUE:
        logger.info("큐가 가득 참 — 생성 건너뜀")
        return

    # 1. 수집 (뉴스 3니치 + 복지혜택)
    all_articles = []
    all_articles += parenting.fetch()
    all_articles += finance.fetch()
    all_articles += health.fetch()
    all_articles += welfare.fetch(max_items=100)
    logger.info(f"전체 수집 완료: {len(all_articles)}건")

    # 2. Claude로 트윗 생성
    generated = writer.generate_batch(all_articles)
    logger.info(f"트윗 생성 완료: {len(generated)}건")

    # 3. 중복 제거 후 큐 저장
    queued = 0
    for item in generated:
        if db.is_content_duplicate(item['tweet_text']):
            logger.info(f"  [중복 건너뜀] {item['tweet_text'][:30]}")
            continue
        db.enqueue_tweet(
            niche=item['niche'],
            tweet_text=item['tweet_text'],
            source_title=item['source_title'],
            source_link=item['source_link'],
        )
        # 복지 서비스는 source_id도 마킹 (API 재수집 방지)
        if item.get('service_id'):
            db.mark_source_posted(item['service_id'])
        queued += 1

    logger.info(f"큐 추가: {queued}건 | 현재 큐 크기: {db.queue_depth()}건")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
