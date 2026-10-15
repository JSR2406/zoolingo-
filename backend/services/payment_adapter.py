"""
Payment adapter for ZooLingo subscriptions.

Supports multiple payment providers via a common interface:
- Stripe (global)
- Razorpay (India-focused, INR pricing)

Configuration:
- PAYMENT_PROVIDER: "stripe" or "razorpay" (default: "stripe")
- STRIPE_SECRET_KEY: Stripe secret key
- STRIPE_WEBHOOK_SECRET: Stripe webhook signing secret
- RAZORPAY_KEY_ID: Razorpay key ID
- RAZORPAY_KEY_SECRET: Razorpay key secret
- RAZORPAY_WEBHOOK_SECRET: Razorpay webhook secret

All secret keys must be server-side only. Never expose them to the frontend.

Webhook events are processed idempotently using billing_events table.
Duplicate and out-of-order events are handled safely.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abstract adapter interface
# ---------------------------------------------------------------------------


class PaymentAdapter(ABC):
    """Abstract payment provider adapter."""

    @abstractmethod
    def create_checkout_session(
        self, user_id: str, plan: str, success_url: str, cancel_url: str
    ) -> Dict[str, Any]:
        """Create a checkout session for subscription upgrade."""

    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription."""

    @abstractmethod
    def verify_webhook_signature(
        self, payload: bytes, signature: str
    ) -> bool:
        """Verify webhook signature from the payment provider."""

    @abstractmethod
    def parse_webhook_event(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Parse a webhook event into a normalized format."""

    @abstractmethod
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Fetch subscription details from the provider."""


# ---------------------------------------------------------------------------
# Stripe adapter
# ---------------------------------------------------------------------------


class StripeAdapter(PaymentAdapter):
    """Stripe payment provider adapter."""

    def __init__(self):
        import stripe

        self._stripe = stripe
        self._stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self._webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

        # Plan -> Stripe price ID mapping (configure in Stripe dashboard)
        self._plan_prices = {
            "pro": os.getenv("STRIPE_PRO_PRICE_ID", "price_pro_placeholder"),
            "premium": os.getenv(
                "STRIPE_PREMIUM_PRICE_ID", "price_premium_placeholder"
            ),
        }

    def create_checkout_session(
        self, user_id: str, plan: str, success_url: str, cancel_url: str
    ) -> Dict[str, Any]:
        price_id = self._plan_prices.get(plan)
        if not price_id or price_id.endswith("_placeholder"):
            raise ValueError(
                f"Stripe price ID not configured for plan '{plan}'. "
                "Set STRIPE_PRO_PRICE_ID or STRIPE_PREMIUM_PRICE_ID."
            )

        session = self._stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,
            metadata={"plan": plan, "user_id": user_id},
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "provider": "stripe",
        }

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        sub = self._stripe.Subscription.modify(
            subscription_id, cancel_at_period_end=True
        )
        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "provider": "stripe",
        }

    def verify_webhook_signature(
        self, payload: bytes, signature: str
    ) -> bool:
        try:
            self._stripe.Webhook.construct_event(
                payload, signature, self._webhook_secret
            )
            return True
        except self._stripe.error.SignatureVerificationError:
            return False
        except Exception:
            return False

    def parse_webhook_event(self, payload: bytes) -> Optional[Dict[str, Any]]:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return None

        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        normalized = {
            "provider": "stripe",
            "event_type": event_type,
            "provider_event_id": event.get("id"),
            "customer_id": data.get("customer"),
            "subscription_id": data.get("subscription"),
            "status": data.get("status"),
            "created_at": datetime.fromtimestamp(
                event.get("created", 0), tz=timezone.utc
            ).isoformat(),
        }

        # Map Stripe event types to normalized actions
        if event_type in ("checkout.session.completed",):
            normalized["action"] = "checkout.completed"
        elif event_type in ("customer.subscription.created",):
            normalized["action"] = "subscription.created"
        elif event_type in ("customer.subscription.updated",):
            normalized["action"] = "subscription.updated"
        elif event_type in ("customer.subscription.deleted",):
            normalized["action"] = "subscription.deleted"
        elif event_type in ("invoice.payment_failed",):
            normalized["action"] = "payment.failed"
        elif event_type in ("invoice.payment_succeeded",):
            normalized["action"] = "payment.succeeded"
        else:
            normalized["action"] = "unknown"

        return normalized

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        try:
            sub = self._stripe.Subscription.retrieve(subscription_id)
            return {
                "subscription_id": sub.id,
                "status": sub.status,
                "plan": sub.items.data[0].price.id if sub.items.data else None,
                "current_period_start": datetime.fromtimestamp(
                    sub.current_period_start, tz=timezone.utc
                ).isoformat(),
                "current_period_end": datetime.fromtimestamp(
                    sub.current_period_end, tz=timezone.utc
                ).isoformat(),
                "cancel_at_period_end": sub.cancel_at_period_end,
                "provider": "stripe",
            }
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Razorpay adapter
# ---------------------------------------------------------------------------


