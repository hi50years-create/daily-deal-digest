"""
API 호출 없이, 수집된 할인정보를 보기 좋은 '재료 노트' 형태로 정리합니다.
완성된 블로그 글이 아니라, 사람(또는 Claude 채팅)이 다듬을 재료예요.
"""

from datetime import datetime


def build_draft_material(deals):
    """할인정보 리스트를 이메일에 넣을 HTML로 정리합니다. (무료, API 미사용)"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

    items_html = ""
    for i, deal in enumerate(deals, 1):
        rec = deal.get("recommend", 0)
        items_html += f"""
        <li style="margin-bottom:10px;">
          <b>{deal['title']}</b> <span style="color:#888; font-size:12px;">(추천 {rec})</span><br>
          <a href="{deal['link']}" style="color:#888; font-size:13px;">원문 보기</a>
        </li>
        """

    html = f"""
    <h2>{today} 할인정보 재료</h2>
    <p>오늘 커뮤니티에서 화제였던 생활 할인정보 후보 {len(deals)}건이에요.
    아직 다듬지 않은 원문 제목 그대로라, <b>그대로 블로그에 올리면 안 되고</b>
    아래 방법 중 하나로 다듬어서 쓰세요.</p>
    <ol>
      {items_html}
    </ol>
    <hr>
    <p style="font-size:13px; color:#888;">
    💡 <b>다듬는 방법</b>: 이 리스트를 통째로 복사해서 Claude 채팅창에 붙여넣고
    "이 할인정보로 오늘 블로그 글 하나 써줘" 라고 하면, 지금 쓰시는 구독 안에서
    바로 완성된 초안을 받을 수 있어요. (별도 API 비용 없음)
    </p>
    """
    return html
