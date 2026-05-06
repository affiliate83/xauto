"""재테크/절약 기사 수집 + 본문 스크래핑"""
import time
import hashlib
from utils import strip_html, logger
from sources import call_naver_news, fetch_article_body

KEYWORDS = [
    '재테크 꿀팁', '절약 생활', '짠테크', '가계부 절약',
    '주부 재테크', '생활비 절약', '적금 꿀팁', '소비 줄이기'
]

_seen = set()


def fetch(max_per_keyword: int = 3) -> list[dict]:
    logger.info("[재테크/절약] 기사 수집 중...")
    results = []
    for keyword in KEYWORDS:
        items = call_naver_news(keyword, display=max_per_keyword + 2)
        count = 0
        for item in items:
            if count >= max_per_keyword:
                break
            title = strip_html(item.get('title', ''))
            desc  = strip_html(item.get('description', ''))
            naver_url    = item.get('link', '')
            original_url = item.get('originallink') or naver_url
            if not title or not naver_url:
                continue
            key = hashlib.md5(f"{title}|{original_url}".encode()).hexdigest()
            if key in _seen:
                continue
            _seen.add(key)

            body = fetch_article_body(naver_url)
            description = body if len(body) > len(desc) else desc

            results.append({
                'niche': 'finance',
                'title': title,
                'description': description,
                'link': original_url,
                'pub_date': item.get('pubDate', ''),
            })
            count += 1
            time.sleep(1)

        time.sleep(2)
    logger.info(f"  [재테크/절약] {len(results)}건 수집")
    return results
