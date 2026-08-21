"""
뽐뿌 핫딜/쿠폰/이벤트 게시판에서 최근 게시물을 가져와서
'생활 할인정보'로 보이는 것만 골라내는 스크립트.

주의: 뽐뿌 사이트 구조가 바뀌면 셀렉터(find 조건)를 다시 확인해야 할 수 있어요.
2026-08 기준 구조로 작성했습니다.
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta

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
    "스타벅스", "스벅", "메가커피", "컴포즈커피", "컴포즈", "이디야", "빽다방",
    "투썸", "할리스", "폴바셋", "파스쿠찌", "요거프레소", "커피빈", "탐앤탐스",
    "매머드커피", "만랩커피", "파리바게뜨", "뚜레쥬르", "던킨", "설빙",
    # 패스트푸드/외식
    "버거킹", "맥도날드", "롯데리아", "맘스터치", "KFC", "서브웨이", "노브랜드버거",
    "교촌", "BBQ", "굽네", "bhc", "네네치킨", "puradak", "푸라닭",
    "도미노피자", "피자헛", "미스터피자", "파파존스",
    # 편의점 (1+1, 2+1 이벤트가 자주 올라옴)
    "GS25", "CU", "세븐일레븐", "이마트24", "미니스톱",
    # 배달앱
    "배달의민족", "배민", "요기요", "쿠팡이츠",
    # 항공/여행
    "제주항공", "진에어", "티웨이", "에어부산", "이스타항공", "에어서울", "에어프레미아",
    # 기타 생활 쿠폰
    "기프티콘", "모바일쿠폰", "스타벅스카드", "해피콘",
]

# 확실히 제외할 카테고리(전자기기/컴퓨터 부품 등, 생활 할인이랑 거리가 멂)
EXCLUDE_KEYWORDS = ["그래픽카드", "CPU", "메모리", "SSD", "노트북", "모니터"]

# 이 추천수 미만이면 후보에서 제외 (인기 없는 글 거르기)
MIN_RECOMMEND = 3

# 최근 며칠 이내 글만 포함 (오늘 포함 기준 일수)
RECENT_DAYS = 3

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


def _parse_post_date(row):
    """게시글 행에서 작성일을 추정합니다.
    오늘 올라온 글은 보통 'HH:MM'만 표시되고, 이전 글은 'MM.DD' 형식으로 표시돼요.
    못 찾거나 형식이 안 맞으면 None을 반환합니다 (이 경우 안전하게 포함시킵니다)."""
    candidates = [
        row.select_one(".baseList-time"),
        row.select_one("time"),
        row.select_one("td.baseList-space.baseList-date"),
    ]
    date_tag = next((t for t in candidates if t), None)
    if not date_tag:
        return None

    text = date_tag.get_text(strip=True)
    now = datetime.now()

    # 오늘 글: "14:32" 같은 시:분 형식
    if re.match(r"^\d{1,2}:\d{2}$", text):
        return now.date()

    # 이전 글: "08.19" 또는 "08/19" 같은 월.일 형식
    m = re.match(r"^(\d{1,2})[.\-/](\d{1,2})$", text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            d = datetime(now.year, month, day).date()
            if d > now.date():  # 연말/연초 경계 보정 (작년 글을 올해로 잘못 계산하는 경우)
                d = datetime(now.year - 1, month, day).date()
            return d
        except ValueError:
            return None

    return None


def fetch_recent_posts(per_board_limit=150, max_pages=8):
    """3개 게시판(핫딜/쿠폰/이벤트) 최신 글 목록을 모두 가져옵니다.
    한 페이지에 보통 20~25개만 있어서, 필요한 개수를 채울 때까지 페이지를 넘겨가며 가져옵니다.
    글은 최신순으로 정렬돼 있다고 가정하고, RECENT_DAYS보다 오래된 글이 나오면
    그 게시판은 더 이상 넘기지 않고 다음 게시판으로 넘어갑니다 (요청 수 절약)."""
    all_posts = []
    cutoff_date = (datetime.now() - timedelta(days=RECENT_DAYS - 1)).date()

    for board_name, board_url in BOARD_URLS.items():
        count = 0
        for page in range(1, max_pages + 1):
            page_url = f"{board_url}&page={page}"
            try:
                resp = requests.get(page_url, headers=HEADERS, timeout=10)
                resp.encoding = "euc-kr"  # 뽐뿌는 EUC-KR 인코딩을 씁니다
                soup = BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                print(f"⚠️ {board_name} 게시판 {page}페이지 불러오기 실패: {e}")
                break

            rows = soup.select("tr.baseList")
            if not rows:
                break  # 더 이상 글이 없으면 다음 게시판으로

            reached_old_post = False
            for row in rows:
                title_tag = row.select_one("a.baseList-title")
                if not title_tag:
                    continue

                post_date = _parse_post_date(row)
                if post_date is not None and post_date < cutoff_date:
                    reached_old_post = True
                    break  # 이 밑으로는 더 오래된 글만 있다고 보고 중단

                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")
                href = urljoin(board_url, href)
                recommend = _parse_recommend_count(row)
                all_posts.append({
                    "title": title, "link": href,
                    "recommend": recommend, "board": board_name,
                    "date": post_date,
                })
                count += 1
                if count >= per_board_limit:
                    break

            if reached_old_post or count >= per_board_limit:
                break

    return all_posts


def filter_lifestyle_deals(posts):
    """생활 할인정보 + 인기 있는 것만 필터링합니다. (날짜는 fetch 단계에서 이미 걸러짐)"""
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
        print(f"⚠️ 추천수를 못 읽었거나 기준({MIN_RECOMMEND}) 넘는 글이 없어서, 최신순으로 대체합니다.")
    return filtered


def get_today_deals(max_items=5):
    posts = fetch_recent_posts()
    deals = filter_lifestyle_deals(posts)
    return deals[:max_items]


if __name__ == "__main__":
    deals = get_today_deals()
    for d in deals:
        print(f"- [추천 {d['recommend']}] {d['title']} ({d['link']})")
