"""Claude Haiku로 X 트윗 생성"""
import os
import re
import time
import anthropic
from dotenv import load_dotenv
from utils import logger, truncate_to_x_limit
from generator.prompts import NICHE_PROMPTS

load_dotenv()

_FENCE_RE = re.compile(r'```[^\n`]*\n?|```\s*$', re.MULTILINE)

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


def generate_tweet(niche: str, title: str, description: str, link: str = '') -> str | None:
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
            max_tokens=450,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text.strip()
        text = _FENCE_RE.sub('', text).strip()
        text = truncate_to_x_limit(text)
        logger.info(f"  [트윗 생성] {len(text)}자 | {text[:40]}...")
        return text
    except Exception as e:
        logger.warning(f"  [Claude 생성 실패] {e}")
        return None


def generate_batch(articles: list[dict]) -> list[dict]:
    results = []
    for article in articles:
        tweet_text = generate_tweet(
            niche=article['niche'],
            title=article['title'],
            description=article['description'],
            link=article.get('link', ''),
        )
        if tweet_text:
            results.append({
                'niche':      article['niche'],
                'tweet_text': tweet_text,
                'source_title': article['title'],
                'source_link':  article.get('link', ''),
                'service_id':   article.get('service_id', ''),  # welfare용
            })
        time.sleep(3)
    return results
