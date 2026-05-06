"""Claude Haiku로 X 스레드 생성 — WP_CRAWLER_ENRICHMENT_GUIDE 패턴 적용"""
import os
import re
import time
import json
import anthropic
from dotenv import load_dotenv
from utils import logger, truncate_to_x_limit
from generator.prompts import NICHE_PROMPTS

load_dotenv()

# 코드 펜스 제거 (가이드: 프롬프트 명시 + 이중 안전망)
_FENCE_RE = re.compile(r'```[^\n`]*\n?|```\s*$', re.MULTILINE)
# [TWEET1] ~ [TWEET4] 마커 분리
_MARKER_RE = re.compile(r'\[TWEET\d\]', re.IGNORECASE)

_client = None


def _get_client() -> anthropic.Anthropic | None:
    global _client
    if _client is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("[오류] ANTHROPIC_API_KEY가 .env에 없습니다.")
            return None
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _parse_thread(text: str) -> list[str]:
    """마커 줄 기준 스레드 분리 — [TWEET1] 또는 TWEET1 단독 줄 모두 처리"""
    text = _FENCE_RE.sub('', text).strip()
    lines = text.split('\n')
    tweets = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if re.match(r'^\[?TWEET\s*\d+\]?$', stripped, re.IGNORECASE):
            if current:
                tweet = '\n'.join(current).strip()
                if tweet:
                    tweets.append(truncate_to_x_limit(tweet, limit=270))
            current = []
        else:
            current.append(line)

    if current:
        tweet = '\n'.join(current).strip()
        if tweet:
            tweets.append(truncate_to_x_limit(tweet, limit=270))

    return tweets


def generate_thread(niche: str, title: str, description: str, link: str = '') -> list[str] | None:
    """스레드 형식 트윗 생성 (4개 연결 트윗)"""
    client = _get_client()
    if client is None:
        return None

    prompt_template = NICHE_PROMPTS.get(niche)
    if not prompt_template:
        logger.warning(f"  [알 수 없는 니치] {niche}")
        return None

    prompt = prompt_template.format(title=title, description=description, link=link)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text.strip()
        tweets = _parse_thread(text)

        if len(tweets) < 2:
            # 마커 파싱 실패 → 단일 트윗으로 fallback
            single = _FENCE_RE.sub('', text).strip()
            single = truncate_to_x_limit(single)
            logger.info(f"  [단일 트윗 fallback] {len(single)}자 | {single[:40]}...")
            return [single]

        logger.info(f"  [스레드 생성] {len(tweets)}개 | {tweets[0][:40]}...")
        return tweets

    except Exception as e:
        logger.warning(f"  [Claude 생성 실패] {e}")
        return None


def generate_batch(articles: list[dict]) -> list[dict]:
    results = []
    for article in articles:
        threads = generate_thread(
            niche=article['niche'],
            title=article['title'],
            description=article['description'],
            link=article.get('link', ''),
        )
        if threads:
            results.append({
                'niche':        article['niche'],
                'tweet_text':   json.dumps(threads, ensure_ascii=False),
                'source_title': article['title'],
                'source_link':  article.get('link', ''),
                'service_id':   article.get('service_id', ''),
            })
        time.sleep(3)
    return results
