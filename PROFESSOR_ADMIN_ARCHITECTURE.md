# Professor & Admin Architecture — Version 2

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Role Hierarchy](#2-role-hierarchy)
3. [Professor System Design](#3-professor-system-design)
4. [Admin System Design](#4-admin-system-design)
5. [Database Schema](#5-database-schema)
6. [API Reference](#6-api-reference)
7. [Workflow Integration Map](#7-workflow-integration-map)
8. [Comparison Against Industry Best Practices](#8-comparison-against-industry-best-practices)
9. [Ideal Architecture Recommendation](#9-ideal-architecture-recommendation)
10. [Environment Variables](#10-environment-variables)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    AssignmentOnline v2                       │
│                                                              │
│  ┌─────────┐   ┌────────────┐   ┌───────────┐   ┌───────┐  │
│  │ Student │   │ Researcher │   │ Professor │   │ Admin │  │
│  └────┬────┘   └─────┬──────┘   └─────┬─────┘   └───┬───┘  │
│       │              │                │              │      │
│  Post Job         Bid/Work       Review/Arbitrate  Manage   │
│       │              │                │              │      │
│  ┌────▼──────────────▼────────────────▼──────────────▼────┐ │
│  │                  FastAPI Backend                        │ │
│  │   /auth  /jobs  /contracts  /payments  /professor       │ │
│  │   /admin  /webhooks  /disputes  /submissions            │ │
│  └────────────────────┬────────────────────────────────────┘ │
│                       │                                      │
│           ┌───────────┼────────────────┐                    │
│           │           │                │                    │
│      ┌────▼────┐  ┌───▼───┐  ┌────────▼─────┐             │
│      │ Postgres│  │ Redis  │  │ Stripe/PayPal │             │
│      │   DB    │  │ Cache  │  │   Webhooks    │             │
│      └─────────┘  └───────┘  └──────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

**Stack:**
- Backend: FastAPI 0.111, Python 3.11, SQLAlchemy 2.0, PostgreSQL 15
- Frontend: Next.js 14 App Router, Tailwind CSS
- Auth: JWT (access + refresh tokens), role-based RBAC
- Payments: Stripe PaymentIntent + PayPal webhooks, double-entry ledger
- Queue: Redis sliding-window counters for fraud detection

---

## 2. Role Hierarchy

```
super_admin          ← Full platform override. Can assign admin roles.
    │
   admin             ← Platform operator. User/payout/dispute management.
    │
professor            ← Academic reviewer. Must be approved by admin.
    │
researcher ─── student   ← End users.
```

**Privilege inheritance (implemented in `require_role`):**
- `super_admin` passes ALL role checks
- `admin` passes all checks except `super_admin`-only endpoints
- `professor` only passes `professor`-only checks

**Role assignment flow:**
1. User registers with `student` or `researcher` role
2. Admin uses `POST /admin/users/{id}/role` to promote to `professor`
3. Promoted user creates professor profile at `POST /professor/profile`
4. Admin approves profile at `POST /admin/professors/{id}/action`
5. Professor can now accept queue items and submit reviews

---

## 3. Professor System Design

### 3.1 Who is a Professor?

A professor is a verified academic who:
- Is affiliated with a verified institution (e.g. MIT, Oxford)
- Has academic credentials (PhD, Postdoc, or equivalent)
- Is approved by a platform admin
- Earns a per-review fee (default $5/review, overridable per professor)
- Can optionally operate blind (anonymised reviews)

### 3.2 Professor Capabilities

| Capability | Description | Endpoint |
|---|---|---|
| Profile management | Create/edit academic profile | `POST/PATCH /professor/profile` |
| Credential verification | Verify researcher academic credentials | `POST /professor/credentials/{id}/action` |
| Endorsements | Publicly endorse researchers by subject area | `POST /professor/endorsements` |
| Assignment templates | Create rubric-backed job templates for students | `POST /professor/assignments` |
| Review queue | Accept and process assigned review items | `GET/POST /professor/queue` |
| Quality reviews | Score submissions (0–100), give feedback, decide verdict | `POST /professor/reviews/contract/{id}` |
| Dispute arbitration | Issue binding rulings on contested contracts | `POST /professor/disputes/{id}/ruling` |
| Analytics | View own performance metrics and SLA compliance | `GET /professor/analytics` |

### 3.3 Quality Review Workflow

```
Contract submitted
       │
  [Admin/System] Creates ReviewQueueItem
       │
  [Professor] Sees item in /professor/queue
       │
  [Professor] Accepts item → status: in_progress
       │ (SLA clock starts — default 48h)
       │
  [Professor] Reviews submission materials
       │
  [Professor] Submits QualityReview with:
      ├─ score (0–100)
      ├─ originality_score (plagiarism: 0–100)
      ├─ feedback (min 50 chars)
      ├─ rubric_scores (per-criterion breakdown)
      └─ verdict: approved | revision_required | rejected
       │
  Verdict outcomes:
  ├─ approved       → Contract status → 'completed' → Payment released
  ├─ revision_required → Contract → 'revision_requested' → Researcher revises
  └─ rejected       → Contract → 'disputed' → Admin handles refund
```

### 3.4 Dispute Arbitration Workflow

```
Dispute opened (student or researcher)
       │
  [Admin] Reviews dispute
       │
  [Admin] Assigns professor → POST /admin/disputes/{id}/assign-professor
       │ (Priority-1 queue item created, 72h SLA)
       │
  [Professor] Reviews all materials (contract, submissions, messages)
       │
  [Professor] Submits DisputeRuling:
      ├─ full_release      → Pay researcher 100%
      ├─ partial_release   → Pay researcher N% (specify percentage)
      ├─ full_refund       → Refund student entirely
      └─ revision          → One more revision round
       │
  [Admin] Executes financial action → POST /admin/disputes/{id}/resolve
  (Professor ruling is binding unless overridden by super_admin)
```

### 3.5 Credential Verification System

```
Researcher submits credential → status: pending
  ├─ credential_type: bachelors | masters | phd | postdoc | certification | publication | award
  ├─ institution_name
  ├─ field_of_study
  ├─ document_url (scanned certificate, pre-signed S3 URL)
  └─ year_obtained

Professor reviews credential
  ├─ verify → status: verified (timestamp + professor ID recorded)
  └─ reject → status: rejected (rejection_reason required)

Verified credentials appear on researcher's public profile.
They unlock premium job categories and boost bid credibility.
```

### 3.6 Course Assignment Templates

Professors create assignment templates that students use to quickly post jobs:
```json
{
  "title": "Literature Review: Machine Learning Ethics",
  "subject": "Computer Science",
  "academic_level": "Postgraduate",
  "rubric": "## Criteria\n1. Coverage (30pts)\n2. Critical analysis (40pts)\n3. Citations (30pts)",
  "min_quality_score": 75,
  "review_required": true,
  "suggested_price": 150.00,
  "deadline_hours": 168
}
```

When `review_required: true`, the contract is placed in the review queue after submission and **payment is held** until the professor approves.

---

## 4. Admin System Design

### 4.1 Admin Responsibilities

| Area | Operations |
|---|---|
| **Users** | List, search, filter, verify, assign roles, suspend, unsuspend, ban |
| **Professors** | List by status, approve/reject applications, override review fees |
| **Jobs** | List all jobs across all statuses |
| **Contracts** | View all contracts with student/researcher details |
| **Disputes** | List, assign professors, execute financial resolutions |
| **Payouts** | List pending payouts, approve (→ processing) or reject (auto-refund) |
| **Transactions** | Full wallet transaction ledger with volume aggregates |
| **Config** | Edit platform-wide configuration key/value pairs |
| **Audit Log** | Browse all admin actions with filter by actor, entity, action |
| **Analytics** | Real-time platform overview (users, jobs, revenue, quality KPIs) |

### 4.2 Admin Dashboard Metrics

```
Users:     Total | Active | Students | Researchers | Professors | New This Month
Jobs:      Total | Open | Completed | Disputed
Revenue:   Total Volume | Platform Revenue (fee%) | Pending Payouts
Quality:   Completion Rate | Avg Review Score | Avg Dispute Resolution Hours
```

### 4.3 Payout Approval Chain

```
Researcher requests payout → status: pending
   (funds debited from WRITER_WALLET immediately)

Admin reviews payout queue → GET /admin/payouts?status=pending

Admin approves → status: processing
   → Payout disbursed via Stripe/PayPal (external step)
   → Admin marks complete (future: automated)

Admin rejects → status: failed
   → Funds automatically refunded to researcher's wallet
   → Rejection reason stored
```

### 4.4 Platform Configuration Keys

| Key | Default | Description |
|---|---|---|
| `platform_fee_pct` | `15` | % of every released payment taken as platform fee |
| `professor_review_fee_usd` | `5.00` | Base fee paid to professor per review |
| `max_revision_rounds` | `3` | Auto-dispute if exceeded |
| `quality_review_required` | `false` | Require professor review before payment release (global) |
| `dispute_sla_hours` | `72` | Hours for professor to submit dispute ruling |
| `review_sla_hours` | `48` | Hours for professor to complete quality review |
| `payout_min_usd` | `10` | Minimum payout amount |
| `fraud_deposit_limit_per_2min` | `3` | Fraud detection: max deposits per 2 min |
| `fraud_failure_limit_per_10min` | `5` | Fraud detection: max failures per 10 min |
| `fraud_kyc_threshold_usd` | `2000` | KYC flag threshold |

---

## 5. Database Schema

### New Tables (v2)

#### `institutions`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(255) UNIQUE | Institution name |
| country | VARCHAR(100) | |
| domain | VARCHAR(100) | Email domain for auto-verification |
| is_verified | BOOLEAN | Admin-verified institution |
| verified_by | UUID FK→users | |

#### `professor_profiles`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users UNIQUE | |
| institution_id | UUID FK→institutions | |
| title | VARCHAR(50) | Dr., Prof., etc. |
| department | VARCHAR(200) | |
| academic_rank | ENUM | lecturer\|assistant\|associate\|full\|emeritus\|adjunct |
| bio | TEXT | |
| expertise_areas | TEXT[] | Array of expertise tags |
| orcid_id | VARCHAR(20) | ORCID identifier |
| institutional_email | VARCHAR(255) | Used for institutional verification |
| status | ENUM | pending\|approved\|rejected\|suspended |
| approved_by | UUID FK→users | Admin who approved |
| review_subjects | TEXT[] | Subjects this professor can review |
| total_reviews_completed | INT | Running count |
| avg_review_score_given | NUMERIC(4,2) | Rolling average |
| review_fee_per_job | NUMERIC(8,2) | USD fee per review (default $5) |

#### `researcher_credentials`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| researcher_id | UUID FK→users | |
| credential_type | ENUM | bachelors\|masters\|phd\|postdoc\|certification\|publication\|award\|other |
| institution_name | VARCHAR(255) | |
| field_of_study | VARCHAR(255) | |
| year_obtained | INT | |
| document_url | VARCHAR(1000) | S3 URL |
| status | ENUM | pending\|verified\|rejected |
| verified_by_id | UUID FK→professor_profiles | |
| verified_at | TIMESTAMPTZ | |
| rejection_reason | TEXT | |

#### `professor_endorsements`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| professor_id | UUID FK→professor_profiles | |
| researcher_id | UUID FK→users | |
| subject_area | VARCHAR(200) | |
| endorsement_text | TEXT | |
| is_active | BOOLEAN | Soft-revocable |
| UNIQUE | (professor_id, researcher_id, subject_area) | One endorsement per combo |

#### `course_assignments`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| professor_id | UUID FK→professor_profiles | |
| title | VARCHAR(300) | |
| description | TEXT | |
| subject | VARCHAR(200) | |
| academic_level | VARCHAR(100) | |
| rubric | TEXT | Markdown rubric |
| min_quality_score | INT | 0–100 threshold for auto-approve |
| review_required | BOOLEAN | Gate payment on professor approval |
| suggested_price | NUMERIC(10,2) | |
| deadline_hours | INT | |
| is_active | BOOLEAN | Soft delete |

#### `quality_reviews`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| contract_id | UUID FK→contracts | |
| professor_id | UUID FK→professor_profiles | |
| assignment_id | UUID FK→course_assignments | Optional link |
| submission_id | UUID FK→submissions | Specific submission reviewed |
| round_number | INT | 1, 2, 3… |
| status | ENUM | pending\|in_review\|approved\|revision_required\|rejected |
| score | INT | 0–100 (CHECK constraint) |
| originality_score | INT | 0–100 (CHECK constraint) |
| feedback | TEXT | Min 50 chars |
| rubric_scores | TEXT | JSON: {criterion: score} |
| payment_held | BOOLEAN | True = payment gated on this review |
| reviewed_at | TIMESTAMPTZ | |
| fee_amount | NUMERIC(8,2) | Fee earned by professor |
| fee_paid | BOOLEAN | |

#### `dispute_rulings`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| dispute_id | UUID FK→disputes UNIQUE | One ruling per dispute |
| professor_id | UUID FK→professor_profiles | |
| ruling | ENUM | full_release\|partial_release\|full_refund\|revision |
| release_percentage | NUMERIC(5,2) | Required for partial_release |
| reasoning | TEXT | Min 100 chars |
| evidence_reviewed | TEXT | Materials reviewed summary |
| submitted_at | TIMESTAMPTZ | |
| overridden_by | UUID FK→users | super_admin override |
| override_reason | TEXT | |

#### `review_queue`
| Column | Type | Description |
|---|---|---|
| id | UUID PK | |
| contract_id | UUID FK→contracts | |
| professor_id | UUID FK→professor_profiles | Assigned professor |
| queue_type | ENUM | quality_review\|credential_verification\|dispute_arbitration |
| status | ENUM | queued\|assigned\|in_progress\|completed\|reassigned\|expired |
| priority | INT | 1=urgent (disputes), 10=low |
| sla_hours | INT | Hours to complete from assignment |
| due_at | TIMESTAMPTZ | Assignment time + SLA |
| assigned_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | |

#### `platform_config`
| Column | Type | Description |
|---|---|---|
| key | VARCHAR(100) PK | Config key |
| value | TEXT | String value (cast at runtime) |
| description | TEXT | Human-readable description |
| updated_by | UUID FK→users | |
| updated_at | TIMESTAMPTZ | Auto-updated |

### Updated Tables

#### `users.role` (ENUM extended)
```
student | researcher | professor | admin | super_admin
```

---

## 6. API Reference

### Professor Endpoints (`/api/v1/professor/`)

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | /institutions | any | List verified institutions |
| POST | /profile | professor | Create professor profile |
| GET | /profile | professor | Get own profile |
| PATCH | /profile | professor | Update profile |
| POST | /credentials | researcher | Submit credential for verification |
| GET | /credentials/pending | professor | View pending credentials |
| POST | /credentials/{id}/action | professor | Verify or reject credential |
| GET | /credentials/researcher/{id} | any | Get researcher's credentials |
| POST | /endorsements | professor | Endorse a researcher |
| GET | /endorsements/researcher/{id} | any | Get researcher's endorsements |
| DELETE | /endorsements/{id} | professor | Revoke endorsement |
| POST | /assignments | professor | Create course assignment template |
| GET | /assignments | professor | List own assignments |
| PATCH | /assignments/{id} | professor | Update assignment |
| DELETE | /assignments/{id} | professor | Deactivate assignment |
| GET | /queue | professor | View review queue |
| POST | /queue/{id}/accept | professor | Accept queue item (starts SLA) |
| POST | /reviews/contract/{id} | professor | Submit quality review |
| GET | /reviews | professor | List own reviews |
| GET | /reviews/contract/{id} | any | Get reviews for a contract |
| GET | /disputes | professor | Get assigned disputes |
| POST | /disputes/{id}/ruling | professor | Submit dispute ruling |
| GET | /analytics | professor | Own performance analytics |

### Admin Endpoints (`/api/v1/admin/`)

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | /dashboard | admin | Platform overview metrics |
| GET | /users | admin | List all users (search, filter) |
| GET | /users/{id} | admin | User detail with activity |
| POST | /users/{id}/verify | admin | Mark user as verified |
| POST | /users/{id}/role | admin | Assign role |
| PATCH | /users/{id}/suspend | admin | Suspend user |
| PATCH | /users/{id}/unsuspend | admin | Re-activate user |
| POST | /users/{id}/ban | super_admin | Permanently ban user |
| GET | /professors | admin | List professor profiles |
| POST | /professors/{id}/action | admin | Approve or reject professor |
| GET | /disputes | admin | All disputes |
| POST | /disputes/{id}/assign-professor | admin | Assign professor to dispute |
| POST | /disputes/{id}/resolve | admin | Execute financial resolution |
| GET | /payouts | admin | All payout requests |
| POST | /payouts/{id}/approve | admin | Approve payout (→ processing) |
| POST | /payouts/{id}/reject | admin | Reject + auto-refund payout |
| GET | /transactions | admin | Platform transaction ledger |
| GET | /config | admin | Get all config values |
| PATCH | /config/{key} | admin | Update config value |
| POST | /config/seed | admin | Seed default config |
| GET | /audit-log | admin | Full audit trail |

---

## 7. Workflow Integration Map

### How Professor Touches Every App Process

```
Job Posting
  └─ Professor creates CourseAssignment template
  └─ Student uses template → job pre-filled with professor's rubric

Bidding
  └─ Researcher credentials verified by professor → badge shown on bid
  └─ Professor endorsements boost researcher's credibility score

Contract Start
  └─ If assignment has review_required=true → payment held in escrow
  └─ ReviewQueueItem created, assigned to professor on submission

Submission
  └─ Professor receives queue item (priority 5, SLA 48h)
  └─ Professor reviews against rubric → quality score + feedback
  └─ Verdict:
      approved           → contract.status = completed
      revision_required  → contract.status = revision_requested
      rejected           → contract.status = disputed

Payment Release
  └─ If review_required: payment gated on professor 'approved' verdict
  └─ Professor fee deducted from platform revenue, paid to professor

Dispute
  └─ Admin assigns approved professor (priority 1, SLA 72h)
  └─ Professor reviews all materials (blind to financial stakes)
  └─ Professor issues DisputeRuling
  └─ Admin executes financial action per ruling
  └─ Ruling overridable only by super_admin (with reason required)

Researcher Reputation
  └─ Professor-verified credentials displayed on researcher profile
  └─ Professor endorsements boost search ranking
  └─ Quality review scores build researcher's overall platform rating
```

---

## 8. Comparison Against Industry Best Practices

### 8.1 Reference Platforms

| Platform | Model | Key Takeaways |
|---|---|---|
| **Upwork** | Client + Freelancer + Agency + Enterprise | Agency model adds a verified intermediary layer (our professor equivalent). Agency contracts have milestone-based payments — same as our review_required gate. |
| **Coursera / EdX** | Student + Instructor + Staff + Institution | Instructors create rubric-backed assignments and grade through a queue system. Our CourseAssignment + QualityReview mirrors this exactly. Peer review for scale; expert review for quality. |
| **Chegg / TutorMe** | Student + Expert Tutor | Tutors are vetted before assignment. Our professor approval workflow mirrors this. |
| **Fiverr Business** | Client + Seller + Success Manager | Success Manager (= our professor) reviews deliverables, mediates disputes, verifies seller credentials. |
| **Academia.edu / ResearchGate** | Researcher + Institution | ORCID integration, institutional affiliation, credential display — all implemented in our professor model. |
| **Elance (legacy)** | Client + Freelancer + Arbiter | Paid arbitrators settle disputes. Our professor dispute ruling system directly mirrors this with the added academic layer. |

### 8.2 Best Practice Comparison Matrix

| Practice | Industry Standard | Our Implementation | Gap |
|---|---|---|---|
| **Role hierarchy** | RBAC with inheritance | super_admin > admin > professor > researcher > student with `require_role` elevation | ✅ Fully implemented |
| **Expert vetting** | Manual + automated credential check | Professor approval by admin + ORCID/institutional email field | ⚠️ ORCID API integration not yet automated |
| **Assignment templates** | Coursera: rubric-backed graded assignments | CourseAssignment with rubric + min_quality_score + review_required gate | ✅ Fully implemented |
| **Blind review** | Upwork: anonymous bid review | review_required contracts don't expose reviewer identity to researcher | ⚠️ Not fully enforced at API level (roadmap) |
| **SLA enforcement** | Fiverr: delivery time guarantees | ReviewQueueItem SLA with `due_at`, status tracking | ⚠️ Auto-reassignment on SLA breach not yet automated (status marked 'expired' only) |
| **Dispute arbitration** | Elance: paid arbitrators | Professor DisputeRuling with financial outcome separation | ✅ Fully implemented |
| **Audit trail** | SOC2: complete admin action log | AuditLog table + `log_admin_action()` on every write | ✅ Fully implemented |
| **Config management** | 12-factor app: environment-based config | PlatformConfig table for runtime-editable config + env vars for secrets | ✅ Hybrid approach |
| **Credential verification** | LinkedIn: verified badge | ResearcherCredential with professor verification + document URL | ✅ Implemented (manual review) |
| **Quality scoring** | Coursera: rubric-based grading | QualityReview with score + rubric_scores + feedback | ✅ Implemented |
| **Plagiarism check** | Turnitin: automated originality | originality_score field (manual entry) | ⚠️ Manual only; Turnitin/iThenticate API not integrated |
| **Payment gating** | Coursera: grade threshold for certificate | review_required + min_quality_score gates payment release | ✅ Fully implemented |
| **Multi-round review** | Academic journals: R&R process | round_number on QualityReview + max_revision_rounds config | ✅ Fully implemented |
| **Professor incentives** | Chegg: per-session payment | review_fee_per_job (USD per review, admin-configurable per professor) | ✅ Implemented (payout via platform payout system) |
| **Conflict of interest** | Academic standard: recusal | Not yet enforced — professor could review work from their own student | ❌ Not implemented (roadmap: link professors to student cohorts) |

### 8.3 What We Do Better Than Most Platforms

1. **Double-entry ledger**: Chegg and Upwork use simple wallet balances. Our implementation uses full double-entry bookkeeping (LedgerAccount + LedgerEntry pairs) — the gold standard for fintech.

2. **Professor as third party**: Most platforms have a binary client/provider relationship. Our professor layer creates a neutral, credentialled third party for quality and dispute resolution — reducing platform intervention costs.

3. **Assignment template system**: Unique to academic platforms. Professors don't just review; they shape the job specification. This reduces ambiguity and revision rates.

4. **Credential chain of trust**: Researchers get credentials verified by professors, who are verified by admins, who are verified by the platform. This creates a verifiable trust chain that Fiverr and Upwork lack.

5. **Idempotency on all financial endpoints**: Industry standard but not always implemented. Every payment endpoint uses Idempotency-Key headers stored in the DB.

---

## 9. Ideal Architecture Recommendation

Based on the comparison above, the ideal v3 architecture should add:

### 9.1 Automated Credential Verification
```
ORCID API integration → auto-verify PhD/publication credentials
Institutional email verification → send code to .edu address
LinkedIn API → verify employment history
```

### 9.2 SLA Auto-Enforcement (Celery Task)
```python
# Celery beat task — runs every 30 minutes
@celery.task
def check_sla_breaches():
    overdue = db.query(ReviewQueueItem).filter(
        ReviewQueueItem.due_at < datetime.now(UTC),
        ReviewQueueItem.status.in_(['assigned', 'in_progress'])
    ).all()
    for item in overdue:
        item.status = 'expired'
        reassign_to_next_available_professor(item)
        notify_admin(item)
```

### 9.3 Conflict of Interest Prevention
```sql
-- Professors cannot review work from students in their course cohort
ALTER TABLE professor_profiles ADD cohort_student_ids UUID[];

-- Service check before queue assignment:
-- if contract.student_id IN professor.cohort_student_ids → skip professor
```

### 9.4 Plagiarism API Integration
```python
# After submission, call iThenticate/Turnitin API
async def check_originality(submission_file_url: str) -> int:
    # Returns 0–100 originality score
    # Stored in quality_review.originality_score
    # Below 70 → auto-flag for review
```

### 9.5 Professor Matching Algorithm
Instead of manual queue assignment:
```python
def find_best_professor(job_subject: str, job_level: str) -> ProfessorProfile:
    candidates = db.query(ProfessorProfile).filter(
        ProfessorProfile.status == 'approved',
        ProfessorProfile.review_subjects.contains([job_subject]),
    ).all()
    # Score by: active queue depth (lower = better),
    #           avg_review_score_given (higher = better),
    #           sla_compliance_rate (higher = better)
    return min(candidates, key=lambda p: score(p))
```

### 9.6 WebSocket Real-Time Queue Notifications
```typescript
// Professor gets notified immediately when a queue item is assigned
const ws = new WebSocket(`wss://api/ws/professor/${professorId}/queue`)
ws.onmessage = (event) => {
  const { type, item } = JSON.parse(event.data)
  if (type === 'new_queue_item') showNotification(item)
}
```

### 9.7 Complete Ideal Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Ideal v3 Architecture                         │
│                                                                     │
│  Frontend (Next.js 14)                                              │
│  ├─ /student    → dashboard, marketplace, jobs, contracts, wallet   │
│  ├─ /researcher → dashboard, browse, bids, contracts, wallet        │
│  ├─ /professor  → queue, reviews, assignments, credentials, analytics│
│  └─ /admin      → dashboard, users, professors, disputes, payouts   │
│                                                                     │
│  API Gateway (FastAPI)                                              │
│  ├─ JWT auth + RBAC (role hierarchy)                                │
│  ├─ Rate limiting (slowapi + Redis)                                 │
│  ├─ Idempotency (all write endpoints)                               │
│  └─ Structured JSON logging                                         │
│                                                                     │
│  Business Logic Layer (Services)                                    │
│  ├─ auth_service       → registration, login, JWT                   │
│  ├─ job_service        → CRUD, pricing, deadline                    │
│  ├─ bid_service        → bidding, floor enforcement, counter        │
│  ├─ contract_service   → lifecycle management                       │
│  ├─ submission_service → upload, approve, revise                    │
│  ├─ payment_service    → escrow, release, refund (double-entry)     │
│  ├─ stripe_service     → PaymentIntent, webhooks                    │
│  ├─ paypal_service     → capture webhooks                           │
│  ├─ fraud_service      → Redis sliding-window counters              │
│  ├─ ledger_service     → double-entry accounting posts              │
│  ├─ professor_service  → review queue, quality, disputes [NEW]      │
│  ├─ admin_service_v2   → platform management, analytics [NEW]       │
│  ├─ messaging_service  → conversations, WhatsApp                    │
│  └─ notification_service → WebSocket, email, WhatsApp push          │
│                                                                     │
│  Data Layer                                                         │
│  ├─ PostgreSQL 15 (primary)                                         │
│  │  ├─ Users + Profiles (student, researcher, professor)            │
│  │  ├─ Jobs, Bids, Contracts, Submissions                           │
│  │  ├─ Payments (double-entry: LedgerAccount + LedgerEntry)         │
│  │  ├─ Professor system (9 new tables)                              │
│  │  └─ PlatformConfig (runtime-editable settings)                   │
│  ├─ Redis (cache + queues)                                          │
│  │  ├─ Fraud detection sliding-window counters                      │
│  │  ├─ Session tokens (blacklist)                                   │
│  │  └─ Celery task broker                                           │
│  └─ S3 (file storage)                                               │
│     ├─ Job attachments                                              │
│     ├─ Submission files                                             │
│     └─ Credential documents                                         │
│                                                                     │
│  Async Workers (Celery)                                             │
│  ├─ Email notifications                                             │
│  ├─ WhatsApp notifications                                          │
│  ├─ SLA breach detection + professor reassignment [ROADMAP]         │
│  ├─ Originality check (Turnitin/iThenticate) [ROADMAP]             │
│  └─ Payout disbursement via Stripe/PayPal                          │
│                                                                     │
│  External Integrations                                              │
│  ├─ Stripe (PaymentIntent, Connect, webhooks)                       │
│  ├─ PayPal (capture webhooks)                                       │
│  ├─ WhatsApp Business API                                           │
│  ├─ AWS S3                                                          │
│  ├─ ORCID API [ROADMAP]                                             │
│  └─ iThenticate/Turnitin API [ROADMAP]                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Environment Variables

Add the following to your `.env`:

```bash
# Existing (v1)
DATABASE_URL=postgresql+psycopg2://research:research@127.0.0.1:5432/research_marketplace
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=<long-random-secret>
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...

# New (v2 — Professor/Admin system)
# All below have working defaults; override in production
PLATFORM_FEE_PCT=15           # Seeded via POST /admin/config/seed
PROFESSOR_REVIEW_FEE=5.00     # Default per-review fee
DEFAULT_REVIEW_SLA_HOURS=48   # Quality review SLA
DEFAULT_DISPUTE_SLA_HOURS=72  # Dispute ruling SLA
MAX_REVISION_ROUNDS=3         # Before auto-dispute

# Optional integrations (roadmap)
ORCID_CLIENT_ID=...
ORCID_CLIENT_SECRET=...
ITNENTICATE_API_KEY=...
```

---

*Document version: 2.0 | Branch: feature/professor-admin-portal*
