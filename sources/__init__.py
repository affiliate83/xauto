"""Naver News API 공통 헬퍼"""
import os
import requests
from dotenv import load_dotenv
from utils import logger

load_dotenv()

_NAVER_ID = os.getenv('NAVER_CLIENT_ID')
_NAVER_SECRET = os.getenv('NAVER_CLIENT_SECRET')


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