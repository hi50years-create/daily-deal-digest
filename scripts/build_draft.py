"""
수집된 할인정보를 소스별 섹션으로 나눠 이메일용 HTML로 정리한다.
API 호출 없음. 완성된 글이 아니라 '재료 목록'이다.
"""

import html
from urllib.parse import urlparse

# 이메일에서 섹션이 나오는 순서. 목록에 없는 소스는 맨 뒤에 이름순으로 붙는다.
SECTION_ORDER = ["뽐뿌", "루리웹", "클리앙", "알구몬", "텔레그램", "쿠팡"]


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


def _group_by_source(deals):
    groups = {}
    for d in deals:
        groups.setdefault(d["source"], []).append(d)
    return groups


def _ordered_sources(groups):
    known = [s for s in SECTION_ORDER if s in groups]
    rest = sorted(s for s in groups if s not in SECTION_ORDER)
    return known + rest


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

    if link:
        link_html = f'<a href="{html.escape(link, quote=True)}" style="color:#888; font-size:13px;">원문 보기</a>'
    else:
        link_html = ""

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


_COUPANG_FILL = [
    "주요 특징", "장점", "사용 대상", "사용 상황",
    "구매자가 좋아할 만한 포인트", "리뷰에서 자주 언급되는 장점", "단점/주의사항",
]


def _coupang_block(deal):
    """쿠팡 상품을 사용자 지정 템플릿으로 정리한다.
    API로 얻는 값(상품명/카테고리/가격/배송/링크)은 채우고,
    나머지(특징·장점·리뷰 등)는 '(작성 필요)'로 두어 Claude가 채우도록 한다.
    <pre> 블록이라 그대로 복사해서 Claude 채팅에 붙여넣으면 된다."""
    lines = ["### [상품 정보]", f"* 상품명: {deal['title']}"]
    if deal["category"]:
        lines.append(f"* 카테고리: {deal['category']}")
    price = deal["price"] or "(확인 필요)"
    if deal["discount"]:
        price += f" ({deal['discount']} 할인)"
    lines.append(f"* 가격: {price}")
    if deal["shipping"]:
        lines.append(f"* 배송: {deal['shipping']}")
    link = _safe_url(deal["link"])
    if link:
        lines.append(f"* 쿠팡 링크: {link}")
    for field in _COUPANG_FILL:
        lines.append(f"* {field}: (작성 필요)")

    body = html.escape("\n".join(lines))
    return (
        '<pre style="white-space:pre-wrap; word-break:break-all; background:#f6f6f6; '
        'border:1px solid #e0e0e0; border-radius:4px; padding:10px; font-size:13px; '
        'margin:0 0 12px;">'
        f"{body}</pre>"
    )


def build_draft_material(deals):
    """할인정보 리스트를 소스별 섹션 HTML로 정리한다."""
    groups = _group_by_source(deals)
    if not groups:
        return "<p>오늘은 쓸만한 생활 할인정보를 못 찾았어요.</p>"

    parts = []
    for source in _ordered_sources(groups):
        header = (
            f'<h3 style="margin:18px 0 6px; font-size:15px; '
            f'border-bottom:1px solid #eee; padding-bottom:3px;">{html.escape(source)}</h3>'
        )
        if source == "쿠팡":
            note = (
                '<p style="font-size:12px; color:#888; margin:0 0 8px;">'
                "아래 블록을 Claude 채팅에 붙여넣고 “이걸로 상품 소개 글 써줘” 하면 빈칸이 채워집니다."
                "</p>"
            )
            blocks = "".join(_coupang_block(d) for d in groups[source])
            parts.append(header + note + blocks + AFFILIATE_NOTE)
        else:
            items = "".join(_deal_li(d) for d in groups[source])
            parts.append(header + f"<ol>{items}</ol>")

    return "\n".join(parts)
