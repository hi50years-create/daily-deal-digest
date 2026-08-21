"""
작성된 HTML 초안을 이메일로 전송합니다.
Gmail 기준 (다른 메일이면 SMTP_HOST/PORT만 바꾸면 됨).
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]


def send_email(html_content, subject=None):
    if not subject:
        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"[할인정보 초안] {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT_EMAIL

    # 정리된 재료 노트를 그대로 이메일 본문에 넣음
    body = f"""
    <p>오늘의 할인정보 재료예요. 완성된 글이 아니라, 다듬어서 쓸 재료 목록이에요.</p>
    <hr>
    {html_content}
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
