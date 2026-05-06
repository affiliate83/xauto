"""육아/생활 기사 수집"""
import time
import hashlib
from utils import strip_html, logger
from sources import call_naver_news

KEYWORDS = [
    '육아 꿀팁', '아이 교육', '엄마 생활정보',
    '육아 절약', '아이 건강', '초등 엄마', '육아 커뮤니티'
]

_seen = set()


def fetch(max_per_keyword: int = 3) -> list[dict]:
    logger.info("[육아/생활] 기사 수집 중...")
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
                'niche': 'parenting',
                'title': title,
                'description': desc,
                'link': link,
                'pub_date': item.get('pubDate', ''),
            })
            count += 1
        time.sleep(2)
    logger.info(f"  [육아/생활] {len(results)}건 수집")
    return results