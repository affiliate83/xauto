"""Naver News API 공통 헬퍼 + 기사 본문 스크래퍼"""
import os
import requests
from dotenv import load_dotenv
from utils import logger

load_dotenv()

_NAVER_ID = os.getenv('NAVER_CLIENT_ID')
_NAVER_SECRET = os.getenv('NAVER_CLIENT_SECRET')

_SCRAPE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}


def call_naver_news(query: str, display: int = 10) -> list[dict]:
    if not _NAVER_ID or not _NAVER_SECRET:
        logger.error("[오류] 네이버 API 키가 .env에 없습니다.")
        return []
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                'X-Naver-Client-Id': _NAVER_ID,
                'X-Naver-Client-Secret': _NAVER_SECRET,
            },
            params={'query': query, 'display': display, 'sort': 'date'},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get('items', [])
    except Exception as e:
        logger.warning(f"  [Naver API 오류] {query}: {e}")
        return []


def fetch_article_body(url: str, max_chars: int = 800) -> str:
    """Naver 뉴스 기사 본문 추출 — 실패 시 빈 문자열 반환"""
    if not url:
        return ''
    try:
        res = requests.get(url, headers=_SCRAPE_HEADERS, timeout=8)
        res.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')

        # 광고·스크립트·스타일 제거
        for tag in soup(['script', 'style', 'aside', 'nav', 'footer']):
            tag.decompose()

        # Naver 뉴스 뷰어 선택자 (우선순위 순)
        for sel in ['#dic_area', '#newsct_article', '.newsct_article',
                    '#articleBodyContents', '.article_body', 'article']:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=' ', strip=True)
                if len(text) > 100:
                    return text[:max_chars]

        # fallback: 길이 60자 이상인 <p> 태그 수집
        parts = [p.get_text(strip=True) for p in soup.find_all('p')
                 if len(p.get_text(strip=True)) > 60]
        combined = ' '.join(parts)
        return combined[:max_chars] if len(combined) > 100 else ''

    except Exception as e:
        logger.debug(f"  [본문 스크래핑 실패] {url[:60]}: {e}")
        return ''
