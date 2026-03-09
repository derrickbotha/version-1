
import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.payment_schema import (
    EscrowDepositRequest,
    PaymentMethodResponse,
    PaymentRefundRequest,
    PaymentReleaseRequest,
    PaymentResponse,
    PayoutRequestSchema,
    SetDefaultPaymentMethodRequest,
    StripeDepositRequest,
    StripeDepositResponse,
    WalletDepositRequest,
    WalletResponse,
    WriterPayoutListResponse,
    WriterPayoutResponse,
    WalletTransactionListResponse,
    WalletTransactionResponse,
)
from app.services import payment_service
from app.services import stripe_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/wallet/deposit",
    response_model=dict,
    status_code=201,
    summary="Deposit funds into own wallet (direct / test mode)",
)
def deposit_to_wallet(
    body: WalletDepositRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # Idempotency (spec §12)
    if idempotency_key:
        cached = payment_service.check_idempotency(
            db, idempotency_key, current_user.id, "/payments/wallet/deposit"
        )
        if cached:
            return {"status": "success", "data": cached}

    wallet = payment_service.deposit_to_wallet(
        db=db,
        user_id=current_user.id,
        amount=body.amount,
    )
    result = WalletResponse.model_validate(wallet).model_dump()
    if idempotency_key:
        payment_service.store_idempotency(
            db, idempotency_key, current_user.id, "/payments/wallet/deposit", result
        )
    return {"status": "success", "data": result}


@router.post(
    "/wallet/stripe-intent",
    response_model=dict,
    status_code=201,
    summary="Create Stripe PaymentIntent for wallet top-up",
)
def create_stripe_deposit_intent(
    body: StripeDepositRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = stripe_service.create_payment_intent(
        amount=body.amount,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
    )
    return {"status": "success", "data": result}


@router.get(
    "/wallet",
    response_model=dict,
    summary="Get own wallet balance",
)
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    wallet = payment_service.get_wallet(db=db, user_id=current_user.id)
    return {
        "status": "success",
        "data": WalletResponse.model_validate(wallet).model_dump(),
    }


@router.get(
    "/wallet/transactions",
    response_model=dict,
    summary="Paginated wallet transaction history",
)
def get_wallet_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = payment_service.get_wallet_transactions(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    response = WalletTransactionListResponse(
        items=[WalletTransactionResponse.model_validate(tx) for tx in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return {"status": "success", "data": response.model_dump()}


@router.post(
    "/escrow",
    response_model=dict,
    status_code=201,
    summary="Create escrow for a contract (student only)",
)
def create_escrow(
    body: EscrowDepositRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    payment = payment_service.create_escrow(
        db=db,
        contract_id=body.contract_id,
        student_id=current_user.id,
        data=body,
    )
    return {
        "status": "success",
        "data": PaymentResponse.model_validate(payment).model_dump(),
    }


@router.post(
    "/release",
    response_model=dict,
    summary="Release escrowed payment to researcher (student only)",
)
def release_payment(
    body: PaymentReleaseRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    payment = payment_service.release_payment(
        db=db,
        contract_id=body.contract_id,
        student_id=current_user.id,
    )
    return {
        "status": "success",
        "data": PaymentResponse.model_validate(payment).model_dump(),
    }


@router.post(
    "/refund",
    response_model=dict,
    summary="Refund escrowed payment to student (student or admin)",
)
def refund_payment(
    body: PaymentRefundRequest,
    current_user: User = Depends(require_role("student", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    payment = payment_service.refund_payment(
        db=db,
        contract_id=body.contract_id,
        requester_id=current_user.id,
        requester_role=current_user.role,
        reason=body.reason,
    )
    return {
        "status": "success",
        "data": PaymentResponse.model_validate(payment).model_dump(),
    }


@router.get(
    "/contract/{contract_id}",
    response_model=dict,
    summary="Get payment status for a contract (participant or admin)",
)
def get_payment_by_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    payment = payment_service.get_payment_by_contract(
        db=db,
        contract_id=contract_id,
        requester_id=current_user.id,
        requester_role=current_user.role,
    )
    return {
        "status": "success",
        "data": PaymentResponse.model_validate(payment).model_dump(),
    }


# ---------------------------------------------------------------------------
# Payment methods (spec §4.7)
# ---------------------------------------------------------------------------

@router.get(
    "/methods",
    response_model=dict,
    summary="List saved payment methods",
)
def list_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    methods = payment_service.get_payment_methods(db, current_user.id)
    return {
        "status": "success",
        "data": [PaymentMethodResponse.model_validate(m).model_dump() for m in methods],
    }


@router.delete(
    "/methods/{pm_id}",
    response_model=dict,
    summary="Delete a saved payment method",
)
def delete_payment_method(
    pm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    payment_service.delete_payment_method(db, pm_id, current_user.id)
    return {"status": "success", "data": {"message": "Payment method removed"}}


@router.post(
    "/methods/default",
    response_model=dict,
    summary="Set default payment method",
)
def set_default_payment_method(
    body: SetDefaultPaymentMethodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    pm = payment_service.set_default_payment_method(db, body.payment_method_id, current_user.id)
    return {"status": "success", "data": PaymentMethodResponse.model_validate(pm).model_dump()}


@router.post(
    "/methods/stripe/save",
    response_model=dict,
    status_code=201,
    summary="Save a Stripe PaymentMethod after successful payment",
)
def save_stripe_method(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    pm_id: str = body.get("payment_method_id", "")
    if not pm_id:
        from fastapi import HTTPException, status as http_status  # noqa: PLC0415
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="payment_method_id required")
    pm = stripe_service.save_payment_method(db, current_user.id, pm_id)
    return {"status": "success", "data": PaymentMethodResponse.model_validate(pm).model_dump()}


# ---------------------------------------------------------------------------
# Writer payout (spec §4.10, §10)
# ---------------------------------------------------------------------------

@router.post(
    "/payout",
    response_model=dict,
    status_code=201,
    summary="Request a payout (researcher only)",
)
def request_payout(
    body: PayoutRequestSchema,
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    payout = payment_service.request_payout(db, current_user.id, body)
    return {"status": "success", "data": WriterPayoutResponse.model_validate(payout).model_dump()}


@router.get(
    "/payouts",
    response_model=dict,
    summary="List own payout history (researcher only)",
)
def list_payouts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    items, total = payment_service.get_payouts(db, current_user.id, page, page_size)
    response = WriterPayoutListResponse(
        items=[WriterPayoutResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return {"status": "success", "data": response.model_dump()}
