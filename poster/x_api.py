"""X(Twitter) API v2 발행 모듈 — tweepy OAuth 1.0a + 이미지 업로드"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tweepy
from dotenv import load_dotenv
from utils import logger

load_dotenv()

_client = None   # tweepy.Client (v2) — 트윗 발행
_api_v1 = None   # tweepy.API (v1.1) — 미디어 업로드


def _get_credentials():
    return (
        os.getenv('X_API_KEY'),
        os.getenv('X_API_SECRET'),
        os.getenv('X_ACCESS_TOKEN'),
        os.getenv('X_ACCESS_TOKEN_SECRET'),
    )


def _get_x_client() -> tweepy.Client | None:
    global _client
    if _client is not None:
        return _client
    api_key, api_secret, access_token, access_token_secret = _get_credentials()
    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.error("[오류] X API 인증 정보가 .env에 없습니다.")
        return None
    _client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    return _client


def _get_api_v1() -> tweepy.API | None:
    """미디어 업로드용 v1.1 API (tweepy.Client는 미디어 업로드 미지원)"""
    global _api_v1
    if _api_v1 is not None:
        return _api_v1
    api_key, api_secret, access_token, access_token_secret = _get_credentials()
    if not all([api_key, api_secret, access_token, access_token_secret]):
        return None
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    _api_v1 = tweepy.API(auth)
    return _api_v1


def verify_credentials() -> bool:
    client = _get_x_client()
    if client is None:
        return False
    try:
        me = client.get_me()
        if me.data:
            logger.info(f"[X 인증 성공] @{me.data.username}")
            return True
        return False
    except tweepy.errors.TweepyException as e:
        logger.error(f"[X 인증 실패] {e}")
        return False


def upload_image(image_path: Path) -> str | None:
    """이미지를 X에 업로드하고 media_id 반환"""
    api = _get_api_v1()
    if api is None:
        return None
    try:
        media = api.media_upload(filename=str(image_path))
        logger.info(f"[이미지 업로드 성공] media_id={media.media_id_string}")
        return media.media_id_string
    except Exception as e:
        logger.warning(f"[이미지 업로드 실패] {e}")
        return None


def post_tweet(tweet_text: str, image_path: Path = None) -> str | None:
    """트윗 발행. image_path 지정 시 이미지 카드 포함."""
    client = _get_x_client()
    if client is None:
        return None

    try:
        response = client.create_tweet(text=tweet_text, user_auth=True)
        tweet_id = str(response.data['id'])
        logger.info(f"[트윗 발행 성공] id={tweet_id} | {tweet_text[:40]}...")
        return tweet_id
    except tweepy.errors.TooManyRequests:
        logger.error("[X API] Rate limit 초과 — 잠시 후 재시도 필요")
        return None
    except tweepy.errors.TweepyException as e:
        logger.error(f"[트윗 발행 실패] {e}")
        return None
    except Exception as e:
        logger.error(f"[트윗 발행 오류] {e}")
        return None


if __name__ == "__main__":
    ok = verify_credentials()
    print("인증 결과:", "성공" if ok else "실패")
