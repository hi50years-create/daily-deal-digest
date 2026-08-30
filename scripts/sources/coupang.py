"""
쿠팡 파트너스 Open API — 골드박스(오늘의 특가) + (옵션) 키워드 검색.

커뮤니티 핫딜과 달리 "쇼핑몰 공식 특가"라서 가격·할인율·이미지·제휴링크가
구조화되어 들어온다. 블로그 글감으로 품질이 좋고, productUrl 이 그대로
파트너스 제휴 링크라서 수익화도 된다.

필요한 환경변수 (없으면 이 소스는 그냥 빈 리스트를 반환한다):
    COUPANG_ACCESS_KEY   파트너스 → 내 계정 → 파트너스 API 에서 발급
    COUPANG_SECRET_KEY
선택:
    COUPANG_KEYWORDS     콤마구분. 지정하면 골드박스 외에 이 키워드들도 검색한다.
                         (키워드마다 요청 1회이므로 3~5개 권장)

인증: HMAC-SHA256 (CEA 방식)
    message   = signed_date + "GET" + path + query   (query 는 '?' 제외)
    signature = hmac_sha256(SECRET, message).hexdigest()
    헤더      = "CEA algorithm=HmacSHA256, access-key=..., signed-date=..., signature=..."
"""

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import requests

from .common import TIMEOUT, make_deal

DOMAIN = "https://api-gateway.coupang.com"
PREFIX = "/v2/providers/affiliate_open_api/apis/openapi/v1"
GOLDBOX_PATH = f"{PREFIX}/products/goldbox"
SEARCH_PATH = f"{PREFIX}/products/search"
DEEPLINK_PATH = f"{PREFIX}/deeplink"


def _keys():
    return os.environ.get("COUPANG_ACCESS_KEY"), os.environ.get("COUPANG_SECRET_KEY")


def has_keys():
    ak, sk = _keys()
    return bool(ak and sk)


def _authorization(method, path, query=""):
    access_key, secret_key = _keys()
    signed_date = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    message = signed_date + method + path + query
    signature = hmac.new(
        secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={signed_date}, signature={signature}"
    )


def _get(path, query=""):
    url = DOMAIN + path + (f"?{query}" if query else "")
    headers = {
        "Authorization": _authorization("GET", path, query),
        "Content-Type": "application/json;charset=UTF-8",
    }
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def to_deeplinks(urls):
    """쿠팡 상품 URL 리스트 → {원본URL: 제휴(단축)링크} 매핑.
    키가 없거나 실패하면 빈 dict."""
    urls = [u for u in urls if u]
    if not urls or not has_keys():
        return {}
    headers = {
        "Authorization": _authorization("POST", DEEPLINK_PATH),
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            DOMAIN + DEEPLINK_PATH,
            headers=headers,
            data=json.dumps({"coupangUrls": urls}),
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        rows = resp.json().get("data") or []
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️ 쿠팡 딥링크 변환 실패: {e}")
        return {}

    out = {}
    for row in rows:
        original = row.get("originalUrl")
        short = row.get("shortenUrl") or row.get("landingUrl")
        if original and short:
            out[original] = short
    return out


def _rows(payload):
    """골드박스는 data 가 list, 검색은 data.productData 가 list."""
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("productData", []) or []
    return []


def _to_deal(row, board):
    price = row.get("productPrice")
    has_price = isinstance(price, (int, float))
    price_str = f"{int(price):,}원" if has_price else ""
    base = row.get("basePrice")
    discount = ""
    if isinstance(base, (int, float)) and has_price and base > price:
        discount = f"{round((base - price) / base * 100)}%"

    ship = []
    if row.get("isRocket"):
        ship.append("로켓배송")
    if row.get("isFreeShipping"):
        ship.append("무료배송")

    return make_deal(
        title=row.get("productName", ""),
        link=row.get("productUrl", ""),
        source="쿠팡",
        board=board,
        price=price_str,
        price_value=int(price) if has_price else 0,
        discount=discount,
        image=row.get("productImage", ""),
        is_affiliate=True,
        category=row.get("categoryName", ""),
        shipping="·".join(ship),
    )


def fetch():
    if not has_keys():
        return []

    deals = []
    try:
        payload = _get(GOLDBOX_PATH)
        rows = _rows(payload)
        if rows:
            print(f"    (쿠팡 응답 필드: {sorted(rows[0].keys())})")
        deals += [_to_deal(r, "골드박스") for r in rows]
        print(f"    (쿠팡 골드박스 {len(rows)}건)")
    except requests.RequestException as e:
        print(f"⚠️ 쿠팡 골드박스 실패: {e}")

    keywords = list(dict.fromkeys(
        k.strip() for k in os.environ.get("COUPANG_KEYWORDS", "").split(",") if k.strip()
    ))
    for kw in keywords:
        try:
            payload = _get(SEARCH_PATH, query=f"keyword={requests.utils.quote(kw)}&limit=3")
            rows = _rows(payload)
            deals += [_to_deal(r, f"검색:{kw}") for r in rows]
            print(f"    (쿠팡 검색 '{kw}' {len(rows)}건, rCode={payload.get('rCode')})")
        except requests.RequestException as e:
            print(f"⚠️ 쿠팡 검색('{kw}') 실패: {e}")

    return [d for d in deals if d["title"] and d["link"]]


if __name__ == "__main__":
    from .common import print_deals
    if not has_keys():
        print("COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 설정되지 않았습니다.")
    print_deals(fetch())
