"""
뽐뿌 핫딜/쿠폰/이벤트 게시판 — RSS 버전.

기존에는 HTML을 직접 긁어서 셀렉터(tr.baseList 등)가 깨질 위험이 있었는데,
뽐뿌가 게시판별 RSS를 제공하므로 그걸 사용한다.
    https://www.ppomppu.co.kr/rss.php?id=<게시판ID>
"""

from .rss import fetch_feeds

FEEDS = [
    ("핫딜", "https://www.ppomppu.co.kr/rss.php?id=ppomppu"),
    ("쿠폰", "https://www.ppomppu.co.kr/rss.php?id=coupon"),
    ("이벤트", "https://www.ppomppu.co.kr/rss.php?id=event2"),
]


def fetch():
    return fetch_feeds(FEEDS, source="뽐뿌")


if __name__ == "__main__":
    from .common import print_deals
    print_deals(fetch())
