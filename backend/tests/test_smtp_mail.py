import smtplib
import threading
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.config import Settings
from app.mail import MailConfigurationError, MailDeliveryError, SmtpMailer


def settings(**overrides):
    return Settings(
        _env_file=None,
        supabase_url="http://127.0.0.1:54321",
        supabase_secret_key="test-only",
        **overrides,
    )


class MailTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = settings(
            smtp_username="sender@gmail.com", smtp_password="test-app-password"
        )

    async def test_verification_message_uses_tls_before_authentication(self):
        with patch("app.mail.smtplib.SMTP") as factory:
            smtp = factory.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            await SmtpMailer(self.config).send_verification_email(
                "member@example.com", "123456", expires_minutes=5
            )
            factory.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
            names = [call[0] for call in smtp.method_calls]
            self.assertLess(names.index("starttls"), names.index("login"))
            smtp.login.assert_called_once_with("sender@gmail.com", "test-app-password")
            message = smtp.send_message.call_args.args[0]
            self.assertEqual(message["To"], "member@example.com")
            self.assertEqual(message["From"].addresses[0].addr_spec, "sender@gmail.com")
            self.assertIn("123456", message.get_content())
            self.assertIn("5분", message.get_content())

    async def test_ssl_port_and_html_alternative(self):
        config = self.config.model_copy(update={"smtp_port": 465})
        with patch("app.mail.smtplib.SMTP_SSL") as factory:
            smtp = factory.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            await SmtpMailer(config).send_email(
                "member@example.com", "제목", "본문", html="<p>본문</p>"
            )
            self.assertEqual(factory.call_args.args, ("smtp.gmail.com", 465))
            self.assertIsNotNone(factory.call_args.kwargs["context"])
            smtp.starttls.assert_not_called()
            message = smtp.send_message.call_args.args[0]
            self.assertEqual(message.get_body(preferencelist=("html",)).get_content(), "<p>본문</p>\n")

    async def test_unconfigured_mail_fails_without_network(self):
        with patch("app.mail.smtplib.SMTP") as factory:
            with self.assertRaises(MailConfigurationError):
                await SmtpMailer(settings()).send_email("member@example.com", "Hi", "Body")
            factory.assert_not_called()

    async def test_delivery_errors_do_not_expose_smtp_response(self):
        for error in (
            smtplib.SMTPAuthenticationError(535, b"test-app-password"),
            TimeoutError("test-app-password"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("app.mail.smtplib.SMTP", side_effect=error):
                    with self.assertRaises(MailDeliveryError) as caught:
                        await SmtpMailer(self.config).send_email("member@example.com", "Hi", "Body")
                    self.assertNotIn("test-app-password", str(caught.exception))
                    self.assertTrue(caught.exception.__suppress_context__)

    async def test_cleanup_failure_does_not_turn_accepted_mail_into_failure(self):
        for error in (smtplib.SMTPResponseException(500, b'QUIT failed'),
                      OSError('connection closed')):
            with self.subTest(error=type(error).__name__):
                with patch('app.mail.smtplib.SMTP') as factory:
                    smtp = factory.return_value.__enter__.return_value
                    smtp.send_message.return_value = {}
                    factory.return_value.__exit__.side_effect = error
                    result = await SmtpMailer(self.config).send_email(
                        'member@example.com', 'Hi', 'Body')
                    self.assertIsNone(result)

    async def test_refused_recipient_is_failure(self):
        with patch("app.mail.smtplib.SMTP") as factory:
            smtp = factory.return_value.__enter__.return_value
            smtp.send_message.return_value = {"member@example.com": (550, b"Rejected")}
            with self.assertRaises(MailDeliveryError):
                await SmtpMailer(self.config).send_email("member@example.com", "Hi", "Body")

    async def test_invalid_headers_fail_before_network(self):
        for recipient, subject in (
            ("member@example.com\r\nBcc: other@example.com", "Hi"),
            ("member@example.com,other@example.com", "Hi"),
            ("invalid", "Hi"),
            ("member@example.com", "Hi\nBcc: other@example.com"),
        ):
            with self.subTest(recipient=recipient, subject=subject):
                with patch("app.mail.smtplib.SMTP") as factory:
                    with self.assertRaises(ValueError):
                        await SmtpMailer(self.config).send_email(recipient, subject, "Body")
                    factory.assert_not_called()

    async def test_network_work_runs_outside_event_loop_thread(self):
        main_thread = threading.get_ident()
        threads = []
        with patch("app.mail.smtplib.SMTP") as factory:
            smtp = factory.return_value.__enter__.return_value
            def send(message):
                threads.append(threading.get_ident())
                return {}
            smtp.send_message.side_effect = send
            await SmtpMailer(self.config).send_email("member@example.com", "Hi", "Body")
        self.assertEqual(len(threads), 1)
        self.assertNotEqual(threads[0], main_thread)

    def test_environment_settings_and_secret_masking(self):
        with patch.dict("os.environ", {
            "SMTP_USERNAME": "env@gmail.com", "SMTP_PASSWORD": "environment-password",
            "SMTP_PORT": "465", "SMTP_TIMEOUT_SECONDS": "20",
        }, clear=True):
            config = settings()
        self.assertEqual(config.smtp_username, "env@gmail.com")
        self.assertEqual(config.smtp_password.get_secret_value(), "environment-password")
        self.assertEqual(config.smtp_port, 465)
        self.assertEqual(config.smtp_timeout_seconds, 20)
        self.assertNotIn("environment-password", repr(config))

    def test_unsafe_port_and_timeout_rejected(self):
        for overrides in ({"smtp_port": 25}, {"smtp_timeout_seconds": 0}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    settings(**overrides)


if __name__ == "__main__":
    unittest.main()
