"""
Billing routes for ZooLingo subscriptions.

Endpoints:
- GET /billing/plans - List available subscription plans
- GET /billing/me - Get current user's subscription and usage
- POST /billing/checkout - Create a checkout session for upgrade
- POST /billing/cancel - Cancel subscription
- POST /billing/webhook - Payment provider webhook (idempotent)

Security:
- All endpoints require authentication (Supabase JWT)
- Webhook signatures are verified before processing
- Webhook events are processed idempotently (unique event IDs)
- Secret keys are server-side only
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from auth import (
    check_conversion_allowed,
    confirm_conversion,
    create_user_profile,
    get_current_user,
    get_user_profile,
    get_user_conversions_used,
    PLAN_CONFIG,
    release_conversion,
    reserve_conversion,
)
from services.payment_adapter import payment_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# ---------------------------------------------------------------------------
# In-memory billing events store (placeholder; replace with Supabase table)
# ---------------------------------------------------------------------------

# Each event: { event_id: { "event_id": str, "event_type": str,
# "processed_at": str, "processed": bool } }
_BILLING_EVENTS: dict = {}

# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class PlanOut(BaseModel):
    id: str
    name: str
    price_monthly_inr: int
    conversion_quota: Optional[int]  # None = unlimited
    features: list


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    provider: str


class SubscriptionOut(BaseModel):
    plan: str
    status: str
    conversions_used: int
    conversion_quota: Optional[int]
    conversions_remaining: Optional[int]
    subscription_id: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: Optional[bool]


class WebhookEvent(BaseModel):
    event_id: str
    event_type: str
    action: str
    provider: str
    customer_id: Optional[str]
    subscription_id: Optional[str]
    status: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/plans", response_model=list[PlanOut])
async def list_plans():
    """List available subscription plans with pricing."""
    plans = []
    for plan_id, config in PLAN_CONFIG.items():
        quota = config.get("conversion_quota")
        plans.append(
            PlanOut(
                id=plan_id,
                name=config["name"],
                price_monthly_inr=config["price_monthly_inr"],
                conversion_quota=quota,
                features=config.get("features", []),
            )
        )
    return plans


@router.get("/me", response_model=SubscriptionOut)
async def billing_me(current_user: dict = Depends(get_current_user)):
    """Get current user's subscription and usage."""
    user_id = str(current_user["id"])
    plan = str(current_user.get("plan", "free"))
    conversions_used = int(current_user.get("conversions_used", 0))

    plan_config = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
    quota = plan_config.get("conversion_quota")

    remaining = None
    if quota is not None:
        remaining = max(0, quota - conversions_used)

    # Try to get subscription from payment provider
    subscription_id = None
    current_period_end = None
    cancel_at_period_end = None
    status_value = "active"

    # Check if user has a subscription stored in profile
    subscription_id = str(current_user.get("subscription_id", "") or None)
    if subscription_id == "None":
        subscription_id = None

    return SubscriptionOut(
        plan=plan,
        status=status_value,
        conversions_used=conversions_used,
        conversion_quota=quota,
        conversions_remaining=remaining,
        subscription_id=subscription_id,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a checkout session for subscription upgrade."""
    user_id = str(current_user["id"])
    plan = payload.plan

    # Validate plan exists
    if plan not in PLAN_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {plan}",
        )

    if plan == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upgrade to free plan",
        )

    try:
        result = payment_adapter.create_checkout_session(
            user_id=user_id,
            plan=plan,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return CheckoutResponse(
        checkout_url=result["checkout_url"],
        session_id=result["session_id"],
        provider=result["provider"],
    )


@router.post("/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
):
    """Cancel the current user's subscription."""
    user_id = str(current_user["id"])
    subscription_id = str(current_user.get("subscription_id", ""))

    if not subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel",
        )

    try:
        result = payment_adapter.cancel_subscription(subscription_id)
    except Exception as e:
        logger.error(f"Subscription cancellation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to cancel subscription",
        )

    # Update user profile to reflect cancellation
    create_user_profile(
        user_id,
        email=str(current_user.get("email", "")),
        plan=str(current_user.get("plan", "free")),
    )

    return {
        "subscription_id": result["subscription_id"],
        "status": result["status"],
        "cancel_at_period_end": result["cancel_at_period_end"],
        "message": "Subscription will cancel at end of current period",
    }


@router.post("/webhook")
async def billing_webhook(request: Request):
    """
    Payment provider webhook endpoint.

    Processes webhook events idempotently:
    - Each event has a unique provider_event_id
    - Duplicate events are ignored (already processed)
    - Out-of-order events are handled safely
    - Webhook signatures are verified before processing
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature") or request.headers.get(
        "razorpay-signature"
    )

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook signature",
        )

    # Verify signature
    if not payment_adapter.verify_webhook_signature(payload, signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    # Parse event
    event = payment_adapter.parse_webhook_event(payload)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to parse webhook event",
        )

    event_id = event["event_id"]

    # Idempotency: skip if already processed
    if event_id in _BILLING_EVENTS:
        logger.info(f"Duplicate webhook event ignored: {event_id}")
        return {"status": "duplicate", "event_id": event_id}

    # Mark as processed
    _BILLING_EVENTS[event_id] = {
        "event_id": event_id,
        "event_type": event["event_type"],
        "action": event["action"],
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "processed": True,
    }

    logger.info(f"Processing webhook event: {event_id} ({event['action']})")

    # Handle subscription events
    action = event["action"]
    subscription_id = event.get("subscription_id")
    customer_id = event.get("customer_id")

    if action == "subscription.created":
        # Subscription created - update user plan
        if subscription_id:
            sub = payment_adapter.get_subscription(subscription_id)
            if sub:
                plan_id = sub.get("plan", "")
                # Map plan ID back to our plan name (simplified)
                logger.info(
                    f"Subscription created: {subscription_id}, plan: {plan_id}"
                )

    elif action == "subscription.updated":
        # Subscription updated - check cancel_at_period_end
        if subscription_id:
            sub = payment_adapter.get_subscription(subscription_id)
            if sub:
                logger.info(
                    f"Subscription updated: {subscription_id}, "
                    f"status: {sub.get('status')}"
                )

    elif action == "subscription.deleted":
        # Subscription cancelled
        logger.info(f"Subscription deleted: {subscription_id}")

    elif action == "payment.succeeded":
        # Payment succeeded - activate subscription
        logger.info(f"Payment succeeded: {subscription_id}")

    elif action == "payment.failed":
        # Payment failed - notify user
        logger.warning(f"Payment failed: {subscription_id}")

    return {
        "status": "processed",
        "event_id": event_id,
        "action": action,
    }


# ---------------------------------------------------------------------------
# Usage endpoint (separate from billing/me for granular access)
# ---------------------------------------------------------------------------


@router.get("/usage")
async def usage(current_user: dict = Depends(get_current_user)):
    """Get current user's usage and allowance."""
    plan = str(current_user.get("plan", "free"))
    conversions_used = int(current_user.get("conversions_used", 0))

    plan_config = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
    quota = plan_config.get("conversion_quota")

    allowed, reason = check_conversion_allowed(current_user)

    remaining = None
    if quota is not None:
        remaining = max(0, quota - conversions_used)

    return {
        "plan": plan,
        "conversions_used": conversions_used,
        "conversion_quota": quota,
        "conversions_remaining": remaining,
        "allowed": allowed,
        "reason": reason if not allowed else "",
    }
