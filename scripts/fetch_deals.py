"""
뽐뿌 핫딜 게시판에서 최근 게시물을 가져와서
'생활 할인정보'로 보이는 것만 골라내는 스크립트.

주의: 뽐뿌 사이트 구조가 바뀌면 셀렉터(find 조건)를 다시 확인해야 할 수 있어요.
2026-08 기준 구조로 작성했습니다.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 3개 게시판을 같이 긁어옵니다: 핫딜(전체 특가) + 쿠폰(브랜드 공식 쿠폰) + 이벤트
BOARD_URLS = {
    "핫딜": "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu",
    "쿠폰": "https://www.ppomppu.co.kr/zboard/zboard.php?id=coupon",
    "이벤트": "https://www.ppomppu.co.kr/zboard/zboard.php?id=event2",
}

# 생활 할인정보로 볼만한 키워드 (제목에 이 중 하나라도 포함되면 후보로 채택)
# 주의: "무료", "할인", "쿠폰", "특가" 같은 범용 단어는 넣지 않습니다.
# 뽐뿌 글 제목은 (가격/배송비) 형식이 많아서 "무료"만 넣어도
# 배송비 무료인 아무 상품이나 다 걸려버려요 (미용티슈, 신발, 정장 등).
# 그래서 실제 브랜드명 위주로만 좁혀서 정확도를 올렸습니다.
LIFESTYLE_KEYWORDS = [
    # 카페/디저트
    "스타벅스", "스벅", "메가커피", "컴포즈커피", "이디야", "빽다방",
    "투썸", "할리스", "폴바셋", "파리바게뜨", "뚜레쥬르", "던킨",
    # 패스트푸드/외식
    "버거킹", "맥도날드", "롯데리아", "맘스터치", "KFC", "서브웨이",
    "교촌", "BBQ", "굽네", "bhc",
    # 배달앱
    "배달의민족", "배민", "요기요", "쿠팡이츠",
    # 항공/여행
    "제주항공", "진에어", "티웨이", "에어부산", "이스타항공",
    # 기타 생활 쿠폰
    "기프티콘", "모바일쿠폰", "스타벅스카드",
]

# 확실히 제외할 카테고리(전자기기/컴퓨터 부품 등, 생활 할인이랑 거리가 멂)
EXCLUDE_KEYWORDS = ["그래픽카드", "CPU", "메모리", "SSD", "노트북", "모니터"]

# 이 추천수 미만이면 후보에서 제외 (인기 없는 글 거르기)
MIN_RECOMMEND = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _parse_recommend_count(row):
    """게시글 행에서 추천수를 뽑아냅니다. 못 찾으면 0을 반환합니다.
    뽐뿌 목록 페이지의 추천수 표기 위치는 클래스명이 몇 가지로 섞여 있어서,
    여러 후보를 순서대로 시도합니다."""
    candidates = [
        row.select_one(".baseList-cnt"),
        row.select_one(".baseList-rec"),
        row.select_one("td.baseList-space.baseList-vote"),
    ]
    for tag in candidates:
        if tag:
            text = tag.get_text(strip=True)
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                return int(digits)
    return 0


def fetch_recent_posts(per_board_limit=40):
    """3개 게시판(핫딜/쿠폰/이벤트) 최신 글 목록을 모두 가져옵니다. (제목/링크/추천수/출처게시판)"""
    all_posts = []

    for board_name, board_url in BOARD_URLS.items():
        try:
            resp = requests.get(board_url, headers=HEADERS, timeout=10)
            resp.encoding = "euc-kr"  # 뽐뿌는 EUC-KR 인코딩을 씁니다
            soup = BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"⚠️ {board_name} 게시판 불러오기 실패: {e}")
            continue

        count = 0
        for row in soup.select("tr.baseList"):
            title_tag = row.select_one("a.baseList-title")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            href = urljoin(board_url, href)  # 상대경로를 안전하게 절대경로로 변환
            recommend = _parse_recommend_count(row)
            all_posts.append({
                "title": title, "link": href,
                "recommend": recommend, "board": board_name,
            })
            count += 1
            if count >= per_board_limit:
                break

    return all_posts


def filter_lifestyle_deals(posts):
    """생활 할인정보 + 인기 있는 것만 필터링합니다."""
    filtered = []
    for post in posts:
        title = post["title"]
        if any(bad in title for bad in EXCLUDE_KEYWORDS):
            continue
        if not any(good in title for good in LIFESTYLE_KEYWORDS):
            continue
        filtered.append(post)

    # 추천수 기준 필터링 (단, 전부 0으로 잡히면 - 셀렉터가 안 맞았을 수 있으니 -
    # 필터 없이 최신순으로라도 반환)
    popular = [p for p in filtered if p["recommend"] >= MIN_RECOMMEND]
    if popular:
        popular.sort(key=lambda p: p["recommend"], reverse=True)
        return popular

    if filtered:
        print("⚠️ 추천수를 못 읽었거나 기준(3) 넘는 글이 없어서, 최신순으로 대체합니다.")
    return filtered


def get_today_deals(max_items=5):
    posts = fetch_recent_posts()
    deals = filter_lifestyle_deals(posts)
    return deals[:max_items]


if __name__ == "__main__":
    deals = get_today_deals()
    for d in deals:
        print(f"- [추천 {d['recommend']}] {d['title']} ({d['link']})")
