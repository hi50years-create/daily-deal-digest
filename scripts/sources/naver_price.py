"""
네이버 쇼핑 검색 API로 '진짜 최저가'를 확인하는 보조 모듈.

핫딜(특히 쿠팡 골드박스)은 판매처가 '특가'라고 이름 붙였을 뿐,
다른 데서 더 싸게 파는 경우가 많다. 커머스 딜을 메일에 넣기 전에
같은 상품의 네이버 쇼핑 최저가를 조회해서 비교 정보를 붙인다.

환경변수 (없으면 가격 조회를 건너뛴다):
    NAVER_CLIENT_ID       https://developers.naver.com 에서 앱 등록 후 발급
    NAVER_CLIENT_SECRET
무료. 하루 25,000회 호출 가능 (골드박스 한 번에 27건 정도라 넉넉함).
"""

import os
import re

import requests

from .common import TIMEOUT

API_URL = "https://openapi.naver.com/v1/search/shop.json"

# 검색어 정리용: 홍보 문구/괄호/기호 제거
_STRIP_RE = re.compile(
    r"[★☆]|\[[^\]]*\]|\([^)]*\)|【[^】]*】|"
    r"특가|최저가|무료배송|무배|당일발송|정품|국내정식|공식|이벤트|사은품|쿠폰"
)
_SEP_RE = re.compile(r"[/\\\-~·|]+")
_WS_RE = re.compile(r"\s+")

# 한 번 조회한 검색어는 캐시 (같은 실행 안에서 중복 호출 방지)
_cache = {}


def has_keys():
    return bool(os.environ.get("NAVER_CLIENT_ID") and os.environ.get("NAVER_CLIENT_SECRET"))


def _clean_query(title):
    q = _STRIP_RE.sub(" ", title)
    q = _SEP_RE.sub(" ", q)
    q = _WS_RE.sub(" ", q).strip()
    # 너무 길면 앞 8단어만 (검색 정확도 ↑)
    return " ".join(q.split()[:8])


def _headers():
    return {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
    }


def lowest_price(title):
    """상품명으로 네이버 쇼핑을 검색해 (최저가:int, 판매처:str) 를 돌려준다.
    못 찾거나 키가 없으면 None.

    오매칭을 줄이려고, 검색어의 주요 토큰(2글자 이상) 중 하나라도 결과 제목에
    들어있는 항목만 대상으로 삼는다."""
    if not has_keys():
        return None

    query = _clean_query(title)
    if len(query) < 2:
        return None
    if query in _cache:
        return _cache[query]

    result = None
    try:
        resp = requests.get(
            API_URL,
            headers=_headers(),
            params={"query": query, "display": 20, "sort": "asc"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

        tokens = [t for t in query.split() if len(t) >= 2]
        best = None
        for item in items:
            try:
                price = int(item.get("lprice") or 0)
            except ValueError:
                continue
            if price <= 0:
                continue
            name = re.sub(r"<[^>]+>", "", item.get("title", ""))
            if tokens and not any(tok in name for tok in tokens):
                continue
            if best is None or price < best[0]:
                best = (price, item.get("mallName", "").strip())
        result = best
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️ 네이버 최저가 조회 실패('{query}'): {e}")

    _cache[query] = result
    return result


def enrich(deals):
    """커머스(is_affiliate) 딜에 네이버 최저가 정보를 채워 넣는다.
    키가 없으면 아무것도 안 하고 그대로 돌려준다."""
    if not has_keys():
        return deals
    for d in deals:
        if not d.get("is_affiliate") or d.get("price_value", 0) <= 0:
            continue
        info = lowest_price(d["title"])
        if info:
            d["lowest_price"], d["lowest_mall"] = info
    return deals


if __name__ == "__main__":
    if not has_keys():
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 설정되지 않았습니다.")
    else:
        for q in ["부산 아쿠아리움 입장권", "농심 신라면 20개"]:
            print(q, "→", lowest_price(q))
