"""
뽐뿌 핫딜 게시판에서 최근 게시물을 가져와서
'생활 할인정보'로 보이는 것만 골라내는 스크립트.

주의: 뽐뿌 사이트 구조가 바뀌면 셀렉터(find 조건)를 다시 확인해야 할 수 있어요.
2026-08 기준 구조로 작성했습니다.
"""

import requests
from bs4 import BeautifulSoup

PPOMPPU_LIST_URL = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"

# 생활 할인정보로 볼만한 키워드 (제목에 이 중 하나라도 포함되면 후보로 채택)
LIFESTYLE_KEYWORDS = [
    "스타벅스", "스벅", "버거킹", "맥도날드", "롯데리아", "맘스터치",
    "배민", "배달의민족", "요기요", "쿠팡이츠",
    "제주항공", "진에어", "티웨이", "항공권", "특가",
    "메가커피", "컴포즈", "이디야", "커피", "치킨",
    "쿠폰", "무료", "1+1", "반값", "할인",
]

# 확실히 제외할 카테고리(전자기기/컴퓨터 부품 등, 생활 할인이랑 거리가 멂)
EXCLUDE_KEYWORDS = ["그래픽카드", "CPU", "메모리", "SSD", "노트북", "모니터"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def fetch_recent_posts(limit=60):
    """뽐뿌 게시판 최신 글 목록을 가져옵니다."""
    resp = requests.get(PPOMPPU_LIST_URL, headers=HEADERS, timeout=10)
    resp.encoding = "euc-kr"  # 뽐뿌는 EUC-KR 인코딩을 씁니다
    soup = BeautifulSoup(resp.text, "html.parser")

    posts = []
    # 게시글 행(tr)에서 제목 링크만 추출
    for row in soup.select("tr.baseList"):
        title_tag = row.select_one("a.baseList-title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.ppomppu.co.kr/zboard/" + href.lstrip("/")
        posts.append({"title": title, "link": href})
        if len(posts) >= limit:
            break
    return posts


def filter_lifestyle_deals(posts):
    """생활 할인정보로 보이는 것만 필터링합니다."""
    filtered = []
    for post in posts:
        title = post["title"]
        if any(bad in title for bad in EXCLUDE_KEYWORDS):
            continue
        if any(good in title for good in LIFESTYLE_KEYWORDS):
            filtered.append(post)
    return filtered


def get_today_deals(max_items=5):
    posts = fetch_recent_posts()
    deals = filter_lifestyle_deals(posts)
    return deals[:max_items]


if __name__ == "__main__":
    deals = get_today_deals()
    for d in deals:
        print(f"- {d['title']} ({d['link']})")
