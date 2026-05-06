"""
트윗 내용을 이미지 카드로 변환 (1080x1080 정사각형)
니치별 색상 테마 + 맑은 고딕 한글 폰트
이모지는 카드에서 제거 (PIL 미지원) — 트윗 캡션에만 포함
"""
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_REGULAR = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD    = "C:/Windows/Fonts/malgunbd.ttf"

OUTPUT_DIR = Path(__file__).parent.parent / "cards"
OUTPUT_DIR.mkdir(exist_ok=True)

THEMES = {
    'welfare': {
        'bg_top':    (240, 230, 255),
        'bg_bottom': (225, 210, 255),
        'accent':    (110, 60, 200),
        'text':      (35, 15, 70),
        'tag_text':  (255, 255, 255),
        'label':     '★  복지 혜택 알림',
    },
    'parenting': {
        'bg_top':    (255, 235, 235),
        'bg_bottom': (255, 215, 225),
        'accent':    (210, 70, 95),
        'text':      (55, 25, 35),
        'tag_text':  (255, 255, 255),
        'label':     '♡  육아 꿀팁',
    },
    'finance': {
        'bg_top':    (225, 240, 255),
        'bg_bottom': (205, 228, 255),
        'accent':    (25, 95, 190),
        'text':      (15, 35, 75),
        'tag_text':  (255, 255, 255),
        'label':     '✦  재테크 꿀팁',
    },
    'health': {
        'bg_top':    (225, 245, 225),
        'bg_bottom': (205, 238, 215),
        'accent':    (38, 145, 75),
        'text':      (18, 58, 28),
        'tag_text':  (255, 255, 255),
        'label':     '✿  건강 꿀팁',
    },
}

SIZE = 1080

# 이모지 유니코드 범위 제거 패턴
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub('', text).strip()


def _draw_gradient(draw: ImageDraw, top: tuple, bottom: tuple):
    for y in range(SIZE):
        r = int(top[0] + (bottom[0] - top[0]) * y / SIZE)
        g = int(top[1] + (bottom[1] - top[1]) * y / SIZE)
        b = int(top[2] + (bottom[2] - top[2]) * y / SIZE)
        draw.line([(0, y), (SIZE, y)], fill=(r, g, b))


def _split_hashtags(text: str) -> tuple[str, str]:
    tags = ' '.join(re.findall(r'#\S+', text))
    body = re.sub(r'#\S+', '', text).strip()
    return body, tags


def _wrap_text(text: str, font: ImageFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.split('\n'):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        current = ''
        for char in paragraph:
            test = current + char
            if font.getlength(test) > max_width and current:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def make_card(niche: str, tweet_text: str, card_id: str) -> Path:
    theme = THEMES.get(niche, THEMES['parenting'])

    img  = Image.new('RGB', (SIZE, SIZE))
    draw = ImageDraw.Draw(img)

    _draw_gradient(draw, theme['bg_top'], theme['bg_bottom'])

    # 흰 카드 영역
    pad = 55
    draw.rounded_rectangle([pad, pad, SIZE - pad, SIZE - pad], radius=32, fill=(255, 255, 255))

    # 상단 굵은 액센트 바
    draw.rounded_rectangle([pad, pad, SIZE - pad, pad + 14], radius=8, fill=theme['accent'])

    # 레이블 뱃지 (이모지 없이 특수문자 기호 사용)
    try:
        font_label = ImageFont.truetype(FONT_BOLD, 34)
    except Exception:
        font_label = ImageFont.load_default()

    lx, ly = pad + 44, pad + 44
    lw = font_label.getlength(theme['label'])
    draw.rounded_rectangle([lx - 14, ly - 8, lx + lw + 14, ly + 46], radius=22, fill=theme['accent'])
    draw.text((lx, ly), theme['label'], font=font_label, fill=theme['tag_text'])

    # 본문 (이모지 제거)
    body, hashtags = _split_hashtags(tweet_text)
    body = _strip_emoji(body).strip(' \n')
    # 남은 공백 정리
    body = re.sub(r'  +', ' ', body)

    try:
        font_body = ImageFont.truetype(FONT_BOLD, 48)
    except Exception:
        font_body = ImageFont.load_default()

    max_w = SIZE - pad * 2 - 88
    lines = _wrap_text(body, font_body, max_w)

    line_h = 70
    total_h = len(lines) * line_h
    start_y = max((SIZE - total_h) // 2 - 10, ly + 90)

    for i, line in enumerate(lines):
        draw.text((pad + 44, start_y + i * line_h), line, font=font_body, fill=theme['text'])

    # 구분선
    draw.line(
        [(pad + 44, SIZE - pad - 88), (SIZE - pad - 44, SIZE - pad - 88)],
        fill=theme['accent'], width=2,
    )

    # 해시태그
    if hashtags:
        try:
            font_tag = ImageFont.truetype(FONT_REGULAR, 30)
        except Exception:
            font_tag = ImageFont.load_default()
        draw.text((pad + 44, SIZE - pad - 72), hashtags, font=font_tag, fill=theme['accent'])

    out_path = OUTPUT_DIR / f"{card_id}.png"
    img.save(out_path, 'PNG')
    return out_path
