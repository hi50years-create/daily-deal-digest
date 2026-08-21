from scripts.fetch_deals import get_today_deals
from scripts.build_draft import build_draft_material
from scripts.send_email import send_email


def main():
    deals = get_today_deals(max_items=5)

    if not deals:
        print("오늘은 쓸만한 생활 할인정보를 못 찾았어요. 메일 안 보내고 종료합니다.")
        return

    html_content = build_draft_material(deals)
    send_email(html_content)
    print(f"완료! {len(deals)}건 재료를 메일로 보냈어요. (API 비용 없음)")


if __name__ == "__main__":
    main()
