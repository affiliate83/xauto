"""
공공데이터포털 국가복지정보 API 수집
noinjob 프로젝트 패턴 재사용 (E:/projects/adsense/noinjob/crawler/sources/welfare.py)
30대 여성 관련 혜택 필터링 후 트윗용 데이터 반환
"""
import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from utils import logger
import db

load_dotenv()

API_KEY  = os.getenv('DATA_GO_KR_API_KEY')
ENDPOINT = os.getenv('WELFARE_API_ENDPOINT',
                     'https://apis.data.go.kr/B554287/NationalWelfareInformationsV001')

# 30대 여성 관련 키워드 필터 (테마·대상 필드에서 하나라도 매칭되면 수집)
_TARGET_KEYWORDS = [
    '여성', '임신', '출산', '산모', '영아', '영유아', '아동', '육아',
    '청년', '가족', '한부모', '건강', '모성', '저소득', '주거', '의료',
]


def _xml_text(el, tag, default=''):
    if el is None:
        return default
    node = el.find(tag)
    return node.text.strip() if node is not None and node.text else default


def _is_relevant(item) -> bool:
    """30대 여성 타겟 관련 혜택인지 테마·대상 필드로 판별"""
    themes = _xml_text(item, 'intrsThemaArray').lower()
    target = _xml_text(item, 'tgtrDtlCn').lower()
    combined = themes + ' ' + target
    return any(kw in combined for kw in _TARGET_KEYWORDS)


def _get_list(page=1, size=100):
    try:
        res = requests.get(
            f"{ENDPOINT}/NationalWelfarelistV001",
            params={'serviceKey': API_KEY, 'numOfRows': size, 'pageNo': page, 'srchKeyCode': '001'},
            timeout=15,
        )
        res.raise_for_status()
        root = ET.fromstring(res.content)
        items = root.findall('.//servList') or root.findall('.//item')
        total_node = root.find('.//totCnt') or root.find('.//totalCount')
        total = int(total_node.text) if total_node is not None and total_node.text else 0
        return items, total
    except Exception as e:
        logger.error(f"[복지API] 목록 조회 실패: {e}")
        return [], 0


def _get_detail(service_id: str):
    try:
        res = requests.get(
            f"{ENDPOINT}/NationalWelfaredetailedV001",
            params={'serviceKey': API_KEY, 'servId': service_id},
            timeout=15,
        )
        if res.status_code == 429:
            logger.warning(f"[복지API] 상세 할당량 초과 (id={service_id})")
            return None
        res.raise_for_status()
        root = ET.fromstring(res.content)
        return root.find('.//servDtlInfo') or root.find('.//item')
    except Exception as e:
        logger.error(f"[복지API] 상세 조회 실패 (id={service_id}): {e}")
        return None


def fetch(max_items: int = 100) -> list[dict]:
    """
    복지 혜택 수집 후 트윗 생성에 필요한 데이터 반환.
    반환 형식: [{niche, title, description, link, service_id, target, cycle, online}]
    """
    if not API_KEY:
        logger.error("[복지API] DATA_GO_KR_API_KEY가 .env에 없습니다.")
        return []

    logger.info("[복지혜택] 수집 시작...")
    items, total = _get_list(size=max_items)
    logger.info(f"  API 응답: {len(items)}건 (전체 {total}건)")

    results = []
    for item in items:
        service_id = _xml_text(item, 'servId')
        if not service_id:
            continue

        # 이미 트윗한 서비스 건너뜀
        if db.is_source_posted(f"welfare_{service_id}"):
            continue

        # 30대 여성 관련 필터
        if not _is_relevant(item):
            continue

        time.sleep(1)
        detail = _get_detail(service_id)

        name      = _xml_text(item, 'servNm')
        overview  = (_xml_text(detail, 'wlfareInfoOutlCn') if detail else '') or _xml_text(item, 'servDgst')
        target    = (_xml_text(detail, 'tgtrDtlCn') if detail else '') or _xml_text(item, 'tgtrDtlCn')
        how_to    = _xml_text(detail, 'alwServCn') if detail else ''
        link      = _xml_text(item, 'servDtlLink')
        cycle     = _xml_text(item, 'sprtCycNm')
        online    = _xml_text(item, 'onapPsbltYn')
        dept      = (_xml_text(detail, 'jurMnofNm') if detail else '') or _xml_text(item, 'jurMnofNm')

        if not name or not link:
            continue

        online_text = '온라인 신청 가능' if online == 'Y' else ''

        # Claude에 넘길 description 조합
        description = ' | '.join(filter(None, [overview[:150], target[:80], how_to[:80]]))

        results.append({
            'niche':      'welfare',
            'title':      name,
            'description': description,
            'link':       link,
            'service_id': f"welfare_{service_id}",
            'target':     target[:60],
            'cycle':      cycle,
            'online':     online_text,
            'dept':       dept,
            'pub_date':   '',
        })

        if len(results) >= 20:  # 최대 20건 (Claude API 비용 절감)
            break

    logger.info(f"  [복지혜택] {len(results)}건 필터링 완료")
    return results
