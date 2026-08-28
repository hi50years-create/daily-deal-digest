"""
알구몬(algumon.com) — 여러 커뮤니티(뽐뿌·루리웹·클리앙·퀘이사존·아카라이브·어미새·zod 등)를
한곳에 모아주는 집계 사이트. HTML 스크래핑.

알구몬은 Svelte 앱이라 서버가 내려주는 초기 HTML에는 최신 9건 정도만 들어있다.
그 9건이 "가장 최근" 딜이므로 데일리 다이제스트 용도로는 충분하다.
뽐뿌/루리웹/클리앙처럼 우리가 직접 수집하는 소스와 겹치는 건 dedupe()가 제목으로 걸러낸다.
알구몬을 통해서만 들어오는 건 퀘이사존·아카라이브·어미새·zod 등이다.

2026-08 기준 구조:
    div.deal-feed-card#deal-<id>
      .badge (텍스트)             원본 커뮤니티 이름 (예: "어미새")
      h3 a                        제목 + 아웃바운드 링크(토큰 만료됨 → 안 씀)
      .deal-price-text            가격 표기
      .avatar img[src]            썸네일
      본문 어딘가의 "N분 전 / N시간 전 / N일 전"  상대 시각
"""

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from .common import HEADERS, TIMEOUT, make_deal

LIST_URL = "https://www.algumon.com/n/deal"
DETAIL_URL = "https://www.algumon.com/n/deal/{id}"

_REL_RE = re.compile(r"(\d+)\s*(분|시간|일)\s*전")


def _parse_relative_date(text):
    """'3분 전', '2시간 전', '1일 전' → date. 못 찾으면 오늘로 본다(피드 상단 = 최신)."""
    m = _REL_RE.search(text)
    if not m:
        return datetime.now().date()
    n, unit = int(m.group(1)), m.group(2)
    if unit == "일":
        return (datetime.now() - timedelta(days=n)).date()
    return datetime.now().date()


def _parse_card(card):
    card_id = (card.get("id") or "").replace("deal-", "").strip()
    title_tag = card.select_one("h3 a")
    if not card_id or not title_tag:
        return None
    title = title_tag.get_text(strip=True)

    badge = card.select_one(".badge")
    board = badge.get_text(strip=True) if badge else ""

    price_tag = card.select_one(".deal-price-text")
    price = price_tag.get_text(" ", strip=True) if price_tag else ""

    img = card.select_one(".avatar img")
    image = img["src"] if img and img.get("src", "").startswith("http") else ""

    date = _parse_relative_date(card.get_text(" ", strip=True))

    return make_deal(
        title=title, link=DETAIL_URL.format(id=card_id), source="알구몬",
        board=board, date=date, price=price, image=image,
    )


def fetch():
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # 응답 헤더에 charset이 없어 requests가 latin-1로 오판함
    soup = BeautifulSoup(resp.text, "html.parser")

    deals = []
    for card in soup.select("div.deal-feed-card"):
        deal = _parse_card(card)
        if deal:
            deals.append(deal)
    return deals


if __name__ == "__main__":
    from .common import print_deals
    print_deals(fetch())
