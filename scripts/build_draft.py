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

    # 네이버 쇼핑 최저가 대조 결과 (조회한 커머스 딜만)
    price_note = ""
    low = deal.get("lowest_price", 0)
    pv = deal.get("price_value", 0)
    if low > 0 and pv > 0:
        mall = html.escape(deal.get("lowest_mall") or "네이버")
        if pv <= low:
            price_note = (
                f'<br><span style="color:#1a7f37; font-size:12px;">'
                f"✅ 이 딜이 최저가 수준 (네이버 최저 {low:,}원 · {mall})</span>"
            )
        else:
            gap = round((pv - low) / low * 100)
            price_note = (
                f'<br><span style="color:#b34700; font-size:12px;">'
                f"⚠️ 네이버 최저 {low:,}원 ({mall}) — 이 딜이 약 {gap}% 비쌈</span>"
            )

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
        f"<b>{title}</b>{meta}{price_note}<br>"
        f"{link_html}{img}"
        f"</li>"
    )


def build_draft_material(deals):
    """할인정보 리스트를 소스별 섹션 HTML로 정리한다."""
    groups = _group_by_source(deals)
    if not groups:
        return "<p>오늘은 쓸만한 생활 할인정보를 못 찾았어요.</p>"

    parts = []
    for source in _ordered_sources(groups):
        items = "".join(_deal_li(d) for d in groups[source])
        parts.append(
            f'<h3 style="margin:18px 0 6px; font-size:15px; border-bottom:1px solid #eee; padding-bottom:3px;">'
            f"{html.escape(source)}</h3>"
            f"<ol>{items}</ol>"
        )
        if source == "쿠팡":
            parts.append(AFFILIATE_NOTE)

    return "\n".join(parts)
