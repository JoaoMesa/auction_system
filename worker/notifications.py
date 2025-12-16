"""
Serviço de notificações para envio de e-mails via SMTP e mensagens no Discord.
Retorna True/False para indicar sucesso. Possui fallback que apenas loga se
as credenciais não estiverem configuradas.
"""
import os
import smtplib
import traceback
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class NotificationService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_user or "noreply@lancecerto.com")

        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

        # Small info log
        self._log_config()

    def _log_config(self):
        print(f"📧 SMTP: {self.smtp_host}:{self.smtp_port} (user={'set' if self.smtp_user else 'not-set'})")
        print(f"🎮 Discord Webhook: {'set' if self.discord_webhook else 'not-set'}")

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Envia e-mail. Se as credenciais SMTP não estiverem disponíveis,
        faz log e retorna True (para não quebrar o fluxo).
        """
        try:
            if not self.smtp_user or not self.smtp_password:
                print("⚠️ Credenciais SMTP ausentes — logando e simulando envio.")
                self._log_simulated_email(to_email, subject, body)
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = to_email

            # plain text part
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            # basic html part (safe)
            html_body = f"""
            <html>
              <body>
                <div style="font-family: Arial, sans-serif; line-height:1.4; color:#111;">
                  {body.replace(chr(10), '<br>')}
                </div>
              </body>
            </html>
            """
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=20)
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, [to_email], msg.as_string())
                server.quit()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20)
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, [to_email], msg.as_string())
                server.quit()

            print(f"✅ Email enviado para {to_email}")
            return True

        except Exception as e:
            print(f"❌ Erro ao enviar e-mail para {to_email}: {e}")
            traceback.print_exc()
            # não quebra o fluxo, grava log
            self._log_simulated_email(to_email, subject, body)
            return False

    def _log_simulated_email(self, to_email: str, subject: str, body: str):
        print("\n📧 === E-MAIL (SIMULADO/LOG) ===")
        print(f"Para: {to_email}")
        print(f"Assunto: {subject}")
        print(f"Conteúdo (inicio): {body[:400]}")
        print("=" * 30 + "\n")

    def send_discord_message(self, content: str) -> bool:
        """
        Envia mensagem para discord via webhook. Retorna True se o envio teve sucesso or se webhook não estiver configurado (simulação).
        """
        try:
            if not self.discord_webhook:
                print("⚠️ Discord webhook não configurado — simulando envio.")
                self._log_simulated_discord(content)
                return True

            payload = {
                "content": content,
                "username": "Lance Certo Bot",
            }
            resp = requests.post(self.discord_webhook, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                print("✅ Mensagem enviada para Discord")
                return True
            else:
                print(f"❌ Discord retornou {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem para Discord: {e}")
            traceback.print_exc()
            self._log_simulated_discord(content)
            return False

    def _log_simulated_discord(self, content: str):
        print("\n🎮 === DISCORD (SIMULADO/LOG) ===")
        print(f"Conteúdo (inicio): {content[:400]}")
        print("=" * 30 + "\n")
