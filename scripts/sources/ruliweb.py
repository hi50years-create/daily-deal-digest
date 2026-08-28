"""
루리웹 예판/핫딜 게시판 — RSS 버전.
    https://bbs.ruliweb.com/market/board/1020/rss
entry에 <category>(게임S/W, 음식, 상품권 등)가 있어서 board로 넣는다.
"""

from .common import make_deal, parse_struct_time
from .rss import load_feed

FEED_URL = "https://bbs.ruliweb.com/market/board/1020/rss"


def fetch():
    parsed = load_feed(FEED_URL)
    if parsed.bozo and not parsed.entries:
        print(f"⚠️ 루리웹 피드가 비어있거나 형식 오류: {FEED_URL}")
        return []

    deals = []
    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue
        tags = entry.get("tags") or []
        board = tags[0].get("term", "") if tags else ""
        date = parse_struct_time(
            entry.get("published_parsed") or entry.get("updated_parsed")
        )
        deals.append(make_deal(
            title=title, link=link, source="루리웹", board=board, date=date,
        ))
    return deals


if __name__ == "__main__":
    from .common import print_deals
    print_deals(fetch())
