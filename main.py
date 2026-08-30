import os

from scripts.fetch_deals import get_today_deals
from scripts.build_draft import build_draft_material
from scripts.send_email import send_email


def main():
    deals = get_today_deals()

    if not deals:
        print("오늘은 쓸만한 생활 할인정보를 못 찾았어요. 메일 안 보내고 종료합니다.")
        return

    # 나중에 "그 딜 링크가 뭐였지?" 확인용으로 최종 목록을 로그에 남긴다.
    print("── 이번 발송 목록 ──")
    for d in deals:
        link = d["product_link"] or d["link"]
        print(f"  [{d['source']}] {d['title']}  →  {link}")

    html_content = build_draft_material(deals)

    # DRY_RUN=1 이면 메일을 보내지 않고 HTML만 출력한다 (테스트용).
    if os.environ.get("DRY_RUN") == "1":
        print("\n===== DRY RUN: 아래 HTML을 메일로 보냈을 것입니다 =====\n")
        print(html_content)
        print(f"\n(총 {len(deals)}건)")
        return

    send_email(html_content)
    print(f"완료! {len(deals)}건 재료를 메일로 보냈어요. (API 비용 없음)")


if __name__ == "__main__":
    main()
