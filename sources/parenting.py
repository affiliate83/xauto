"""육아/생활 기사 수집 + 본문 스크래핑"""
import time
import hashlib
from utils import strip_html, logger
from sources import call_naver_news, fetch_article_body

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
            desc  = strip_html(item.get('description', ''))
            naver_url    = item.get('link', '')
            original_url = item.get('originallink') or naver_url
            if not title or not naver_url:
                continue
            key = hashlib.md5(f"{title}|{original_url}".encode()).hexdigest()
            if key in _seen:
                continue
            _seen.add(key)

            # 기사 본문 스크래핑 (네이버 뷰어 URL 사용)
            body = fetch_article_body(naver_url)
            description = body if len(body) > len(desc) else desc

            results.append({
                'niche': 'parenting',
                'title': title,
                'description': description,
                'link': original_url,
                'pub_date': item.get('pubDate', ''),
            })
            count += 1
            time.sleep(1)   # 본문 스크래핑 후 딜레이

        time.sleep(2)   # 키워드 간 딜레이
    logger.info(f"  [육아/생활] {len(results)}건 수집")
    return results
