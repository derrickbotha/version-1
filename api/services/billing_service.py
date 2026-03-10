import stripe
import httpx
from sqlalchemy.orm import Session
from ..models.billing import Order, Subscription, OrderStatus, PlanEnum
from ..models.user import Wallet, WalletTransaction
from ..config import settings
from decimal import Decimal
import uuid

stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_STRIPE_PRICES = {
    # Map plan → Stripe Price ID (set in env or dashboard)
    "starter":      "price_starter_monthly",
    "professional": "price_professional_monthly",
    "agentic_pro":  "price_agentic_pro_monthly",
}

def calculate_order_amount(plan: str, review_type: str) -> float:
    base = settings.PLAN_PRICES.get(plan, 299.0)
    professor_fee = settings.PROFESSOR_REVIEW_COST_USD if review_type == "agent_professor" else 0.0
    return round(base + professor_fee, 2)

def create_stripe_checkout(db: Session, user_id: str, assignment_id: str,
                            plan: str, review_type: str, success_url: str,
                            cancel_url: str) -> dict:
    amount = calculate_order_amount(plan, review_type)
    prof_fee = settings.PROFESSOR_REVIEW_COST_USD if review_type == "agent_professor" else 0.0

    order = Order(
        user_id=user_id,
        assignment_id=assignment_id,
        amount=Decimal(str(amount)),
        description=f"ASA {plan} plan + {'professor review' if prof_fee else 'agent review'}",
        review_type=review_type,
        professor_fee=Decimal(str(prof_fee)),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"ASA {plan.title()} — {review_type.replace('_', ' ').title()}"},
                "unit_amount": int(amount * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url + f"?order_id={order.id}",
        cancel_url=cancel_url,
        metadata={"order_id": str(order.id), "user_id": str(user_id)},
    )
    order.stripe_pi_id = session.payment_intent
    db.commit()
    return {"checkout_url": session.url, "order_id": str(order.id), "amount": amount}

def handle_stripe_webhook(db: Session, payload: bytes, sig_header: str):
    event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"].get("order_id")
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = OrderStatus.paid
            from datetime import datetime
            order.paid_at = datetime.utcnow()
            db.commit()

def get_paypal_token() -> str:
    resp = httpx.post(
        f"{settings.PAYPAL_BASE_URL}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
    )
    return resp.json()["access_token"]

def create_paypal_order(db: Session, user_id: str, assignment_id: str,
                         plan: str, review_type: str) -> dict:
    amount = calculate_order_amount(plan, review_type)
    prof_fee = settings.PROFESSOR_REVIEW_COST_USD if review_type == "agent_professor" else 0.0
    token = get_paypal_token()

    order_db = Order(
        user_id=user_id,
        assignment_id=assignment_id,
        amount=Decimal(str(amount)),
        review_type=review_type,
        professor_fee=Decimal(str(prof_fee)),
        description=f"ASA {plan}",
    )
    db.add(order_db)
    db.commit()

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": str(amount)},
            "description": f"ASA {plan}",
        }],
        "application_context": {
            "return_url": "https://app.scholarassistant.ai/billing/success",
            "cancel_url": "https://app.scholarassistant.ai/billing/cancel",
        },
    }
    resp = httpx.post(
        f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    pp_order = resp.json()
    order_db.paypal_order_id = pp_order["id"]
    db.commit()

    approve_url = next(l["href"] for l in pp_order["links"] if l["rel"] == "approve")
    return {"checkout_url": approve_url, "order_id": str(order_db.id), "amount": amount}
