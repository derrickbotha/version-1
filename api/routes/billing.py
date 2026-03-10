from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.billing import OrderCreate, OrderOut, CheckoutSession, SubscriptionOut
from ..services.auth_service import get_current_user
from ..services.billing_service import (
    create_stripe_checkout, create_paypal_order, handle_stripe_webhook,
    calculate_order_amount,
)
from ..models.billing import Order, Subscription
from ..config import settings
import stripe

router = APIRouter(prefix="/billing", tags=["billing"])

def current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    try:
        return get_current_user(token, db)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/checkout/stripe", response_model=CheckoutSession)
def stripe_checkout(body: OrderCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    plan = user.subscription.plan if user.subscription else "professional"
    try:
        result = create_stripe_checkout(
            db=db,
            user_id=str(user.id),
            assignment_id=str(body.assignment_id) if body.assignment_id else None,
            plan=plan,
            review_type=body.review_type,
            success_url="https://app.scholarassistant.ai/billing/success",
            cancel_url="https://app.scholarassistant.ai/billing/cancel",
        )
        return CheckoutSession(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/checkout/paypal", response_model=CheckoutSession)
def paypal_checkout(body: OrderCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    plan = user.subscription.plan if user.subscription else "professional"
    try:
        result = create_paypal_order(
            db=db,
            user_id=str(user.id),
            assignment_id=str(body.assignment_id) if body.assignment_id else None,
            plan=plan,
            review_type=body.review_type,
        )
        return CheckoutSession(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        handle_stripe_webhook(db, payload, sig_header)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}

@router.get("/orders", response_model=list)
def list_orders(user=Depends(current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    return [{"id": str(o.id), "amount": float(o.amount), "status": o.status,
              "description": o.description, "created_at": o.created_at.isoformat()} for o in orders]

@router.get("/pricing")
def pricing():
    return {
        "plans": [
            {"id": "starter",      "name": "Starter",       "price": 199, "level": "High School",    "features": ["12-15 assignments", "800-1200 words", "Low research intensity"]},
            {"id": "professional", "name": "Professional",  "price": 299, "level": "Undergraduate",  "features": ["16-20 assignments", "1500-3000 words", "Medium/High research", "Knowledge graph access"]},
            {"id": "agentic_pro",  "name": "Agentic Pro",   "price": 399, "level": "Postgraduate",   "features": ["4-8 assignments", "5000-10000 words", "Very High research", "50+ sources per paper", "Human-in-loop review"]},
            {"id": "enterprise",   "name": "Enterprise",    "price": None,"level": "PhD / Research", "features": ["1-2 chapters", "10000+ words", "Extreme research depth", "Custom pricing", "Dedicated researcher"]},
        ],
        "addons": [
            {"id": "professor_review", "name": "Professor Review", "price": 20, "description": "A qualified professor reviews and annotates your assignment before delivery"},
        ]
    }
