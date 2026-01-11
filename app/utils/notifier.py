import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import Optional, List
from app.core.config import global_config

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    邮件通知处理程序。
    使用 SMTP 配置发送邮件。
    """

    def __init__(self) -> None:
        """
        使用环境变量或配置文件初始化 EmailNotifier。
        """
        # 优先使用环境变量，然后是配置文件
        self.smtp_server: str = str(global_config.get("email.smtp_server", "") or "")
        self.smtp_port: int = int(global_config.get("email.smtp_port", 465))
        self.sender_email: str = str(global_config.get("email.sender_email", "") or "")
        self.sender_password: str = str(global_config.get("email.sender_password", "") or "")

        receiver_config = global_config.get("email.receiver_emails", [])
        if receiver_config is None:
            receiver_config = []
        if not isinstance(receiver_config, list):
            receiver_config = [receiver_config]
        self.receiver_emails: List[str] = [
            str(email).strip() for email in receiver_config if str(email).strip()
        ]


    def send_message(self, title: str, content: str) -> None:
        """
        发送邮件通知。

        Args:
            title: 邮件主题。
            content: 邮件正文内容。
        """
        if not all(
            [
                self.smtp_server,
                self.sender_email,
                self.sender_password,
                self.receiver_emails,
            ]
        ):
            logger.warning("邮件配置不完整。跳过邮件通知。")
            logger.info(f"通知 - 标题: {title}, 内容: {content}")
            return

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

            server.login(self.sender_email, self.sender_password)  # type: ignore
            # 发送给所有接收者
            server.sendmail(self.sender_email, self.receiver_emails, message.as_string())  # type: ignore
            server.quit()
            logger.info(f"邮件通知已发送: {title}")
        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")


# 单例实例
notifier = EmailNotifier()
