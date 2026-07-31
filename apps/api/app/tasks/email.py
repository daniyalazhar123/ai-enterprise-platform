from __future__ import annotations

from typing import Any

import aiosmtplib
from email.message import EmailMessage

from apps.api.app.core.config import settings


async def send_email(
    to: str,
    subject: str,
    body: str,
    html: str | None = None,
) -> dict[str, Any]:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if html:
        msg.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_PORT == 587,
        )
        return {"success": True, "to": to}
    except Exception as e:
        return {"success": False, "to": to, "error": str(e)}


async def send_verification_email(to: str, token: str) -> dict[str, Any]:
    verify_url = f"https://app.ai-enterprises.com/auth/verify?token={token}"
    return await send_email(
        to=to,
        subject="Verify your email address",
        body=f"Click here to verify your email: {verify_url}",
        html=f'<p>Click <a href="{verify_url}">here</a> to verify your email.</p>',
    )


async def send_password_reset_email(to: str, token: str) -> dict[str, Any]:
    reset_url = f"https://app.ai-enterprises.com/auth/reset?token={token}"
    return await send_email(
        to=to,
        subject="Reset your password",
        body=f"Click here to reset your password: {reset_url}",
        html=f'<p>Click <a href="{reset_url}">here</a> to reset your password.</p>',
    )