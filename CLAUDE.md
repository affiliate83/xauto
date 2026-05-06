# X Auto — 한국어 자동 콘텐츠 시스템

## 프로젝트 개요
30대 한국 여성 대상 X(트위터) 계정 자동 운영 시스템.
네이버 뉴스 API로 기사 수집 → Claude Haiku로 280자 트윗 생성 → X API로 하루 4회 자동 발행.
목표: X Premium 수익 공유 (팔로워 500명 이상 + 90일 500만 임프레션)

## 작업 디렉토리
E:\projects\xauto\

## 기술 스택
- Python 3.11+
- Claude Haiku (claude-haiku-4-5-20251001) — 트윗 생성
- Naver News API — 기사 수집
- tweepy 4.x — X API v2 OAuth 1.0a 발행
- APScheduler — 07:00 / 12:00 / 19:00 / 22:00 KST 자동 발행
- SQLite (xauto.db) — 콘텐츠 큐 + 중복 방지

## 콘텐츠 3대 주제 & 발행 시간
| 주제 | 키워드 파일 | 발행 시간 (KST) |
|------|------------|----------------|
| 육아/생활 | sources/parenting.py | 07:00 |
| 재테크/절약 | sources/finance.py | 12:00 |
| 건강/다이어트 | sources/health.py | 19:00 |
| (자유 순서) | — | 22:00 |

## 주요 명령어
```bash
# 의존성 설치
pip install -r requirements.txt

# 기사 수집 + 트윗 생성 + 큐 저장 (발행 안 함)
python main.py

# 스케줄러 시작 (발행 데몬 — 종료: Ctrl+C)
python scheduler.py

# X API 인증 테스트
python poster/x_api.py

# 큐 내용 확인
python -c "import db; [print(t['niche'], '|', t['tweet_text']) for t in db.get_pending_tweets(10)]"
```

## 파일 구조
```
xauto/
├── main.py          ← 파이프라인 진입점 (수집→생성→큐저장)
├── scheduler.py     ← 발행 데몬
├── db.py            ← SQLite (posted_hashes + content_queue)
├── utils.py         ← 로거, strip_html, truncate_to_x_limit
├── sources/
│   ├── __init__.py  ← Naver API 공통 헬퍼
│   ├── parenting.py ← 육아 키워드
│   ├── finance.py   ← 재테크 키워드
│   └── health.py    ← 건강 키워드
├── generator/
│   ├── prompts.py   ← 니치별 Claude 프롬프트 템플릿
│   └── writer.py    ← Claude Haiku 트윗 생성
├── poster/
│   └── x_api.py     ← tweepy POST /2/tweets
└── logs/            ← 일별 UTF-8 로그
```

## X API 설정 방법
1. developer.twitter.com 접속 → 개발자 계정 신청
2. Project + App 생성
3. App Settings → User Authentication Settings → Read and Write 선택
4. Keys and Tokens 탭 → 4개 키 발급 → .env에 입력
5. `python poster/x_api.py` 로 인증 확인

## 제약사항 (반드시 준수)
- 트윗 280자 초과 금지 — `truncate_to_x_limit()` 항상 적용
- Claude API 호출 간격 최소 3초 (`time.sleep(3)`)
- Naver API 호출 간격 최소 2초 (`time.sleep(2)`)
- X API 월 1,500건 제한 → `MONTHLY_LIMIT = 1400` 안전 마진 적용
- `.env` 절대 Git 커밋 금지
- 커밋 메시지 한글 작성

## 수익화 로드맵
| 단계 | 조건 | 행동 |
|------|------|------|
| Phase 0 | 시작 | API 세팅 + 테스트 발행 |
| Phase 1 | 자동화 운영 | 하루 4회 발행 유지 |
| Phase 2 | 팔로워 500명 | X Premium 구독 ($8/월) |
| Phase 3 | 90일 500만 임프레션 | 수익 공유 신청 |

## 코드 패턴 참조
기존 파크골프 크롤러 `E:\projects\parkgolfkkorea\crawler\` 패턴을 재사용:
- `utils.py` ← `crawler/utils.py` (로거, strip_html)
- `sources/__init__.py` ← `crawler/sources/news.py` (Naver API)
- `generator/writer.py` ← `crawler/enricher.py` (Claude 싱글톤)
- `db.py` ← `crawler/utils.py` (SQLite 중복 체크)