"""
모든 핫딜 소스가 공유하는 것들:
- deal(딜) 딕셔너리 스키마와 생성 헬퍼 make_deal()
- 생활 할인정보 판별용 키워드 목록
- 날짜/추천수/중복제거 유틸

deal 딕셔너리 스키마 (기존 구조를 확장, 하위호환):
    {
      "title": str,          # 글 제목
      "link": str,           # 원문 URL
      "source": str,         # "뽐뿌" | "루리웹" | "클리앙" | "알구몬" | "텔레그램" | "쿠팡"
      "board": str,          # 하위 게시판/카테고리 (없으면 "")
      "recommend": int,      # 추천수 (모르면 0)
      "date": datetime.date | None,
      "price": str,          # 가격 표기 (커머스 API만 채움, 없으면 "")
      "price_value": int,    # 가격 숫자값 (모르면 0)
      "discount": str,       # 할인율 표기 예: "43%" (없으면 "")
      "image": str,          # 썸네일 URL (없으면 "")
      "is_affiliate": bool,  # 제휴 링크 여부 (쿠팡 True)
    }
"""

import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

# 공용 User-Agent (일부 사이트는 UA 없으면 차단함)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# 요청 타임아웃 (초)
TIMEOUT = 12

# 최근 며칠 이내 글만 포함 (오늘 포함 기준 일수)
RECENT_DAYS = 3

# 이 추천수 미만이면 후보에서 제외 (추천수를 읽을 수 있는 소스에 한함)
MIN_RECOMMEND = 3

# 생활 할인정보로 볼만한 키워드 (제목에 이 중 하나라도 포함되면 후보로 채택)
# 주의: "무료", "할인", "쿠폰", "특가" 같은 범용 단어는 넣지 않습니다.
# 커뮤니티 글 제목은 (가격/배송비) 형식이 많아서 "무료"만 넣어도
# 배송비 무료인 아무 상품이나 다 걸려버려요. 실제 브랜드명 위주로 좁힙니다.
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

    # ── 아래는 '실제 특가가 자주 올라오는' 것 위주로 추가 (2026-08) ──
    # 마트/이커머스: 대량 식품·생필품 반값 특가 단골
    # (쿠팡은 골드박스 API로 따로 수집, 네이버는 거의 모든 글에 붙어서 제외)
    "트레이더스", "이마트", "홈플러스", "노브랜드", "마켓컬리", "컬리", "SSG", "11번가",
    # 생필품/육아: 핫딜 게시판 최다 카테고리 중 하나
    "올리브영", "다이소", "물티슈", "기저귀", "분유", "다우니", "섬유유연제",
    "페브리즈", "치약", "샴푸",
    # 식품/음료: 라면·과자·제로음료 대량 특가
    "농심", "오뚜기", "삼양라면", "오리온", "롯데웰푸드", "해태",
    "코카콜라", "펩시", "제로콜라", "칠성사이다", "서울우유",
    # 영양제/건강: 가성비 딜이 매우 활발
    "비타민", "유산균", "프로바이오틱스", "오메가3", "루테인", "밀크씨슬",
    "콜라겐", "프로틴", "닭가슴살",
    # 문화/여행: 예매권·숙박쿠폰 특가
    "CGV", "메가박스", "롯데시네마", "야놀자", "여기어때", "아고다", "밀리의서재",

    # ── 스포츠/아웃도어 (블로그 주제와 정렬, 2026-08) ──
    # 스포츠 브랜드
    "나이키", "아디다스", "뉴발란스", "아식스", "언더아머", "데카트론", "푸마",
    "리복", "호카", "살로몬", "네파", "K2", "블랙야크", "노스페이스",
    "컬럼비아", "아크테릭스", "파타고니아", "디스커버리",
    # 러닝/홈트/피트니스
    "러닝화", "트레드밀", "런닝머신", "덤벨", "아령", "케틀벨", "요가매트",
    "폼롤러", "저항밴드", "철봉", "푸쉬업바",
    # 보충제 (프로틴·닭가슴살은 위 건강 그룹에 이미 있음)
    "크레아틴", "BCAA", "게이너", "프로틴바",
    # 골프
    "골프공", "골프화", "골프클럽", "골프장갑", "거리측정기", "보이스캐디",
    "타이틀리스트", "캘러웨이", "젝시오", "PXG",
    # 등산/캠핑/아웃도어
    "등산화", "등산복", "캠핑", "텐트", "침낭", "코펠", "스탠리", "콜맨",
    "헬리녹스", "아이스박스",
    # 자전거/구기/기타
    "자전거", "로드바이크", "자전거헬멧", "축구공", "농구공", "배드민턴",
    "요넥스", "윌슨", "수영복", "수경",
]

