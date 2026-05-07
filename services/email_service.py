#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送服务
Email Sending Service using SMTP
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from email.header import Header

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP email sending service. Reads config from settings at send time."""

    @staticmethod
    def _get_config():
        from config.settings import EMAIL_CONFIG
        return EMAIL_CONFIG

    @classmethod
    def _is_configured(cls) -> bool:
        cfg = cls._get_config()
        return bool(cfg["smtp_username"] and cfg["smtp_password"])

    @classmethod
    def send_verification_email(cls, to_email: str, code: str) -> bool:
        """Send a verification code email. Returns True on success."""
        cfg = cls._get_config()

        if not cls._is_configured():
            logger.warning("SMTP not configured, skipping email send to %s (code: %s)", to_email, code)
            return False

        subject = f"{cfg['from_name']} - 邮箱验证码"
        html_body = f"""\
<html>
<body style="font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; padding: 20px;">
    <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 22px;">TCM AI 中医智能诊疗</h1>
        </div>
        <div style="padding: 30px;">
            <p style="color: #374151; font-size: 16px; margin-bottom: 20px;">您的邮箱验证码为：</p>
            <div style="background: #f3f4f6; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 20px;">
                <span style="font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px;">{code}</span>
            </div>
            <p style="color: #9ca3af; font-size: 13px; line-height: 1.6;">
                验证码 5 分钟内有效，请勿泄露给他人。<br>
                如果您未进行此操作，请忽略本邮件。
            </p>
        </div>
    </div>
</body>
</html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((cfg["from_name"], cfg["smtp_username"]))
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if cfg.get("use_ssl", False):
                server = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
            else:
                server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
                if cfg["use_tls"]:
                    server.starttls()
            server.login(cfg["smtp_username"], cfg["smtp_password"])
            server.sendmail(cfg["smtp_username"], to_email, msg.as_string())
            server.quit()
            logger.info("Verification email sent to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            raise


email_service = EmailService()
