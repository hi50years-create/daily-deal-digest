"""
텔레그램 핫딜 채널 — 웹 미리보기(t.me/s/<채널>) 스크래핑.

로그인·API 키·세션이 전혀 필요 없다. 텔레그램이 공개 채널마다 제공하는
https://t.me/s/<채널명> 미리보기 페이지에서 최근 메시지(약 20개)를 읽는다.

기본 채널 hotdeal_kr 은 "한국 커뮤니티 핫딜 모아보기" — 뽐뿌·루리웹·클리앙·
퀘이사존·아카라이브·zod 등 여러 곳을 1분 단위로 모아 재전송하는 집계 채널이다.
채널을 바꾸거나 추가하려면 환경변수 TELEGRAM_CHANNELS 에 콤마로 구분해 넣는다.
    TELEGRAM_CHANNELS=hotdeal_kr,another_channel

메시지 구조:
    .tgme_widget_message[data-post="<채널>/<번호>"]
      .tgme_widget_message_text        본문 (첫 줄 = 제목, 링크는 별도 앵커)
      a[href]  (t.me 아닌 것)           "자세히 보기" 원문 링크 + 괄호 안에 출처
      time[datetime]                    ISO 작성시각
"""

import os
import re
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from .common import HEADERS, TIMEOUT, is_recent, make_deal

DEFAULT_CHANNELS = ["hotdeal_kr"]
PREVIEW_URL = "https://t.me/s/{channel}"

_SOURCE_IN_PAREN = re.compile(r"[\(（]([^)）]+)[\)）]")


def _channels():
    raw = os.environ.get("TELEGRAM_CHANNELS", "")
    chans = [c.strip() for c in raw.split(",") if c.strip()]
    return chans or DEFAULT_CHANNELS


def _parse_message(msg):
    text_tag = msg.select_one(".tgme_widget_message_text")
    if not text_tag:
        return None
    full_text = text_tag.get_text("\n", strip=True)
    title = full_text.split("\n", 1)[0].strip()
    if not title:
        return None

    # 원문 링크: t.me 가 아닌 첫 앵커. 없으면 메시지 퍼머링크.
    link = ""
    board = ""
    for a in msg.select("a[href]"):
        href = a.get("href", "")
        if "//t.me/" in href or href.startswith("/"):
            continue
        link = href
        m = _SOURCE_IN_PAREN.search(a.get_text(strip=True))
        if m:
            board = m.group(1).strip()
        break
    if not link:
        post = msg.get("data-post", "")
        if post:
            link = f"https://t.me/{post}"

    date = None
    time_tag = msg.select_one("time[datetime]")
    if time_tag:
        try:
            date = datetime.fromisoformat(time_tag["datetime"]).date()
        except ValueError:
            date = None

    return make_deal(
        title=title, link=link, source="텔레그램", board=board, date=date,
    )


def fetch():
    deals = []
    for channel in _channels():
        resp = requests.get(
            PREVIEW_URL.format(channel=quote(channel, safe="")),
            headers=HEADERS, timeout=TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for msg in soup.select(".tgme_widget_message"):
            deal = _parse_message(msg)
            if deal and deal["link"] and is_recent(deal):
                deals.append(deal)
    return deals


if __name__ == "__main__":
    from .common import print_deals
    print_deals(fetch())
