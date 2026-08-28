"""
RSS 피드를 읽어 deal 딕셔너리 목록으로 바꾸는 공통 헬퍼.

주의: feedparser.parse(url) 는 내부적으로 urllib를 쓰는데 타임아웃을 못 건다.
그래서 requests 로 먼저 받아온 뒤(TIMEOUT 적용) 바이트만 feedparser 에 넘긴다.
"""

import feedparser
import requests

from .common import HEADERS, TIMEOUT, make_deal, parse_struct_time


def load_feed(url):
    """RSS URL을 타임아웃을 걸어 받아온 뒤 feedparser 로 파싱해 돌려준다."""
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def entry_to_deal(entry, source, board):
    """feedparser entry 하나 → deal dict. 제목/링크가 없으면 None."""
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()
    if not title or not link:
        return None
    date = parse_struct_time(
        entry.get("published_parsed") or entry.get("updated_parsed")
    )
    return make_deal(title=title, link=link, source=source, board=board, date=date)


def fetch_feeds(feed_specs, source):
    """feed_specs: [(board_name, feed_url), ...]
    source: deal["source"]에 넣을 이름 (예: "뽐뿌")

    피드 하나가 실패해도 나머지는 계속 처리한다.
    """
    deals = []
    for board_name, feed_url in feed_specs:
        try:
            parsed = load_feed(feed_url)
        except requests.RequestException as e:
            print(f"⚠️ {source}/{board_name} 피드 요청 실패: {e}")
            continue

        if parsed.bozo and not parsed.entries:
            print(f"⚠️ {source}/{board_name} 피드가 비어있거나 형식 오류: {feed_url}")
            continue

        for entry in parsed.entries:
            deal = entry_to_deal(entry, source, board_name)
            if deal:
                deals.append(deal)
    return deals