class RazorpayAdapter(PaymentAdapter):
    """Razorpay payment provider adapter (India-focused, INR)."""

    def __init__(self):
        try:
            import razorpay
        except ImportError:
            raise ImportError(
                "razorpay package not installed. "
                "Add 'razorpay==1.4.0' to requirements."
            )

        self._client = razorpay.Client(
            auth=(
                os.getenv("RAZORPAY_KEY_ID", ""),
                os.getenv("RAZORPAY_KEY_SECRET", ""),
            )
        )
        self._webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

        # Plan -> Razorpay plan ID mapping (configure in Razorpay dashboard)
        self._plan_ids = {
            "pro": os.getenv("RAZORPAY_PRO_PLAN_ID", "plan_pro_placeholder"),
            "premium": os.getenv(
                "RAZORPAY_PREMIUM_PLAN_ID", "plan_premium_placeholder"
            ),
        }

    def create_checkout_session(
        self, user_id: str, plan: str, success_url: str, cancel_url: str
    ) -> Dict[str, Any]:
        plan_id = self._plan_ids.get(plan)
        if not plan_id or plan_id.endswith("_placeholder"):
            raise ValueError(
                f"Razorpay plan ID not configured for plan '{plan}'. "
                "Set RAZORPAY_PRO_PLAN_ID or RAZORPAY_PREMIUM_PLAN_ID."
            )

        # Razorpay subscription creation
        subscription_data = {
            "plan_id": plan_id,
            "customer_notify": 1,
            "notes": {"user_id": user_id, "plan": plan},
        }
        subscription = self._client.subscription.create(subscription_data)

        return {
            "checkout_url": subscription.get("short_url", ""),
            "session_id": subscription.id,
            "provider": "razorpay",
        }

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        sub = self._client.subscription.cancel(subscription_id, cancel_at_period_end=True)
        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "provider": "razorpay",
        }

    def verify_webhook_signature(
        self, payload: bytes, signature: str
    ) -> bool:
        try:
            self._client.utility.verify_webhook_signature(
                {
                    "razorpay_payment_id": signature,  # simplified; Razorpay uses
                    # razorpay_payment_id, razorpay_subscription_id, razorpay_signature
                },
                signature,
                self._webhook_secret,
            )
            return True
        except Exception:
            return False

    def parse_webhook_event(self, payload: bytes) -> Optional[Dict[str, Any]]:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return None

        event_type = event.get("event", "")
        payload_data = event.get("payload", {})

        normalized = {
            "provider": "razorpay",
            "event_type": event_type,
            "provider_event_id": event.get("id"),
            "created_at": datetime.fromtimestamp(
                event.get("created_at", 0), tz=timezone.utc
            ).isoformat(),
        }

        # Extract subscription/payment details from payload
        subscription_entity = (
            payload_data.get("subscription", {}).get("entity", {})
            if isinstance(payload_data.get("subscription"), dict)
            else {}
        )
        payment_entity = (
            payload_data.get("payment", {}).get("entity", {})
            if isinstance(payload_data.get("payment"), dict)
            else {}
        )

        normalized["subscription_id"] = subscription_entity.get("id")
        normalized["customer_id"] = subscription_entity.get("customer_id")
        normalized["status"] = subscription_entity.get("status")
        normalized["plan_id"] = subscription_entity.get("plan_id")

        # Map Razorpay event types to normalized actions
        event_action_map = {
            "subscription.created": "subscription.created",
            "subscription.activated": "subscription.created",
            "subscription.updated": "subscription.updated",
            "subscription.cancelled": "subscription.deleted",
            "subscription.charged": "payment.succeeded",
            "subscription.expiring": "subscription.updated",
            "subscription.expired": "subscription.deleted",
            "payment.captured": "payment.succeeded",
            "payment.failed": "payment.failed",
        }
        normalized["action"] = event_action_map.get(event_type, "unknown")

        return normalized

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        try:
            sub = self._client.subscription.fetch(subscription_id)
            return {
                "subscription_id": sub.id,
                "status": sub.status,
                "plan": sub.plan_id,
                "current_period_start": None,
                "current_period_end": None,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "provider": "razorpay",
            }
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------


def get_payment_adapter() -> PaymentAdapter:
    """Return the configured payment adapter."""
    provider = os.getenv("PAYMENT_PROVIDER", "stripe").lower()

    if provider == "razorpay":
        return RazorpayAdapter()
    return StripeAdapter()


# Global adapter instance
payment_adapter = get_payment_adapter()
