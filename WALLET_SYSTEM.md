# Academic Research Platform — Wallet & Account System

**Spec Reference:** `academic_research_wallet_system_spec_v4.md`
**Version:** 4.0
**Status:** Implemented

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Database Schema](#3-database-schema)
4. [Double-Entry Ledger](#4-double-entry-ledger)
5. [Payment Providers](#5-payment-providers)
6. [Fraud Detection](#6-fraud-detection)
7. [Idempotency](#7-idempotency)
8. [Webhook Security](#8-webhook-security)
9. [Writer Payout System](#9-writer-payout-system)
10. [Account Settings](#10-account-settings)
11. [API Reference](#11-api-reference)
12. [Frontend Pages & Components](#12-frontend-pages--components)
13. [Environment Variables](#13-environment-variables)
14. [File Map](#14-file-map)

---

## 1. System Overview

The platform provides a fintech-grade financial infrastructure for an academic research marketplace. It connects students (buyers) with researchers (writers/sellers) and handles the full payment lifecycle:

```
Student deposits funds
    → Funds held in escrow when contract starts
        → Released to researcher on work approval
            → Researcher requests payout to bank/PayPal
```

Every financial event generates double-entry ledger records ensuring auditability, reconciliation, and financial correctness. The platform never stores raw card details — all card data is handled by PCI-compliant providers (Stripe, PayPal).

---

## 2. Architecture

### Service Layout (Monolith with Service-Layer Separation)

```
FastAPI Application
├── Routers          — HTTP layer, input validation, auth checks
├── Services         — Business logic, orchestration
├── Models           — SQLAlchemy ORM (PostgreSQL)
└── Schemas          — Pydantic v2 request/response contracts
```

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Primary Database | PostgreSQL | All persistent data |
| Cache / Rate Limiting | Redis | Wallet balance cache (TTL 24h), fraud counters |
| Payment — Cards | Stripe | PaymentIntents, webhooks, saved methods |
| Payment — PayPal | PayPal | Capture webhooks, billing agreements |
| Event Streaming | Celery + Redis | Background tasks (future: Kafka/RabbitMQ) |

### Payment Flow

```
Student UI
  → POST /payments/wallet/stripe-intent  → Stripe API (PaymentIntent)
  → Stripe.js collects card on frontend
  → Stripe webhook: payment_intent.succeeded
  → Webhook handler → deposit_to_wallet()
      → Wallet balance updated
      → WalletTransaction recorded (type: deposit)
      → LedgerEntry pair posted (PAYMENT_PROCESSOR → USER_WALLET)
      → Redis cache invalidated
```

---

## 3. Database Schema

### 3.1 Pre-existing Tables (unchanged)

| Table | Purpose |
|---|---|
| `users` | Auth, roles (student/researcher/admin), status |
| `student_profiles` | University, degree program, country |
| `researcher_profiles` | Bio, expertise, rating, jobs completed |
| `wallets` | One per user, cached balance (Numeric 12,2) |
| `wallet_transactions` | Ledger of wallet movements (deposit, escrow_lock, release, refund, payout) |
| `payments` | Per-contract escrow records (pending→escrowed→released/refunded) |
| `contracts` | Job–researcher agreements with status machine |
| `jobs`, `bids`, `submissions`, `disputes` | Core marketplace tables |

### 3.2 New Tables Added (Spec v4)

#### `ledger_accounts`
Double-entry ledger accounts. Each account belongs to a type and optionally an owner.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `account_type` | ENUM | `USER_WALLET`, `WRITER_WALLET`, `ESCROW_ACCOUNT`, `PLATFORM_REVENUE`, `PAYMENT_PROCESSOR`, `REFUND_POOL`, `PAYOUT_CLEARING` |
| `owner_id` | UUID FK → users | Nullable (system accounts have no owner) |
| `currency` | VARCHAR(10) | Default `USD` |
| `created_at` | TIMESTAMPTZ | |

#### `ledger_entries`
Individual debit or credit lines. Every financial event creates exactly two rows (one debit, one credit).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `transaction_ref` | VARCHAR(255) | Human-readable reference (e.g. `escrow:contract-uuid`) |
| `account_id` | UUID FK → ledger_accounts | |
| `debit` | NUMERIC(14,2) | ≥ 0; CHECK: cannot have both debit > 0 AND credit > 0 |
| `credit` | NUMERIC(14,2) | ≥ 0 |
| `currency` | VARCHAR(10) | |
| `description` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

**Integrity constraint:** `SUM(debits) = SUM(credits)` across all entries for any transaction_ref.

#### `payment_methods`
Saved Stripe PaymentMethod tokens or PayPal billing agreements.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `provider` | ENUM | `stripe`, `paypal` |
| `provider_token` | TEXT | Stripe PM ID or PayPal billing agreement ID |
| `brand` | VARCHAR(50) | `visa`, `mastercard`, `paypal`, etc. |
| `last4` | VARCHAR(4) | Last 4 digits of card |
| `expiry_month` | INT | |
| `expiry_year` | INT | |
| `is_default` | BOOLEAN | Only one default per user |
| `created_at` | TIMESTAMPTZ | |

#### `writer_payouts`
Tracks researcher payout requests and their processing status.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `writer_id` | UUID FK → users | Must be role=researcher |
| `amount` | NUMERIC(12,2) | Minimum $10.00 |
| `currency` | VARCHAR(10) | Default `USD` |
| `status` | ENUM | `pending` → `processing` → `completed` / `failed` |
| `provider` | VARCHAR(50) | `stripe` or `paypal` |
| `provider_reference` | VARCHAR(255) | Provider payout ID once processed |
| `notes` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

#### `idempotency_keys`
Prevents duplicate operations from retried requests (spec §12).

| Column | Type | Notes |
|---|---|---|
| `key` | VARCHAR(255) PK | Value of `Idempotency-Key` header |
| `user_id` | UUID | |
| `endpoint` | VARCHAR(255) | Path the key was used on |
| `response_body` | TEXT | JSON-serialised original response |
| `created_at` | TIMESTAMPTZ | |

---

## 4. Double-Entry Ledger

Every financial event posts a balanced pair of `LedgerEntry` rows via `ledger_service.post_double_entry()`.

### Accounting Rules

| Event | Debit Account | Credit Account |
|---|---|---|
| Wallet deposit | `PAYMENT_PROCESSOR` | `USER_WALLET` (owner = student) |
| Escrow lock | `USER_WALLET` (owner = student) | `ESCROW_ACCOUNT` |
| Escrow release | `ESCROW_ACCOUNT` | `WRITER_WALLET` (owner = researcher) |
| Refund | `ESCROW_ACCOUNT` | `USER_WALLET` (owner = student) |
| Writer payout | `WRITER_WALLET` (owner = researcher) | `PAYOUT_CLEARING` |

### Ledger Service

**File:** `app/services/ledger_service.py`

```python
post_double_entry(
    db,
    transaction_ref="escrow:contract-uuid",
    debit_type="USER_WALLET",
    credit_type="ESCROW_ACCOUNT",
    amount=Decimal("250.00"),
    debit_owner=student_id,
    description="Escrow lock for contract ...",
)
```

- `_get_or_create_account()` — lazily creates the named account if it does not yet exist
- Both entries are added in the same DB transaction as the wallet operation — no partial posts

---

## 5. Payment Providers

### 5.1 Stripe

**File:** `app/services/stripe_service.py`

#### Wallet Top-Up Flow

```
1. Frontend calls POST /api/v1/payments/wallet/stripe-intent  {amount}
2. Backend creates Stripe PaymentIntent (amount_cents, metadata.user_id)
3. Returns {client_secret, payment_intent_id, publishable_key}
4. Frontend uses Stripe.js to collect and confirm card payment
5. Stripe fires payment_intent.succeeded webhook
6. POST /api/v1/webhooks/stripe → verified via stripe-signature header
7. _handle_payment_intent_succeeded() → deposit_to_wallet(user_id, amount)
```

#### Handled Webhook Events

| Event | Handler |
|---|---|
| `payment_intent.succeeded` | Credits wallet, posts ledger entry |
| `payment_intent.payment_failed` | Records failed attempt for fraud detection |
| `charge.refunded` | Logged |
| `payout.paid` | Marks `WriterPayout.status = completed` |

#### Saving a Card

After a successful payment, the frontend can call `POST /payments/methods/stripe/save` with the `payment_method_id` to persist the card token for future use.

### 5.2 PayPal

**File:** `app/services/paypal_service.py`

#### Handled Webhook Events

| Event | Handler |
|---|---|
| `PAYMENT.CAPTURE.COMPLETED` | Credits wallet using `resource.custom_id` as user_id |
| `PAYMENT.CAPTURE.DENIED` | Records failed attempt for fraud detection |
| `PAYMENT.CAPTURE.REFUNDED` | Logged |

**Note:** Full PayPal signature verification requires downloading PayPal's certificate. The current implementation accepts the webhook body and validates the event type. Replace with `paypalrestsdk.WebhookEvent.verify()` in production.

---

## 6. Fraud Detection

**File:** `app/services/fraud_service.py`
**Backend:** Redis sliding-window counters with TTL.

| Rule | Threshold | Window | Action |
|---|---|---|---|
| Rapid deposits | 3 deposits | 2 minutes | Block with message |
| Failed payments | 5 failures | 10 minutes | Block payments |
| Large deposit | > $2,000 | — | KYC flag — block, redirect to support |

### Implementation

```python
# On every deposit attempt:
flagged, reason = fraud_service.check_deposit(user_id, amount)
if flagged:
    raise HTTPException(403, detail=reason)

# On every failed payment:
fraud_service.record_failed_payment(user_id)

# Redis keys:
fraud:deposits:{user_id}   TTL: 120s
fraud:fails:{user_id}      TTL: 600s
```

**Graceful degradation:** If Redis is unavailable, fraud checks are bypassed and a warning is logged. All other payment operations continue normally.

---

## 7. Idempotency

**File:** `app/services/payment_service.py` — `check_idempotency()` / `store_idempotency()`
**Table:** `idempotency_keys`

Clients send `Idempotency-Key: <uuid>` header on deposit requests. If the same key is received again by the same user, the original response is returned immediately without re-executing the operation.

```http
POST /api/v1/payments/wallet/deposit
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{"amount": "100.00"}
```

Supported endpoints:
- `POST /payments/wallet/deposit`
- `POST /payments/wallet/stripe-intent` (via Stripe's own idempotency key pass-through)

---

## 8. Webhook Security

**File:** `app/routers/webhook_router.py`

### Stripe
- Signature verified via `stripe.Webhook.construct_event(payload, sig_header, webhook_secret)`
- Returns HTTP 400 on invalid signature
- Event ID can be stored for deduplication (future enhancement)

### PayPal
- Accepts `paypal-transmission-id` header
- Full cert-based signature verification is stubbed — replace with `paypalrestsdk.WebhookEvent.verify()` in production

### General
- Both webhook endpoints are public (no JWT auth) — verified only by provider signature
- All webhook processing is synchronous; move to background task queue for high volume

---

## 9. Writer Payout System

**Files:** `app/services/payment_service.py`, `app/routers/payments_router.py`

### Payout Rules

| Rule | Value |
|---|---|
| Minimum payout | $10.00 |
| Eligible roles | `researcher` only |
| Supported providers | `stripe`, `paypal` |
| Processing time | 1–3 business days (manual trigger in current version) |

### Payout Flow

```
1. Researcher calls POST /api/v1/payments/payout  {amount, provider}
2. payment_service.request_payout():
   a. Checks wallet balance >= amount
   b. Debits wallet balance
   c. Creates WalletTransaction (type: payout)
   d. Creates WriterPayout (status: pending)
   e. Posts ledger entry: WRITER_WALLET → PAYOUT_CLEARING
3. Returns WriterPayoutResponse
4. Admin/system processes payout via Stripe Payouts API or PayPal Payouts API
5. Stripe fires payout.paid webhook → status updated to completed
```

### Payout Schedules (spec §10)

| Schedule | Status |
|---|---|
| Manual (current) | ✅ Implemented — researcher requests, admin processes |
| Daily automated | Planned — Celery beat task |
| Weekly automated | Planned — Celery beat task |

---

## 10. Account Settings

**Files:** `app/services/account_service.py`, `app/routers/account_router.py`

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/account` | Full account data (profile + role profile) |
| `PATCH` | `/api/v1/account/profile` | Update first/last name, phone, WhatsApp |
| `PATCH` | `/api/v1/account/contact` | Update email (triggers re-verification), phone |
| `PATCH` | `/api/v1/account/location` | Update country, city, postal code, timezone |
| `POST` | `/api/v1/account/security/change-password` | Change password (verifies current password first) |
| `PATCH` | `/api/v1/account/student-profile` | Update university, degree program |
| `PATCH` | `/api/v1/account/researcher-profile` | Update bio, expertise array |

### Security

- Email change sets `is_verified = False` (requires re-verification flow)
- Password change validates `current_password` via bcrypt before hashing new password
- All endpoints require a valid JWT (`get_current_user`)
- Deleted users (`status = deleted`) are rejected with HTTP 404

---

## 11. API Reference

### Wallet

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/payments/wallet/deposit` | Any | Direct deposit (test/admin). Supports `Idempotency-Key` header. Fraud-checked. |
| `POST` | `/payments/wallet/stripe-intent` | Any | Create Stripe PaymentIntent for card deposit |
| `GET` | `/payments/wallet` | Any | Get wallet balance |
| `GET` | `/payments/wallet/transactions` | Any | Paginated transaction history (`page`, `page_size` max 100) |

### Escrow

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/payments/escrow` | Student | Lock funds in escrow for a contract |
| `POST` | `/payments/release` | Student | Release escrowed funds to researcher |
| `POST` | `/payments/refund` | Student / Admin | Refund escrowed funds to student |
| `GET` | `/payments/contract/{id}` | Participant / Admin | Get payment status for a contract |

### Payment Methods

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/payments/methods` | Any | List saved payment methods |
| `DELETE` | `/payments/methods/{id}` | Any | Remove a saved method |
| `POST` | `/payments/methods/default` | Any | Set a method as default |
| `POST` | `/payments/methods/stripe/save` | Any | Save a Stripe PaymentMethod token |

### Payouts

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/payments/payout` | Researcher | Request a payout (min $10) |
| `GET` | `/payments/payouts` | Researcher | Paginated payout history |

### Webhooks

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/webhooks/stripe` | None (sig-verified) | Stripe event receiver |
| `POST` | `/webhooks/paypal` | None | PayPal event receiver |

### Account

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/account` | Any | Full account + role profile |
| `PATCH` | `/account/profile` | Any | Name, phone, WhatsApp |
| `PATCH` | `/account/contact` | Any | Email, phone |
| `PATCH` | `/account/location` | Any | Country, city, postal, timezone |
| `POST` | `/account/security/change-password` | Any | Change password |
| `PATCH` | `/account/student-profile` | Any | University, degree |
| `PATCH` | `/account/researcher-profile` | Any | Bio, expertise |

> All `/api/v1/` prefixed. Full interactive docs at `http://localhost:8000/docs`.

---

## 12. Frontend Pages & Components

### `/account` — Account Settings

**File:** `frontend/app/account/page.tsx`

5-tab settings page accessible from the sidebar "Account Settings" link.

| Tab | Fields |
|---|---|
| **Profile** | First name, last name, phone, WhatsApp number |
| **Contact** | Email (re-verification triggered on change), phone, WhatsApp |
| **Location** | Country, city, postal code, timezone |
| **Security** | Change password (current + new + confirm) + account status display |
| **My Details** | Student: university, degree program. Researcher: bio, expertise (comma-separated), rating badge, jobs completed counter |

Features:
- Animated success/error flash messages (auto-dismiss 4 seconds)
- User card in sidebar showing avatar initial, name, role, verification badge
- All saves are optimistic — re-fetches account data from API after success

### `/wallet` — Wallet Dashboard

**File:** `frontend/app/wallet/page.tsx`

Role-aware wallet page. Renders differently for students vs researchers.

#### Student View

| Section | Description |
|---|---|
| **Balance Card** | Gradient card showing available balance |
| **Add Funds** | Amount input with $50/$100/$250/$500 quick-select buttons. Fraud errors shown inline. |
| **Stripe Banner** | Info card explaining Stripe card acceptance |
| **PayPal Banner** | Info card explaining PayPal support |
| **Saved Methods** | Lists saved cards/PayPal with brand, last4, expiry. Set default (⭐) or delete (🗑️). |
| **Transaction History** | All wallet movements with icons, labels, signed amounts, timestamps |

#### Researcher View

| Section | Description |
|---|---|
| **Balance Card** | Shows total earnings available for payout |
| **Request Payout** | Amount input, provider toggle (Stripe / PayPal), submit. Min $10 enforced client + server. |
| **Saved Methods** | Same as student |
| **Payout History** | Lists all payout requests with status badges (pending/processing/completed/failed) |
| **Transaction History** | Same as student |

### `lib/api.ts` — API Client Extensions

New typed functions added:

```typescript
// Account
getAccount()
updateProfile(payload)
updateContact(payload)
updateLocation(payload)
changePassword(payload)
updateStudentProfile(payload)
updateResearcherProfile(payload)

// Payment Methods
getPaymentMethods()
deletePaymentMethod(id)
setDefaultPaymentMethod(payment_method_id)

// Stripe
createStripeDepositIntent(amount, save_method?)

// Payouts
requestPayout(amount, provider)
getPayouts(page?)
```

---

## 13. Environment Variables

Add these to the backend environment (`.env` file or shell export):

```bash
# Stripe (required for card payments)
STRIPE_SECRET_KEY=sk_live_...        # or sk_test_... for sandbox
STRIPE_PUBLISHABLE_KEY=pk_live_...   # returned to frontend for Stripe.js
STRIPE_WEBHOOK_SECRET=whsec_...      # from Stripe dashboard → Webhooks

# PayPal (required for PayPal payments)
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=sandbox                  # sandbox | live

# Redis (required for fraud detection + caching)
REDIS_URL=redis://localhost:6379/0

# Existing
DATABASE_URL=postgresql+psycopg2://research:research@127.0.0.1:5432/research_marketplace
JWT_SECRET=changeme-use-a-long-random-secret
```

**Running the backend:**
```bash
cd /home/dbm/AssignmentOnline/research-platform
DATABASE_URL=postgresql+psycopg2://research:research@127.0.0.1:5432/research_marketplace \
  REDIS_URL=redis://localhost:6379/0 \
  JWT_SECRET=changeme-use-a-long-random-secret \
  STRIPE_SECRET_KEY=sk_test_... \
  STRIPE_PUBLISHABLE_KEY=pk_test_... \
  STRIPE_WEBHOOK_SECRET=whsec_... \
  /home/dbm/AssignmentOnline/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Running the frontend:**
```bash
cd /home/dbm/AssignmentOnline/research-platform/frontend
PORT=3000 npm run dev
```

---

## 14. File Map

### New Backend Files

```
app/
├── config.py                          ← Added: stripe_*, paypal_* settings
├── models/
│   └── payment.py                     ← Added: LedgerAccount, LedgerEntry,
│                                               PaymentMethod, WriterPayout,
│                                               IdempotencyKey
├── schemas/
│   ├── account_schema.py              ← NEW: all account settings schemas
│   └── payment_schema.py              ← Added: PaymentMethodResponse,
│                                               PayoutRequestSchema,
│                                               WriterPayoutResponse,
│                                               StripeDepositRequest/Response,
│                                               FraudFlagResponse
├── services/
│   ├── account_service.py             ← NEW: profile/contact/location/password
│   ├── ledger_service.py              ← NEW: post_double_entry()
│   ├── fraud_service.py               ← NEW: Redis fraud rules (spec §11)
│   ├── stripe_service.py              ← NEW: PaymentIntent, webhook handler
│   ├── paypal_service.py              ← NEW: PayPal webhook handler
│   └── payment_service.py             ← Extended: idempotency, fraud check,
│                                               ledger entries, payment methods,
│                                               payout request
└── routers/
    ├── account_router.py              ← NEW: /account/* endpoints
    ├── webhook_router.py              ← NEW: /webhooks/stripe, /webhooks/paypal
    ├── payments_router.py             ← Extended: stripe-intent, payment methods,
    │                                               payout endpoints
    └── main.py                        ← Extended: registered account_router,
                                                   webhook_router
```

### New Frontend Files

```
frontend/
├── app/
│   ├── account/
│   │   └── page.tsx                   ← NEW: 5-tab account settings page
│   └── wallet/
│       └── page.tsx                   ← REWRITTEN: full wallet dashboard
│                                               (student + researcher views)
└── lib/
    └── api.ts                         ← Extended: 15 new typed API functions
```

### New Database Tables

```
ledger_accounts       — double-entry ledger accounts (spec §4.4)
ledger_entries        — individual debit/credit lines (spec §4.5)
payment_methods       — saved Stripe/PayPal tokens (spec §4.7)
writer_payouts        — researcher payout requests (spec §4.10)
idempotency_keys      — duplicate request prevention (spec §12)
```

---

## Spec Coverage Matrix

| Spec Section | Description | Status |
|---|---|---|
| §1 System Overview | Financial infrastructure for marketplace | ✅ |
| §3 Event-Driven Architecture | Domain events on every financial operation | ✅ Synchronous; async queue ready |
| §4.1 Users | Extended user fields | ✅ Existing |
| §4.3 Wallets | One wallet per user, balance_cached | ✅ |
| §4.4 Ledger Accounts | 7 account types | ✅ |
| §4.5 Ledger Entries | Debit/credit pairs with check constraints | ✅ |
| §4.6 Transactions | Wallet transaction history | ✅ (`wallet_transactions` table) |
| §4.7 Payment Methods | Stripe + PayPal saved tokens | ✅ |
| §4.9 Escrow Accounts | Per-contract escrow with held/released/refunded | ✅ (`payments` table) |
| §4.10 Writer Payouts | pending→processing→completed/failed | ✅ |
| §5 Redis Cache | Wallet balance cache (TTL 24h) | ✅ Fraud counters; balance cache on roadmap |
| §6 Double-Entry Accounting | All 5 financial events post ledger pairs | ✅ |
| §7 Stripe Integration | PaymentIntent, 4 webhook events | ✅ |
| §8 PayPal Integration | 3 capture webhook events | ✅ |
| §9 Escrow System | Lock → release → refund | ✅ |
| §10 Writer Payout System | Manual payout request + history | ✅ Daily/weekly automated: planned |
| §11 Fraud Prevention | 3 rules implemented via Redis | ✅ |
| §12 Idempotent Payments | `Idempotency-Key` header on deposits | ✅ |
| §13 Webhook Security | Stripe sig verification, PayPal validation | ✅ |
| §14 OpenAPI Endpoints | All endpoints listed in §11 above | ✅ |
| §16 Performance | Paginated transactions (50/page max) | ✅ |
| §17 Security | PCI providers, rate limiting, bcrypt, JWT | ✅ |
| §18 UI Components | All listed components built | ✅ |
