"""
수집된 할인정보를 소스별 섹션으로 나눠 이메일용 HTML로 정리한다.
API 호출 없음. 완성된 글이 아니라 '재료 목록'이다.

쿠팡 상품(파트너스 API로 온 것 + 커뮤니티/텔레그램에 올라온 쿠팡 딜)은
맨 아래 '쿠팡 상품 정리' 섹션에 사용자 지정 템플릿으로 모아준다.
"""

import html
import re
from urllib.parse import urlparse

from .sources.common import has_coupang_product

# 커뮤니티 섹션이 나오는 순서. 목록에 없는 소스는 맨 뒤에 이름순으로.
SECTION_ORDER = ["뽐뿌", "루리웹", "클리앙", "알구몬", "텔레그램"]

# 쿠팡 템플릿에서 API로 못 채우는(=Claude가 채울) 항목
_COUPANG_FILL = [
    "주요 특징", "장점", "사용 대상", "사용 상황",
    "구매자가 좋아할 만한 포인트", "리뷰에서 자주 언급되는 장점", "단점/주의사항",
]

_LEAD_TAG_RE = re.compile(r"^(?:\s*[\[\(（【][^\]\)）】]*[\]\)）】]\s*)+")
_TRAIL_PAREN_RE = re.compile(r"\s*[\(（][^)）]*[\)）]\s*$")
_PRICE_RE = re.compile(r"([\d][\d,]*)\s*원")


def _safe_url(url):
    """http/https 링크만 통과시킨다 (javascript:, data: 등 차단)."""
    try:
        return url if urlparse(url).scheme in ("http", "https") else ""
    except ValueError:
        return ""


AFFILIATE_NOTE = (
    '<p style="font-size:11px; color:#aaa; margin:4px 0 0;">'
    "※ 쿠팡 링크는 파트너스 활동의 일환으로, 일정액의 수수료를 제공받을 수 있습니다."
    "</p>"
)


def _clean_product_name(title):
    """'[쿠팡] 농심 라뽁구리 큰사발면 105g 3개 (3,660원/무료)' → '농심 라뽁구리 큰사발면 105g 3개'"""
    t = _LEAD_TAG_RE.sub("", title)
    t = _TRAIL_PAREN_RE.sub("", t)
    return t.strip() or title.strip()


def _coupang_fields(deal):
    """쿠팡 템플릿에 넣을 값들을 뽑는다.
    파트너스 API로 온 것(source=쿠팡)은 필드가 이미 채워져 있고,
    커뮤니티/텔레그램 딜은 제목에서 상품명·가격·배송을 추정한다."""
    # 링크: 딜 페이지에서 뽑아낸 실제 상품 링크가 있으면 그걸, 없으면 원문 링크
    link = deal["product_link"] or deal["link"]
    has_product = bool(deal["product_link"])

    if deal["source"] == "쿠팡":
        return {
            "name": deal["title"],
            "category": deal["category"],
            "price": deal["price"],
            "discount": deal["discount"],
            "shipping": deal["shipping"],
            "link": link,
            "has_product": True,
        }

    m = _PRICE_RE.search(deal["title"])
    shipping = "무료배송" if re.search(r"무료|무배", deal["title"]) else ""
    return {
        "name": _clean_product_name(deal["title"]),
        "category": "",
        "price": f"{m.group(1)}원" if m else "",
        "discount": deal["discount"],
        "shipping": shipping,
        "link": link,
        "has_product": has_product,
    }