# 확실히 제외할 카테고리(전자기기/컴퓨터 부품 등, 생활 할인이랑 거리가 멂)
EXCLUDE_KEYWORDS = [
    "그래픽카드", "CPU", "메모리", "SSD", "노트북", "모니터",
    "RAM", "파워", "메인보드", "그래픽",
]


def make_deal(title, link, source, board="", recommend=0, date=None,
              price="", price_value=0, discount="", image="", is_affiliate=False):
    """deal 딕셔너리를 기본값을 채워서 만든다. 모든 소스는 이걸 통해 딜을 생성한다."""
    return {
        "title": (title or "").strip(),
        "link": (link or "").strip(),
        "source": source,
        "board": board or "",
        "recommend": int(recommend or 0),
        "date": date,
        "price": price or "",
        "price_value": int(price_value or 0),
        "discount": discount or "",
        "image": image or "",
        "is_affiliate": bool(is_affiliate),
    }


def cutoff_date():
    """RECENT_DAYS 기준으로 '이 날짜보다 이전이면 오래된 글' 인 경계 날짜를 돌려준다."""
    return (datetime.now() - timedelta(days=RECENT_DAYS - 1)).date()


def is_recent(d):
    """딜의 date가 최근 범위 안이면 True. date가 None(모름)이면 안전하게 True."""
    if d.get("date") is None:
        return True
    return d["date"] >= cutoff_date()


def parse_struct_time(struct_time):
    """feedparser의 published_parsed(time.struct_time) → date. 실패하면 None."""
    if not struct_time:
        return None
    try:
        return datetime(*struct_time[:6]).date()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"[\[\(（【][^\]\)）】]*[\]\)）】]")
_PRICE_RE = re.compile(r"[\d,]+\s*원|\$\s*[\d.]+|₩\s*[\d,]+")
_NONWORD_RE = re.compile(r"[\s\-~/·,.!?\"'`]+")


def _normalize_title(title):
    """중복 판단용으로 제목을 정규화한다: 대괄호/소괄호 태그, 가격표기, 공백/기호 제거."""
    t = _TAG_RE.sub(" ", title)
    t = _PRICE_RE.sub(" ", t)
    t = _NONWORD_RE.sub("", t)
    return t.lower()


def _link_key(link):
    """중복 판단용 링크 키: host + path (쿼리스트링/프로토콜/모바일 서브도메인 무시)."""
    try:
        p = urlparse(link)
        host = p.netloc.lower()
        for prefix in ("www.", "m.", "mobile."):
            if host.startswith(prefix):
                host = host[len(prefix):]
        return f"{host}{p.path.rstrip('/')}"
    except ValueError:
        return link


