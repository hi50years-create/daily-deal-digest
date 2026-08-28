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
from scripts.sources import aliexpress, coupang, naver_price
from scripts.sources.common import (
    cap_per_source,
    dedupe,
    exclude_electronics,
    filter_lifestyle_deals,
)

# 기본으로 켜는 커뮤니티 소스들 (키가 필요 없는 것들)
SOURCES_DEFAULT = "ppomppu,ruliweb,clien,algumon,telegram"

# 커뮤니티 소스는 소스별 이만큼, 커머스(쿠팡 등)는 별도 상한
COMMUNITY_PER_SOURCE = 6
COMMERCE_MAX = 8

# 커머스 딜 가격이 네이버 최저가의 이 배수를 넘으면 '특가 아님'으로 보고 제외.
# 1.15 = 15% 이상 비싸면 버림 (검색 오매칭 여지를 감안해 여유를 둠).
MARKET_PRICE_TOLERANCE = 1.15


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


def _drop_overpriced(deals):
    """네이버 최저가가 확인된 커머스 딜 중, 그 최저가보다 너무 비싼 건 제외한다.
    ('골드박스 특가'라고 이름만 붙고 실제론 다른 데가 더 싼 경우 걸러냄)"""
    kept = []
    for d in deals:
        low = d.get("lowest_price", 0)
        price = d.get("price_value", 0)
        if low > 0 and price > 0 and price > low * MARKET_PRICE_TOLERANCE:
            print(
                f"  · 제외(특가 아님): {d['title'][:40]} "
                f"— 쿠팡 {price:,}원 > 네이버 최저 {low:,}원"
            )
            continue
        kept.append(d)
    return kept


def get_today_deals(per_source_max=COMMUNITY_PER_SOURCE):
    raw = _collect_raw()
    deals = dedupe(raw)

    community = filter_lifestyle_deals([d for d in deals if not d["is_affiliate"]])
    commerce = exclude_electronics([d for d in deals if d["is_affiliate"]])

    # 커머스 딜은 네이버 쇼핑 최저가와 대조 (키 없으면 그대로 통과)
    commerce = naver_price.enrich(commerce)
    commerce = _drop_overpriced(commerce)

    result = cap_per_source(community, per_source_max) + cap_per_source(commerce, COMMERCE_MAX)
    return result


if __name__ == "__main__":
    from scripts.sources.common import print_deals

    print_deals(get_today_deals())
