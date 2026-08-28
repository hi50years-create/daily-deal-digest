"""
클리앙 '알뜰구매'(지름) 게시판 — HTML 스크래핑.

클리앙은 RSS 경로가 막혀 있어서(400/404) 목록 페이지를 직접 파싱한다.
클리앙이 데이터센터 IP(예: GitHub Actions)를 403으로 막는 경우가 있는데,
그때는 이 소스만 조용히 건너뛴다. 계속 실패하면 SOURCES에서 'clien'을 빼면 된다.

2026-08 기준 구조:
    div.list_item.symph_row          한 게시글 행 (단, .notice 는 공지)
      .list_subject a                제목 + href
      .list_symph em / strong        추천수
      .keyword .icon_keyword         분류(이벤트정보 등)
      .list_time .timestamp          "YYYY-MM-DD HH:MM:SS"
      .list_thumbnail img[src]       썸네일
"""

import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .common import HEADERS, TIMEOUT, is_recent, make_deal

BOARD_URL = "https://www.clien.net/service/board/jirum"
MAX_PAGES = 2


def _parse_row(row):
    subject = row.select_one(".list_subject a")
    if not subject:
        return None
    title = subject.get_text(strip=True)
    link = urljoin(BOARD_URL, subject.get("href", ""))
    # 목록 정렬 파라미터(?od=...&po=...) 제거해서 깔끔한 글 주소로
    s = urlsplit(link)
    link = urlunsplit((s.scheme, s.netloc, s.path, "", ""))

    recommend = 0
    sym = row.select_one(".list_symph em, .list_symph strong")
    if sym:
        digits = re.sub(r"\D", "", sym.get_text())
        recommend = int(digits) if digits else 0

    kw = row.select_one(".keyword .icon_keyword")
    board = kw.get_text(strip=True) if kw else ""

    date = None
    ts = row.select_one(".list_time .timestamp")
    if ts:
        try:
            date = datetime.strptime(ts.get_text(strip=True), "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            date = None

    img_tag = row.select_one(".list_thumbnail img")
    image = ""
    if img_tag and img_tag.get("src", "").startswith("http"):
        image = img_tag["src"]

    return make_deal(
        title=title, link=link, source="클리앙",
        board=board, recommend=recommend, date=date, image=image,
    )


def fetch():
    deals = []
    for page in range(MAX_PAGES):
        url = f"{BOARD_URL}?&po={page}" if page else BOARD_URL
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("div.list_item.symph_row")
        if not rows:
            break

        page_deals = [
            _parse_row(row) for row in rows
            if "notice" not in row.get("class", [])
        ]
        page_deals = [d for d in page_deals if d]
        deals += page_deals

        # 이 페이지 글이 전부 최근 범위 밖이면 다음 페이지는 볼 필요 없음
        if page_deals and not any(is_recent(d) for d in page_deals):
            break
    return deals


if __name__ == "__main__":
    from .common import print_deals
    print_deals(fetch())