def _coupang_block(deal):
    """쿠팡 상품 하나를 사용자 지정 템플릿(<pre> 블록)으로 만든다.
    아는 값만 채우고 나머지는 '(작성 필요)' — 통째로 복사해 Claude에 붙여넣으면 됨."""
    f = _coupang_fields(deal)

    lines = ["### [상품 정보]", f"* 상품명: {f['name']}"]
    if f["category"]:
        lines.append(f"* 카테고리: {f['category']}")
    price = f["price"] or "(확인 필요)"
    if f["discount"]:
        price += f" ({f['discount']} 할인)"
    lines.append(f"* 가격: {price}")
    if f["shipping"]:
        lines.append(f"* 배송: {f['shipping']}")
    link = _safe_url(f["link"])
    if link:
        label = "상품 링크" if f["has_product"] else "링크(원문 게시글)"
        lines.append(f"* {label}: {link}")
    for field in _COUPANG_FILL:
        lines.append(f"* {field}: (작성 필요)")

    body = html.escape("\n".join(lines))
    return (
        '<pre style="white-space:pre-wrap; word-break:break-all; background:#f6f6f6; '
        'border:1px solid #e0e0e0; border-radius:4px; padding:10px; font-size:13px; '
        'margin:0 0 12px;">'
        f"{body}</pre>"
    )


def _deal_li(deal):
    title = html.escape(deal["title"])
    link = _safe_url(deal["link"])
    image = _safe_url(deal["image"])

    meta_bits = []
    if deal["board"]:
        meta_bits.append(html.escape(deal["board"]))
    if deal["recommend"]:
        meta_bits.append(f"추천 {deal['recommend']}")
    if deal["price"]:
        meta_bits.append(html.escape(deal["price"]))
    if deal["discount"]:
        meta_bits.append(html.escape(deal["discount"]) + " 할인")
    meta = f' <span style="color:#888; font-size:12px;">[{" · ".join(meta_bits)}]</span>' if meta_bits else ""

    link_html = (
        f'<a href="{html.escape(link, quote=True)}" style="color:#888; font-size:13px;">원문 보기</a>'
        if link else ""
    )

    img = ""
    if image:
        img = (
            f'<br><img src="{html.escape(image, quote=True)}" alt="" '
            f'style="max-width:120px; max-height:120px; margin-top:4px; border-radius:4px;">'
        )

    return (
        f'<li style="margin-bottom:10px;">'
        f"<b>{title}</b>{meta}<br>"
        f"{link_html}{img}"
        f"</li>"
    )


def _h3(text):
    return (
        f'<h3 style="margin:18px 0 6px; font-size:15px; '
        f'border-bottom:1px solid #eee; padding-bottom:3px;">{html.escape(text)}</h3>'
    )


def _ordered_sources(sources):
    known = [s for s in SECTION_ORDER if s in sources]
    rest = sorted(s for s in sources if s not in SECTION_ORDER)
    return known + rest


def build_draft_material(deals):
    """할인정보 리스트를 소스별 섹션 + 맨 아래 쿠팡 상품 정리 섹션으로 만든다."""
    if not deals:
        return "<p>오늘은 쓸만한 생활 할인정보를 못 찾았어요.</p>"

    coupang_deals = [d for d in deals if has_coupang_product(d)]
    other_deals = [d for d in deals if not has_coupang_product(d)]

    parts = []

    # 커뮤니티 소스 섹션 (쿠팡 관련 딜은 뺀다 — 아래 별도 섹션으로)
    groups = {}
    for d in other_deals:
        groups.setdefault(d["source"], []).append(d)
    for source in _ordered_sources(groups):
        items = "".join(_deal_li(d) for d in groups[source])
        parts.append(_h3(source) + f"<ol>{items}</ol>")

    # 맨 아래: 쿠팡 상품 정리
    if coupang_deals:
        note = (
            '<p style="font-size:12px; color:#888; margin:0 0 8px;">'
            "각 블록을 통째로 복사해 Claude 채팅에 붙여넣고 "
            "“이걸로 상품 소개 글 써줘” 하면 빈칸이 채워집니다."
            "</p>"
        )
        blocks = "".join(_coupang_block(d) for d in coupang_deals)
        parts.append(_h3("🛒 쿠팡 상품 정리") + note + blocks + AFFILIATE_NOTE)

    return "\n".join(parts)
