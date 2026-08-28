"""
알리익스프레스 어필리에이트 API — 스텁(뼈대만).

지금은 계정/키가 없어서 항상 빈 리스트를 반환한다.
나중에 https://portals.aliexpress.com 에서 어필리에이트 승인을 받고
아래 환경변수를 채우면 자동으로 동작한다.
    ALIEXPRESS_APP_KEY
    ALIEXPRESS_APP_SECRET
    ALIEXPRESS_TRACKING_ID

구현 시 사용할 엔드포인트: aliexpress.affiliate.hotproduct.query
    - 파라미터: sort=discountAsc / target_currency=KRW / target_language=KO
    - 응답의 상품별 sale_price, original_price, discount, promotion_link 를
      make_deal(source="알리", is_affiliate=True) 로 변환
"""

import os

# from .common import make_deal  # 실제 구현 시 사용


def has_keys():
    return bool(os.environ.get("ALIEXPRESS_APP_KEY") and os.environ.get("ALIEXPRESS_APP_SECRET"))


def fetch():
    if not has_keys():
        return []
    # TODO: aliexpress.affiliate.hotproduct.query 호출 구현
    print("⚠️ 알리익스프레스 키는 있으나 fetch()가 아직 구현되지 않았습니다.")
    return []


if __name__ == "__main__":
    print("알리익스프레스 소스는 아직 스텁입니다. 수집 결과: []")
