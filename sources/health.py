"""건강/다이어트 기사 수집"""
import time
import hashlib
from utils import strip_html, logger
from sources import call_naver_news

KEYWORDS = [
    '다이어트 식단', '건강 꿀팁', '여성 건강', '홈트레이닝',
    '간헐적 단식', '건강 식품', '다이어트 성공', '체중 감량'
]

_seen = set()


def fetch(max_per_keyword: int = 3) -> list[dict]:
    logger.info("[건강/다이어트] 기사 수집 중...")
    results = []
    for keyword in KEYWORDS:
        items = call_naver_news(keyword, display=max_per_keyword + 2)
        count = 0
        for item in items:
            if count >= max_per_keyword:
                break
            title = strip_html(item.get('title', ''))
            desc = strip_html(item.get('description', ''))
            link = item.get('originallink') or item.get('link', '')
            if not title or not link:
                continue
            key = hashlib.md5(f"{title}|{link}".encode()).hexdigest()
            if key in _seen:
                continue
            _seen.add(key)
            results.append({
                'niche': 'health',
                'title': title,
                'description': desc,
                'link': link,
                'pub_date': item.get('pubDate', ''),
            })
            count += 1
        time.sleep(2)
    logger.info(f"  [건강/다이어트] {len(results)}건 수집")
    return results