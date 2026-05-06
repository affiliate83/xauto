"""X(Twitter) API v2 발행 모듈 — 단일 트윗 + 스레드 지원"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tweepy
from dotenv import load_dotenv
from utils import logger

load_dotenv()

_client = None
_api_v1 = None


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


def post_tweet(tweet_text: str) -> str | None:
    """단일 트윗 발행"""
    client = _get_x_client()
    if client is None:
        return None
    try:
        response = client.create_tweet(text=tweet_text, user_auth=True)
        tweet_id = str(response.data['id'])
        logger.info(f"[트윗 발행 성공] id={tweet_id} | {tweet_text[:40]}...")
        return tweet_id
    except tweepy.errors.TooManyRequests:
        logger.error("[X API] Rate limit 초과")
        return None
    except tweepy.errors.TweepyException as e:
        logger.error(f"[트윗 발행 실패] {e}")
        return None
    except Exception as e:
        logger.error(f"[트윗 발행 오류] {e}")
        return None


def post_thread(tweets: list[str]) -> str | None:
    """스레드 발행 — 트윗들을 순서대로 연결, 첫 트윗 ID 반환"""
    client = _get_x_client()
    if client is None:
        return None

    reply_to_id = None
    first_tweet_id = None

    for i, text in enumerate(tweets):
        try:
            kwargs = {'text': text, 'user_auth': True}
            if reply_to_id:
                kwargs['in_reply_to_tweet_id'] = int(reply_to_id)

            response = client.create_tweet(**kwargs)
            tweet_id = str(response.data['id'])

            if i == 0:
                first_tweet_id = tweet_id
            reply_to_id = tweet_id
            logger.info(f"  [스레드 {i+1}/{len(tweets)}] id={tweet_id} | {text[:30]}...")

            if i < len(tweets) - 1:
                time.sleep(2)

        except tweepy.errors.TooManyRequests:
            logger.error("[X API] Rate limit 초과 — 스레드 중단")
            break
        except tweepy.errors.TweepyException as e:
            logger.error(f"[스레드 발행 실패] {i+1}번째 트윗: {e}")
            break

    return first_tweet_id


if __name__ == "__main__":
    ok = verify_credentials()
    print("인증 결과:", "성공" if ok else "실패")
