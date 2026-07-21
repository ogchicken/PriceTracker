from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass
from typing import Any

import resend

from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    idempotency_key: str


class EmailProvider(abc.ABC):
    @abc.abstractmethod
    async def send(self, message: EmailMessage) -> str:
        raise NotImplementedError


class ResendEmailProvider(EmailProvider):
    def __init__(self, api_key: str, from_address: str) -> None:
        self.from_address = from_address
        resend.api_key = api_key

    async def send(self, message: EmailMessage) -> str:
        def _send() -> Any:
            return resend.Emails.send(
                {
                    "from": self.from_address,
                    "to": [message.to],
                    "subject": message.subject,
                    "html": message.html,
                },
                {"idempotency_key": message.idempotency_key},
            )

        result = await asyncio.to_thread(_send)
        return str(result.get("id", ""))


class LoggingEmailProvider(EmailProvider):
    """Non-delivering provider used only by development and tests."""

    async def send(self, message: EmailMessage) -> str:
        logger.info("email_suppressed", recipient=message.to, subject=message.subject)
        return f"suppressed:{message.idempotency_key}"


def build_email_provider(settings: Settings) -> EmailProvider:
    if settings.resend_api_key:
        return ResendEmailProvider(settings.resend_api_key, settings.email_from)
    if settings.environment in {"development", "test"}:
        return LoggingEmailProvider()
    raise RuntimeError("Resend API key is required outside development and test")
