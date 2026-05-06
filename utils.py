"""공통 유틸리티: 로거, 텍스트 정제"""
import io
import re
import sys
import logging
import datetime
from pathlib import Path

# Windows 콘솔 한글 깨짐 방지
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"{datetime.date.today().isoformat()}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('xauto')


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def truncate_to_x_limit(text: str, limit: int = 275) -> str:
    """X 280자 제한 준수. URL은 자동 단축(23자)되므로 본문만 카운트."""
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    last_space = truncated.rfind(' ')
    if last_space > limit - 30:
        truncated = truncated[:last_space]
    return truncated.rstrip()