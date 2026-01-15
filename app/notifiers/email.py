from app.core import cfg
import logging
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import List
from .notifier import Notifier


class EmailNotifier(Notifier):
    """
    邮件通知处理程序。
    使用 SMTP 配置发送邮件。
    """

    def __init__(self) -> None:
        """
        初始化 EmailNotifier。
        """
        self.smtp_server: str = cfg.email.smtp_server
        self.smtp_port: int = cfg.email.smtp_port
        self.sender_email: str = cfg.email.sender_email
        self.sender_password: str = cfg.email.sender_password
        self.receiver_emails: List[str] = cfg.email.receiver_emails

    def notify(self, title: str, content: str) -> None:
        """
        发送邮件通知。

        Args:
            title: 邮件主题。
            content: 邮件正文内容。
        """
        message = MIMEText(content, "html", "utf-8")
        message["From"] = self.sender_email
        # 邮件头显示所有接收者
        message["To"] = ", ".join(self.receiver_emails)
        message["Subject"] = str(Header(title, "utf-8"))
        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(
                self.sender_email, self.receiver_emails, message.as_string()
            )
            server.quit()
            logging.info(f"邮件通知已发送: {title} {content}")
        except Exception as e:
            logging.error(f"发送邮件通知失败: {e}")
