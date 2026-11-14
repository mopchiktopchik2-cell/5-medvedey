"""Отправка коммерческого предложения на email.

Если SMTP не настроен (нет ``SMTP_HOST``), письмо с PDF не теряется:
оно сохраняется в ``outbox`` как .eml, который можно открыть почтовым клиентом.
"""

import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Literal

from app.config import settings
from app.models import Estimate, Settings
from app.pdf import fmt_money

EmailStatus = Literal["sent", "outbox"]


class EmailDeliveryError(RuntimeError):
    """SMTP настроен, но отправить письмо не удалось."""


@dataclass(frozen=True)
class EmailResult:
    status: EmailStatus
    detail: str


def _ascii_filename(number: str) -> str:
    transliterated = number.replace("КП", "KP").replace("кп", "kp")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", transliterated).strip("-")
    return cleaned or "KP"


def build_message(
    estimate: Estimate,
    company: Settings,
    pdf_bytes: bytes,
    to: str,
    comment: str | None = None,
) -> EmailMessage:
    subject = f"Коммерческое предложение № {estimate.number} — {company.company_name}"
    created = estimate.created_at.strftime("%d.%m.%Y")

    lines = [
        "Здравствуйте!",
        "",
        f"Направляем коммерческое предложение № {estimate.number} от {created}.",
        "",
        f"Изделие: {estimate.product_type_name}, тираж {estimate.quantity} шт.",
        f"Сложность: {estimate.complexity_name}",
        f"Себестоимость единицы: {fmt_money(estimate.unit_cost)}",
        f"Итого за тираж: {fmt_money(estimate.total_cost)}",
        f"Срок изготовления: до {estimate.lead_time_days} рабочих дней.",
    ]
    if comment:
        lines.extend(["", comment.strip()])
    lines.extend(
        [
            "",
            "Документ во вложении. Будем рады ответить на вопросы.",
            "",
            company.company_name,
            company.company_requisites,
        ]
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user or "no-reply@mir.local"
    message["To"] = to
    message.set_content("\n".join(lines))
    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"{_ascii_filename(estimate.number)}.pdf",
    )
    return message


def send_estimate_email(
    estimate: Estimate,
    company: Settings,
    pdf_bytes: bytes,
    to: str,
    comment: str | None = None,
) -> EmailResult:
    message = build_message(estimate, company, pdf_bytes, to, comment)

    if not settings.smtp_host:
        outbox = Path(settings.outbox_dir)
        outbox.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")
        path = outbox / f"{_ascii_filename(estimate.number)}-{stamp}.eml"
        path.write_bytes(bytes(message))
        return EmailResult(
            status="outbox",
            detail=f"SMTP не настроен: письмо сохранено в {path}",
        )

    try:
        context = ssl.create_default_context()
        if settings.smtp_use_ssl:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=context,
            )
        else:
            server = smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            )
        with server:
            if settings.smtp_starttls:
                server.starttls(context=context)
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password or "")
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(f"Не удалось отправить письмо: {exc}") from exc

    return EmailResult(status="sent", detail=f"КП отправлено на {to}")