def dedupe(deals):
    """제목 정규화 + 링크(host+path) 두 기준으로 중복 딜을 제거한다.
    먼저 온 것을 남긴다(소스 등록 순서가 우선순위). 단, 나중 것이 추천수가
    더 높거나 가격/이미지 정보가 있으면 그 필드를 채워 넣는다."""
    seen_title = {}
    seen_link = {}
    result = []
    for d in deals:
        tkey = _normalize_title(d["title"])
        lkey = _link_key(d["link"]) if d["link"] else None

        dup = None
        if tkey and tkey in seen_title:
            dup = seen_title[tkey]
        elif lkey and lkey in seen_link:
            dup = seen_link[lkey]

        if dup is not None:
            if d["recommend"] > dup["recommend"]:
                dup["recommend"] = d["recommend"]
            for field in ("price", "discount", "image"):
                if not dup[field] and d[field]:
                    dup[field] = d[field]
            continue

        if tkey:
            seen_title[tkey] = d
        if lkey:
            seen_link[lkey] = d
        result.append(d)
    return result


def _keyword_hit(title, keyword):
    """한글 키워드는 부분일치, 영문/숫자 키워드는 단어 경계 일치.
    (예: 'CU'가 'CUTE' 안에서, 'BBQ'가 'BBQR' 안에서 잘못 걸리는 것 방지)"""
    if re.fullmatch(r"[A-Za-z0-9]+", keyword):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", title) is not None
    return keyword in title


def has_excluded(title):
    return any(_keyword_hit(title, bad) for bad in EXCLUDE_KEYWORDS)


def has_lifestyle(title):
    return any(_keyword_hit(title, good) for good in LIFESTYLE_KEYWORDS)


def filter_lifestyle_deals(deals):
    """생활 할인정보 + 인기 있는 것만 필터링한다. (커뮤니티 소스용)

    - 전자기기 제외
    - 생활 브랜드 키워드 포함
    - 최근 글만
    - 추천수 MIN_RECOMMEND 이상 (단, 소스가 추천수를 못 주면 전부 0이므로
      그 경우엔 필터 없이 최신순으로라도 통과시킨다)
    """
    filtered = [
        d for d in deals
        if is_recent(d) and not has_excluded(d["title"]) and has_lifestyle(d["title"])
    ]

    popular = [d for d in filtered if d["recommend"] >= MIN_RECOMMEND]
    if popular:
        popular.sort(key=lambda d: d["recommend"], reverse=True)
        return popular

    if filtered:
        print(f"⚠️ 추천수 기준({MIN_RECOMMEND}) 넘는 글이 없어서 최신순으로 대체합니다.")
    return filtered


def filter_commerce_deals(deals):
    """커머스 특가(쿠팡 골드박스 등)용 필터.

    골드박스는 쿠팡이 자체 지정한 특가라 관심 없는 상품(놀이공원 입장권 등)이
    잔뜩 섞여 있다. 그래서 커뮤니티 딜과 똑같이 LIFESTYLE_KEYWORDS 에 걸리는 것만
    통과시킨다 (전자기기는 제외). 관심 브랜드/카테고리는 그 목록에 추가하면 된다.
    """
    return [
        d for d in deals
        if not has_excluded(d["title"]) and has_lifestyle(d["title"])
    ]


def cap_per_source(deals, limit):
    """소스별로 최대 limit개까지만 남긴다. 입력 순서(정렬된 상태)를 유지."""
    counts = {}
    result = []
    for d in deals:
        src = d["source"]
        if counts.get(src, 0) >= limit:
            continue
        counts[src] = counts.get(src, 0) + 1
        result.append(d)
    return result


def print_deals(deals):
    """소스 모듈을 단독 실행했을 때 결과를 사람이 보기 좋게 출력한다."""
    if not deals:
        print("(수집된 딜 없음)")
        return
    for d in deals:
        bits = [d["source"]]
        if d["board"]:
            bits.append(d["board"])
        if d["recommend"]:
            bits.append(f"추천 {d['recommend']}")
        if d["price"]:
            bits.append(d["price"])
        if d["discount"]:
            bits.append(d["discount"])
        meta = " · ".join(bits)
        print(f"- [{meta}] {d['title']}")
        print(f"  {d['link']}")
