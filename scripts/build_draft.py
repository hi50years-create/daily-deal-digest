"""
API 호출 없이, 수집된 할인정보를 목록만 깔끔하게 정리합니다.
설명/안내 문구 없이 리스트만 출력합니다.
"""


def build_draft_material(deals):
    """할인정보 리스트를 이메일에 넣을 HTML로 정리합니다. (무료, API 미사용)"""
    items_html = ""
    for deal in deals:
        rec = deal.get("recommend", 0)
        board = deal.get("board", "")
        items_html += f"""
        <li style="margin-bottom:10px;">
          <b>{deal['title']}</b> <span style="color:#888; font-size:12px;">[{board}] (추천 {rec})</span><br>
          <a href="{deal['link']}" style="color:#888; font-size:13px;">원문 보기</a>
        </li>
        """

    return f"<ol>{items_html}</ol>"
