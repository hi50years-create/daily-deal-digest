"""
커뮤니티 딜 페이지(루리웹·클리앙·아카라이브 등)를 열어서
본문에 있는 '실제 상품 링크'(쿠팡 등)를 뽑아낸다.

텔레그램/커뮤니티 딜은 링크가 게시글 주소라서, 정작 상품이 어디인지
보려면 글에 들어가야 한다. 이 모듈이 그 글을 한 번 더 받아서
상품 URL을 찾아준다. 못 찾으면 None (원래 게시글 링크를 그대로 씀).
"""

from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .common import HEADERS, TIMEOUT

# '실제 상품'으로 인정할 쇼핑몰 호스트
SHOPPING_HOSTS = (
    "coupang.com", "coupa.ng",
    "smartstore.naver.com", "brand.naver.com", "shopping.naver.com",
    "11st.co.kr", "gmarket.co.kr", "auction.co.kr", "ssg.com", "gsshop.com",
    "lotteon.com", "wemakeprice.com", "tmon.co.kr", "oliveyoung.co.kr",
    "kurly.com", "aliexpress.com", "amazon.",
)

# 딜 페이지 열어볼 커뮤니티 호스트 (이 외엔 시도 안 함)
RESOLVABLE_HOSTS = ("ruliweb.com", "clien.net", "arca.live", "fmkorea.com", "damoang.net")


def _unwrap(url):
    """루리웹 등의 리디렉션 래퍼를 벗긴다.
    예: web.ruliweb.com/link.php?ol=<encoded real url>"""
    try:
        p = urlparse(url)
    except ValueError:
        return url
    if "ruliweb.com" in p.netloc and p.path.endswith("link.php"):
        q = parse_qs(p.query)
        if q.get("ol"):
            return unquote(q["ol"][0])
    return url


def _is_shopping(url):
    host = urlparse(url).netloc.lower()
    return any(h in host for h in SHOPPING_HOSTS)


def resolve_product_link(deal_page_url):
    """딜 페이지 URL을 받아 본문의 첫 상품 링크를 돌려준다. 못 찾으면 None."""
    host = urlparse(deal_page_url).netloc.lower()
    if not any(h in host for h in RESOLVABLE_HOSTS):
        return None

    try:
        resp = requests.get(deal_page_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.select("a[href]"):
        href = _unwrap(a.get("href", "").strip())
        if href.startswith("http") and _is_shopping(href):
            return href
    return None


if __name__ == "__main__":
    import sys
    print(resolve_product_link(sys.argv[1]))
