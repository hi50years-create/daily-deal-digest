"""
작성된 HTML 초안을 이메일로 전송합니다.
Gmail 기준 (다른 메일이면 SMTP_HOST/PORT만 바꾸면 됨).
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_email(html_content, subject=None):
    # 환경변수는 실제로 보낼 때 읽는다 (DRY_RUN 등에서 import만 해도 되도록).
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    if not subject:
        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"[할인정보 초안] {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient

    # 목록만 그대로 이메일 본문에 넣음 (다른 설명 문구 없음)
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
