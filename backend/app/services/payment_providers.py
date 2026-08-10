from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.config import settings


class PaymentProviderError(RuntimeError):
    pass


class PaymentProvider(Protocol):
    name: str
    def verify_webhook(self, body: bytes, signature: str | None) -> bool: ...
    async def initialize_checkout(self, *, email: str, amount_minor: int, currency: str, reference: str, callback_url: str) -> dict[str, Any]: ...
    async def create_refund(self, *, transaction_reference: str, amount_minor: int, currency: str, reference: str) -> dict[str, Any]: ...
    async def retrieve_refund(self, *, provider_reference: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class StripePaymentProvider:
    name: str = "STRIPE"

    def verify_webhook(self, body: bytes, signature: str | None) -> bool:
        secret = settings.stripe_webhook_secret
        if not secret or not signature:
            return False
        # Stripe's official SDK performs timestamp/tolerance validation; use it
        # when installed and retain a strict HMAC fallback for test fixtures.
        try:
            import stripe
            stripe.WebhookSignature.verify_header(body.decode(), signature, secret)
            return True
        except Exception:
            expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature.removeprefix("sha256="))

    async def initialize_checkout(self, *, email: str, amount_minor: int, currency: str, reference: str, callback_url: str) -> dict[str, Any]:
        if not settings.stripe_secret_key:
            raise PaymentProviderError("Stripe is not configured")
        try:
            import stripe
            stripe.api_key = settings.stripe_secret_key
            session = await stripe.checkout.Session.create_async(mode="payment", customer_email=email, line_items=[{"price_data": {"currency": currency.lower(), "product_data": {"name": "ClinicalFlow Pro"}, "unit_amount": amount_minor}, "quantity": 1}], success_url=callback_url, cancel_url=settings.payment_cancel_url, metadata={"reference": reference})
            return {"provider": self.name, "provider_reference": session.id, "checkout_url": session.url}
        except Exception as error:
            raise PaymentProviderError("Stripe checkout initialization failed") from error

    async def create_refund(self, *, transaction_reference: str, amount_minor: int, currency: str, reference: str) -> dict[str, Any]:
        if not settings.stripe_secret_key:
            raise PaymentProviderError("Stripe is not configured")
        try:
            import stripe
            stripe.api_key = settings.stripe_secret_key
            refund = await stripe.Refund.create_async(payment_intent=transaction_reference, amount=amount_minor, metadata={"reference": reference})
            return {"provider": self.name, "provider_reference": refund.id, "status": str(refund.status or "pending").upper()}
        except Exception as error:
            raise PaymentProviderError("Stripe refund creation failed") from error

    async def retrieve_refund(self, *, provider_reference: str) -> dict[str, Any]:
        if not settings.stripe_secret_key:
            raise PaymentProviderError("Stripe is not configured")
        try:
            import stripe
            stripe.api_key = settings.stripe_secret_key
            refund = await stripe.Refund.retrieve_async(provider_reference)
            return {"provider": self.name, "provider_reference": refund.id, "status": str(refund.status or "pending").upper()}
        except Exception as error:
            raise PaymentProviderError("Stripe refund retrieval failed") from error


@dataclass(frozen=True)
class PaystackPaymentProvider:
    name: str = "PAYSTACK"

    def verify_webhook(self, body: bytes, signature: str | None) -> bool:
        secret = settings.paystack_webhook_secret or settings.paystack_secret_key
        return bool(secret and signature and hmac.compare_digest(hmac.new(secret.encode(), body, hashlib.sha512).hexdigest(), signature))

    async def initialize_checkout(self, *, email: str, amount_minor: int, currency: str, reference: str, callback_url: str) -> dict[str, Any]:
        if not settings.paystack_secret_key:
            raise PaymentProviderError("Paystack is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post("https://api.paystack.co/transaction/initialize", headers={"Authorization": f"Bearer {settings.paystack_secret_key}"}, json={"email": email, "amount": amount_minor, "currency": currency, "reference": reference, "callback_url": callback_url})
        if response.status_code >= 400:
            raise PaymentProviderError("Paystack checkout initialization failed")
        data = response.json().get("data") or {}
        return {"provider": self.name, "provider_reference": data.get("reference") or reference, "checkout_url": data.get("authorization_url")}

    async def create_refund(self, *, transaction_reference: str, amount_minor: int, currency: str, reference: str) -> dict[str, Any]:
        if not settings.paystack_secret_key:
            raise PaymentProviderError("Paystack is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post("https://api.paystack.co/refund", headers={"Authorization": f"Bearer {settings.paystack_secret_key}"}, json={"transaction": transaction_reference, "amount": amount_minor, "currency": currency, "customer_note": reference})
        if response.status_code >= 400:
            raise PaymentProviderError("Paystack refund creation failed")
        data = response.json().get("data") or {}
        return {"provider": self.name, "provider_reference": str(data.get("id") or data.get("refund_id") or reference), "status": str(data.get("status") or "PENDING").upper()}

    async def retrieve_refund(self, *, provider_reference: str) -> dict[str, Any]:
        if not settings.paystack_secret_key:
            raise PaymentProviderError("Paystack is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"https://api.paystack.co/refund/{provider_reference}", headers={"Authorization": f"Bearer {settings.paystack_secret_key}"})
        if response.status_code >= 400:
            raise PaymentProviderError("Paystack refund retrieval failed")
        data = response.json().get("data") or {}
        return {"provider": self.name, "provider_reference": str(data.get("id") or provider_reference), "status": str(data.get("status") or "PENDING").upper()}


def provider_for_country(country_code: str) -> PaymentProvider:
    return PaystackPaymentProvider() if country_code.upper() in {"NG", "GH", "KE", "ZA"} else StripePaymentProvider()


def provider_for_name(provider: str) -> PaymentProvider:
    normalized = provider.upper()
    if normalized == "STRIPE":
        return StripePaymentProvider()
    if normalized == "PAYSTACK":
        return PaystackPaymentProvider()
    raise PaymentProviderError("Unsupported payment provider")
