# 매일 할인정보 자료 수집 봇 (멀티소스 버전)

매일 정해진 시간에 여러 핫딜 소스에서 생활 할인정보를 찾아서,
소스별로 정리된 목록을 이메일로 보내주는 자동화 파이프라인입니다.

**💰 비용: 0원** (쿠팡 파트너스를 켜도 API 이용료는 없음).

**⚠️ 완성된 블로그 글이 아니라 "재료 목록"이 옵니다.** 아침에 메일 받으면
통째로 복사해서 Claude 채팅에 붙여넣고 "이 할인정보로 블로그 글 써줘" 하면
완성본을 받을 수 있어요.

## 수집 소스

| 소스 | 방식 | 비고 |
|---|---|---|
| 뽐뿌 (핫딜/쿠폰/이벤트) | RSS | 셀렉터 안 깨짐 |
| 루리웹 예판·핫딜 | RSS | |
| 클리앙 알뜰구매 | HTML 스크래핑 | 데이터센터 IP를 막을 때가 있음 (불안정하면 `SOURCES`에서 제외) |
| 알구몬 | HTML 스크래핑 | 여러 커뮤니티(퀘이사존·아카라이브·어미새·zod 등) 집계 |
| 텔레그램 `hotdeal_kr` | 웹 미리보기(`t.me/s/`) | 로그인·키 불필요 |
| 쿠팡 파트너스 | Open API | **키 있을 때만** — 가격·할인율·이미지·제휴링크 포함 |
| 알리익스프레스 | (스텁) | 계정 생기면 키만 넣으면 동작 |

소스 간 중복은 제목/링크로 자동 제거되고, 겹치면 원본 커뮤니티 링크를 남깁니다.

### 쿠팡 골드박스

쿠팡 "골드박스"는 **쿠팡이 자체적으로 지정한 특가**라 관심 없는 상품(놀이공원
입장권 등)도 잔뜩 섞여 있고, 다른 쇼핑몰이 더 싼 경우도 있습니다. 그래서 골드박스도
커뮤니티 딜과 똑같이 **`LIFESTYLE_KEYWORDS` 에 걸리는 것만** 메일에 넣습니다.
받고 싶은 카테고리는 그 목록(`scripts/sources/common.py`)에 추가하세요.

(무료로 쓸 수 있던 네이버 쇼핑 검색 API가 2026-07-31 종료되어 자동 최저가 대조는
빠져 있습니다. 남는 항목도 가격은 직접 확인하세요.)

## 준비물 (딱 한 번만 설정)

1. **GitHub 저장소** — 이 폴더 전체를 업로드
2. **Gmail 앱 비밀번호** — 구글 계정 > 보안 > 2단계 인증 켠 뒤 "앱 비밀번호" 생성
3. **받을 이메일 주소**

## GitHub Secrets (필수 3개)

저장소 Settings > Secrets and variables > Actions > **Secrets** 탭:

| Secret 이름 | 값 |
|---|---|
| `SMTP_USER` | 발신용 Gmail 주소 |
| `SMTP_PASS` | 앱 비밀번호 (일반 비밀번호 아님!) |
| `RECIPIENT_EMAIL` | 받으실 이메일 주소 |

## GitHub Variables / Secrets (선택)

**Variables** 탭 (민감정보 아님):

| 이름 | 기본값 | 설명 |
|---|---|---|
| `SOURCES` | `ppomppu,ruliweb,clien,algumon,telegram` | 켤 소스 목록(콤마구분). 특정 소스를 빼고 싶을 때 |
| `TELEGRAM_CHANNELS` | `hotdeal_kr` | 읽을 텔레그램 채널(콤마구분). `t.me/s/<이름>` 이 열리는 공개 채널이어야 함 |
| `COUPANG_KEYWORDS` | (없음) | 지정 시 쿠팡 골드박스 외에 이 키워드들도 검색(3~5개 권장) |

**Secrets** 탭 (선택 기능):

| 이름 | 값 |
|---|---|
| `COUPANG_ACCESS_KEY` | 파트너스 → 내 계정 → 파트너스 API 에서 발급 |
| `COUPANG_SECRET_KEY` | 〃 |

쿠팡 키 2개가 등록되면 쿠팡 소스가 자동으로 켜집니다. 쿠팡 링크는 제휴(파트너스)
링크라 메일 하단에 고지 문구가 자동으로 붙습니다.

## 테스트 방법

1. 저장소 Actions 탭 > "매일 할인정보 초안 메일 발송" > "Run workflow"
2. 몇 분 뒤 메일함 확인
3. 로그에서 소스별 수집 건수(`· ppomppu: 45건 수집` …)와
   한 소스 실패 시 `건너뜁니다` 메시지를 볼 수 있어요

로컬 테스트 (메일 발송 없이 HTML만 출력):

```bash
pip install -r requirements.txt
DRY_RUN=1 python main.py                    # 전체 파이프라인
python -m scripts.sources.ppomppu           # 소스 하나만
python -m scripts.sources.telegram
```

## 발행 시간 바꾸기

`.github/workflows/daily-deals.yml`의 `cron: '0 23 * * *'` 수정 (UTC 기준, 한국시간 -9시간).

## 필터 키워드 조정 (중요)

`scripts/sources/common.py`의 `LIFESTYLE_KEYWORDS` 가 "생활 할인정보"를 걸러냅니다.
**이 목록에 없는 브랜드/카테고리는 아무리 소스를 늘려도 메일에 안 나옵니다.**
카페·외식 위주로 좁게 잡혀 있으니, 관심 있는 브랜드(마트·생필품·화장품 등)를
직접 추가하세요. `EXCLUDE_KEYWORDS` 는 반대로 걸러낼 것(전자기기 등)입니다.

영문/숫자 키워드(`CU`, `BBQ` 등)는 단어 경계로 매칭해서 `CUTE` 같은 오탐을 막습니다.

## 소스가 깨졌을 때

- 뽐뿌/루리웹: RSS 주소 변경 여부 확인 (`scripts/sources/ppomppu.py`, `ruliweb.py`)
- 클리앙/알구몬: 사이트 개편으로 CSS 셀렉터가 안 맞을 수 있음
  (`scripts/sources/clien.py`, `algumon.py`)
- 특정 소스만 계속 실패하면 `SOURCES` 에서 빼도 나머지는 정상 동작합니다

## 나중에 완전 자동 글쓰기로 업그레이드

`scripts/build_draft.py`를 Claude API 호출 버전으로 바꾸면 됩니다 (월 1달러 미만 예상).
