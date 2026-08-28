"""
여러 핫딜 소스를 모아서 '생활 할인정보'만 골라내는 오케스트레이터.

소스별 세부 로직은 scripts/sources/*.py 에 있고, 여기서는:
  1) 켜져 있는 소스들을 순서대로 호출 (하나 실패해도 나머지는 계속)
  2) 소스 간 중복 제거
  3) 커뮤니티 딜은 생활 키워드 + 추천수로 필터, 커머스 딜은 전자기기만 제외
  4) 소스별 개수 제한을 걸어 flat 리스트로 반환 (build_draft 가 소스별로 섹션 분리)

켤 소스 지정: 환경변수 SOURCES (콤마구분). 기본값은 아래 SOURCES_DEFAULT.
쿠팡은 COUPANG_ACCESS_KEY/COUPANG_SECRET_KEY 가 있으면 자동으로 포함된다.
"""

import os

from scripts.sources import SOURCE_REGISTRY
from scripts.sources import aliexpress, coupang
from scripts.sources.common import (
    cap_per_source,
    dedupe,
    filter_commerce_deals,
    filter_lifestyle_deals,
    is_coupang_related,
)
from scripts.sources.resolve_link import resolve_product_link

# 기본으로 켜는 커뮤니티 소스들 (키가 필요 없는 것들)
SOURCES_DEFAULT = "ppomppu,ruliweb,clien,algumon,telegram"

# 커뮤니티 소스는 소스별 이만큼, 커머스(쿠팡 골드박스+키워드검색)는 별도 상한
COMMUNITY_PER_SOURCE = 8
COMMERCE_MAX = 16


def _enabled_sources():
    raw = (os.environ.get("SOURCES") or SOURCES_DEFAULT).split(",")
    # 중복 제거(같은 소스를 두 번 호출하지 않도록), 순서 유지
    names = list(dict.fromkeys(s.strip() for s in raw if s.strip()))

    # 키가 있으면 커머스 소스를 자동 추가 (중복 추가 방지)
    if coupang.has_keys() and "coupang" not in names:
        names.append("coupang")
    if aliexpress.has_keys() and "aliexpress" not in names:
        names.append("aliexpress")

    return names


def _collect_raw():
    raw = []
    for name in _enabled_sources():
        fetch = SOURCE_REGISTRY.get(name)
        if fetch is None:
            print(f"⚠️ 알 수 없는 소스 '{name}' — 건너뜁니다.")
            continue
        try:
            items = fetch()
            print(f"  · {name}: {len(items)}건 수집")
            raw += items
        except Exception as e:
            print(f"⚠️ {name} 수집 실패, 건너뜁니다: {e}")
    return raw


def get_today_deals(per_source_max=COMMUNITY_PER_SOURCE):
    raw = _collect_raw()
    deals = dedupe(raw)

    raw_commerce = [d for d in deals if d["is_affiliate"]]
    community = filter_lifestyle_deals([d for d in deals if not d["is_affiliate"]])
    commerce = filter_commerce_deals(raw_commerce)

    boards = {}
    for d in raw_commerce:
        key = d["board"].split(":")[0] if d["board"] else "(없음)"
        boards[key] = boards.get(key, 0) + 1
    print(
        f"  → 중복제거 후 커뮤니티 {len([d for d in deals if not d['is_affiliate']])}건 / "
        f"커머스 {len(raw_commerce)}건({boards}), "
        f"필터 통과: 커뮤니티 {len(community)}건 / 커머스 {len(commerce)}건"
    )

    result = cap_per_source(community, per_source_max) + cap_per_source(commerce, COMMERCE_MAX)
    _resolve_product_links(result)
    return result


def _resolve_product_links(deals):
    """커뮤니티/텔레그램의 쿠팡 딜은 링크가 게시글 주소라서, 글을 한 번 더 열어
    실제 상품 링크를 뽑는다. 쿠팡 상품이면 제휴 딥링크로 변환(수익화)."""
    targets = [
        d for d in deals
        if d["source"] != "쿠팡" and not d["product_link"] and is_coupang_related(d)
    ]
    if not targets:
        return

    coupang_urls = []
    for d in targets:
        pl = resolve_product_link(d["link"])
        if pl:
            d["product_link"] = pl
            if "coupang" in pl.lower():
                coupang_urls.append(pl)
    print(f"  → 커뮤니티 쿠팡 딜 {len(targets)}건 중 상품링크 추출 "
          f"{sum(1 for d in targets if d['product_link'])}건")

    mapping = coupang.to_deeplinks(coupang_urls)
    for d in targets:
        if d["product_link"] in mapping:
            d["product_link"] = mapping[d["product_link"]]
            d["is_affiliate"] = True


if __name__ == "__main__":
    from scripts.sources.common import print_deals

    print_deals(get_today_deals())
