# ASA v2.5 — Agentic Scholar Assistant
## Complete Architecture Document
### Replication Guide for AI Agents & Developers

> **Purpose**: This document is a complete, self-contained blueprint of the ASA platform.
> Every file, every function signature, every database table, every API endpoint, and every
> deployment detail is documented here. An AI agent reading this document should be able to
> reconstruct the entire system from scratch.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Directory Structure](#3-directory-structure)
4. [Database Schema](#4-database-schema)
5. [API Layer (FastAPI)](#5-api-layer-fastapi)
6. [Authentication System](#6-authentication-system)
7. [Assignment Pipeline — 13 Stages](#7-assignment-pipeline--13-stages)
8. [Research Agents](#8-research-agents)
9. [Writing Agent](#9-writing-agent)
10. [QA Agent](#10-qa-agent)
11. [Delivery Agent](#11-delivery-agent)
12. [Knowledge Graph](#12-knowledge-graph)
13. [Vector Embeddings](#13-vector-embeddings)
14. [Billing System](#14-billing-system)
15. [LMS Submission Agent](#15-lms-submission-agent)
16. [Frontend (Next.js)](#16-frontend-nextjs)
17. [Infrastructure & Deployment](#17-infrastructure--deployment)
18. [Environment Variables](#18-environment-variables)
19. [Data Flow — End to End](#19-data-flow--end-to-end)
20. [Replication Checklist](#20-replication-checklist)

---

## 1. System Overview

ASA v2.5 is a fully agentic academic writing platform. Students submit assignment briefs through
a web portal; the platform autonomously researches, writes, quality-checks, and delivers a
polished academic essay in DOCX format — optionally uploading it directly to the student's LMS.

### Core Value Proposition

- Student inputs: assignment title, topic, instructions, word count, academic level, citation style
- Platform outputs: formatted DOCX essay with 20–50 academic sources, plagiarism < 15%, quality ≥ 75/100
- Optional: automatic LMS submission (Moodle, Canvas, Blackboard) via headless browser

### What Makes It "Agentic"

1. **Assignment Analysis Agent** — DeepSeek reads the brief and extracts keywords, methodology,
   required source count, focus region, and academic scope
2. **Query Expansion Engine** — generates 8–15 search query variants (keyword, boolean, author-based, OA-only)
3. **Parallel Research Agents** — Web Agent and Institutional Agent run concurrently via `asyncio.gather()`
4. **Knowledge Graph** — papers are stored as nodes with typed edges (WRITTEN_BY, PUBLISHED_IN,
   STUDIES, USES_METHOD, ACCESSIBLE_VIA) and grow across sessions
5. **Context Builder** — groups papers into themes, ranks by impact, extracts arguments and contradictions
6. **Writing Agent** — DeepSeek `deepseek-reasoner` writes with full context (themes, arguments, region focus)
7. **QA Agent** — Copyleaks plagiarism check + DeepSeek tone rewrite + citation validation
8. **Delivery Agent** — DOCX generation via `python-docx`, optional LMS upload via Playwright

---

## 2. Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| API framework | FastAPI | 0.111.0 | HTTP REST API |
| ASGI server | Uvicorn | 0.29.0 | Production server |
| ORM | SQLAlchemy | 2.0.30 | Database models |
| DB driver | psycopg2-binary | 2.9.9 | PostgreSQL adapter |
| Vector DB | pgvector | 0.2.5 | 1536-dim embeddings |
| Data validation | Pydantic | 2.7.1 | Request/response schemas |
| Settings | pydantic-settings | 2.2.1 | `.env` loading |
| Auth tokens | python-jose[cryptography] | 3.3.0 | JWT signing/verification |
| Password hashing | passlib[bcrypt] + bcrypt | 1.7.4 + 4.0.1 | bcrypt hashing |
| HTTP client | httpx | 0.27.0 | External API calls (async) |
| Payments | stripe | 9.9.0 | Stripe Checkout |
| Document gen | python-docx | 1.1.0 | DOCX creation |
| Encryption | cryptography | 42.0.8 | Fernet AES-128 for LMS passwords |
| Cache/queue | redis | 5.0.4 | Session cache |
| Task queue | celery | 5.4.0 | Background tasks |
| File upload | python-multipart | 0.0.9 | Multipart form data |
| Email | aiosmtplib | 3.0.1 | Async SMTP |
| S3 storage | boto3 | 1.34.110 | File storage |
| PDF extraction | PyMuPDF | 1.24.3 | Extract text from PDFs |

### AI APIs

| Service | Model | Purpose | Key |
|---|---|---|---|
| DeepSeek | deepseek-reasoner | Essay writing | DEEPSEEK_API_KEY |
| DeepSeek | deepseek-chat | Assignment analysis, tone rewrite | DEEPSEEK_API_KEY |
| Perplexity Sonar | sonar-pro | Web research | PERPLEXITY_API_KEY |
| OpenAI-compatible | text-embedding-3-large | 1536-dim embeddings | OPENAI_API_KEY (optional) |
| Copyleaks | — | Plagiarism detection | COPYLEAKS_API_KEY + COPYLEAKS_EMAIL |
| Scopus (Elsevier) | — | Institutional search | SCOPUS_API_KEY |
| Springer Nature | — | Academic metadata | SPRINGER_API_KEY |
| IEEE Xplore | — | Technical papers | IEEE_API_KEY |
| CrossRef | — | DOI lookup (free) | no key needed |
| arXiv | — | OA preprints (free) | no key needed |
| DOAJ | — | OA journals (free) | no key needed |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Framework | Next.js 14 (App Router) | 14.x |
| Styling | Tailwind CSS | 3.x |
| Forms | react-hook-form | 7.x |
| HTTP | axios | 1.x |
| Language | TypeScript | 5.x |

### Infrastructure

| Component | Technology | Notes |
|---|---|---|
| Database | PostgreSQL 16 + pgvector | pgvector extension required |
| Cache | Redis 7 | Rate limiting, sessions |
| Reverse proxy | Nginx | Routes /, /api/, /ws/ |
| Containerisation | Docker Compose | 5 services |
| LMS automation | Playwright (Node.js) | Chromium headless |
| LMS automation | Playwright (Python) | Via venv for pipeline |

---

## 3. Directory Structure

```
asa-platform/
├── .env                          # Runtime secrets (never commit)
├── .env.example                  # Template with all keys documented
├── .gitignore
├── requirements.txt              # Top-level (mirrors api/requirements.txt)
│
├── api/                          # FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # App factory, router registration, startup
│   ├── config.py                 # Pydantic Settings (reads .env)
│   ├── database.py               # SQLAlchemy engine, SessionLocal, Base
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py           # Re-exports all models (so create_all_tables works)
│   │   ├── user.py               # User, Wallet, WalletTransaction
│   │   ├── assignment.py         # Assignment, AssignmentSubmission, Delivery
│   │   ├── billing.py            # Order, Subscription
│   │   ├── research.py           # ResearchSource, ResearchEmbedding, KGNode, KGEdge
│   │   └── dom_graph.py          # DomGraph, DomSelector (LMS DOM cache)
│   │
│   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py               # UserCreate, UserLogin, UserOut, Token
│   │   ├── assignment.py         # AssignmentCreate, AssignmentOut, AssignmentStatusOut
│   │   ├── billing.py            # OrderCreate, OrderOut, CheckoutSession
│   │   └── research.py           # SemanticSearchQuery, SearchResult
│   │
│   ├── routes/                   # FastAPI routers
│   │   ├── __init__.py           # Exports all routers
│   │   ├── auth.py               # /auth/* — register, login, refresh, me
│   │   ├── assignments.py        # /assignments/* — CRUD + pipeline trigger
│   │   ├── billing.py            # /billing/* — Stripe, PayPal, pricing
│   │   ├── research.py           # /research/* — semantic search
│   │   ├── webhook.py            # /webhook/* — n8n status callbacks
│   │   └── admin.py              # /admin/* — internal admin tools
│   │
│   └── services/                 # Business logic
│       ├── auth_service.py       # register, authenticate, JWT encode/decode
│       ├── assignment_service.py # create_assignment, Fernet encrypt, pipeline_log
│       └── billing_service.py    # Stripe checkout, PayPal order, webhook handler
│
├── orchestrator/                 # Python async pipeline orchestration
│   ├── __init__.py               # Exports run_pipeline, analyze_assignment, etc.
│   ├── pipeline.py               # Main 13-stage async pipeline
│   ├── analysis_agent.py         # DeepSeek assignment brief parser
│   ├── query_expansion.py        # Generates keyword/boolean/OA query variants
│   └── context_builder.py        # Theme grouping, paper ranking, contradiction detection
│
├── agents/                       # Individual AI agents
│   ├── research/
│   │   ├── __init__.py
│   │   ├── web_agent.py          # Perplexity + CrossRef + arXiv + DOAJ
│   │   ├── institutional_agent.py # Scopus + Springer + IEEE + CrossRef
│   │   ├── normalizer.py         # Dedup, 3-strategy DOI extraction, APA formatter
│   │   └── access_classifier.py  # OPEN_ACCESS / INSTITUTIONAL / PROXY / AUTHOR_COPY
│   ├── writing_agent.py          # DeepSeek deepseek-reasoner essay generation
│   ├── qa_agent.py               # Plagiarism + tone rewrite + citation validation
│   ├── delivery_agent.py         # DOCX gen + email + LMS upload
│   ├── scraping_agent.py         # Playwright LMS scraper (course/assignment discovery)
│   ├── research_agent.py         # Legacy web research (v2 — use agents/research/ instead)
│   └── pipeline.py               # Legacy pipeline (v2 — use orchestrator/ instead)
│
├── embeddings/
│   └── pipeline.py               # Chunking, embedding, pgvector storage, semantic search
│
├── knowledge_graph/
│   └── graph_service.py          # Upsert nodes/edges, graph stats
│
├── frontend/                     # Next.js 14 student portal
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx            # Root layout, font loading
│   │   ├── globals.css           # Tailwind base styles
│   │   ├── api/                  # Next.js API routes (thin proxies)
│   │   ├── auth/
│   │   │   ├── login/page.tsx    # Login form
│   │   │   └── register/page.tsx # Registration form
│   │   ├── dashboard/page.tsx    # Assignment list, stats
│   │   ├── assignments/
│   │   │   └── new/page.tsx      # 4-step assignment creation wizard
│   │   └── billing/page.tsx      # Payment selection and pricing
│   ├── components/
│   │   ├── Sidebar.tsx           # Navigation sidebar
│   │   ├── forms/                # Reusable form components
│   │   └── ui/                   # Buttons, cards, badges
│   └── lib/
│       └── api.ts                # Axios instance with JWT auto-refresh interceptor
│
├── infrastructure/
│   ├── docker/
│   │   └── docker-compose.yml    # Full 5-service stack
│   └── configs/
│       └── nginx.conf            # Reverse proxy config
│
├── scripts/                      # Utility scripts
├── workflows/                    # n8n workflow JSON exports (v2 — not used in v2.5)
└── templates/                    # Email templates
```

---

## 4. Database Schema

PostgreSQL 16 with `pgvector` extension. All primary keys are UUID v4.

### 4.1 users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,        -- bcrypt via passlib
    full_name       VARCHAR(255) NOT NULL,
    academic_level  academiclevel,                -- ENUM: high_school, undergraduate, postgraduate, phd
    institution     VARCHAR(255),
    is_active       BOOLEAN DEFAULT true,
    is_verified     BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);
```

### 4.2 wallets

```sql
CREATE TABLE wallets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID UNIQUE REFERENCES users(id),
    balance     NUMERIC(12,2) DEFAULT 0,
    currency    VARCHAR(3) DEFAULT 'USD',
    created_at  TIMESTAMP DEFAULT now(),
    updated_at  TIMESTAMP DEFAULT now()
);
-- Created automatically when user registers
```

### 4.3 wallet_transactions

```sql
CREATE TABLE wallet_transactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id   UUID REFERENCES wallets(id),
    amount      NUMERIC(12,2) NOT NULL,
    tx_type     VARCHAR(50),        -- 'deposit', 'debit', 'refund'
    description TEXT,
    reference   VARCHAR(255),
    created_at  TIMESTAMP DEFAULT now()
);
```

### 4.4 assignments

```sql
CREATE TABLE assignments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users(id) NOT NULL,

    -- Assignment brief (from student)
    title             VARCHAR(500) NOT NULL,
    module_code       VARCHAR(100),
    topic             TEXT,
    instructions      TEXT,
    focus_area        TEXT,          -- e.g. "focus specifically on insurance sector"
    word_count        INTEGER DEFAULT 2000,
    academic_level    VARCHAR(50),
    deadline          TIMESTAMP,
    citation_style    VARCHAR(20) DEFAULT 'Harvard',  -- Harvard, APA, MLA, Chicago

    -- LMS auto-submit credentials (encrypted at rest with Fernet AES-128)
    lms_url           VARCHAR(500),
    lms_username      VARCHAR(255),
    lms_password_enc  TEXT,          -- encrypted; decrypted only inside delivery_agent
    lms_assignment_id VARCHAR(100),  -- numeric ID from Moodle /mod/assign/view.php?id=

    -- Delivery preferences
    delivery_method   deliverymethod,   -- ENUM: download, lms_upload, email
    delivery_email    VARCHAR(255),
    review_type       reviewtype,       -- ENUM: agent_only, agent_professor

    -- Pipeline state
    status            assignmentstatus, -- ENUM: pending, researching, writing, qa_check, prof_review, completed, failed
    n8n_execution_id  VARCHAR(255),     -- legacy; not used in v2.5
    pipeline_log      JSONB DEFAULT '[]', -- array of {stage, status, data, ts} entries

    -- Output
    docx_path         TEXT,            -- local path: /tmp/asa-outputs/<name>_<id>.docx
    docx_s3_key       TEXT,            -- S3 key when uploaded
    plagiarism_score  VARCHAR(20),     -- "12%" or "low risk"
    quality_score     INTEGER,         -- 0-100

    created_at        TIMESTAMP DEFAULT now(),
    updated_at        TIMESTAMP DEFAULT now()
);
```

### 4.5 assignment_submissions

```sql
CREATE TABLE assignment_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id   UUID REFERENCES assignments(id),
    content_md      TEXT,               -- Raw markdown from writing agent
    content_docx    TEXT,               -- S3 key of DOCX
    word_count      INTEGER,
    sources_used    JSONB DEFAULT '[]', -- Array of paper objects used
    professor_notes TEXT,               -- Notes from optional professor review
    revision_count  INTEGER DEFAULT 0,
    submitted_at    TIMESTAMP DEFAULT now()
);
```

### 4.6 deliveries

```sql
CREATE TABLE deliveries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id   UUID REFERENCES assignments(id),
    method          deliverymethod,     -- download, lms_upload, email
    destination     TEXT,               -- email address or LMS URL
    delivered_at    TIMESTAMP,
    success         BOOLEAN DEFAULT false,
    error_message   TEXT
);
```

### 4.7 research_sources

```sql
CREATE TABLE research_sources (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title         TEXT NOT NULL,
    authors       JSONB DEFAULT '[]',  -- ["Last, F.", "Last, F."]
    journal       VARCHAR(500),
    doi           VARCHAR(255) UNIQUE,
    url           TEXT,
    abstract      TEXT,
    year          INTEGER,
    citation_apa  TEXT,                -- pre-formatted APA 7th citation string
    topics        JSONB DEFAULT '[]',  -- ["machine learning", "data science"]
    methods       JSONB DEFAULT '[]',  -- ["regression", "neural network"]
    full_text     TEXT,                -- extracted PDF text (via PyMuPDF)
    created_at    TIMESTAMP DEFAULT now()
);
```

### 4.8 research_embeddings

```sql
CREATE TABLE research_embeddings (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id      UUID REFERENCES research_sources(id),
    chunk_text    TEXT NOT NULL,        -- 600-token chunk of paper content
    chunk_index   INTEGER,             -- 0, 1, 2, ... with 20% overlap
    embedding     VECTOR(1536),        -- text-embedding-3-large / DeepSeek embedding
    metadata      JSONB DEFAULT '{}',  -- {section: "introduction", source_agent: "arxiv"}
    created_at    TIMESTAMP DEFAULT now()
);

-- ANN index for cosine similarity search
CREATE INDEX ON research_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 4.9 kg_nodes

```sql
CREATE TABLE kg_nodes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   UUID REFERENCES research_sources(id),  -- nullable for non-paper nodes
    node_type   VARCHAR(50),    -- Paper, Author, Journal, Topic, Method, AccessMethod, Institution
    name        TEXT NOT NULL,  -- paper title / author name / journal name etc.
    properties  JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT now()
);
```

### 4.10 kg_edges

```sql
CREATE TABLE kg_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id  UUID REFERENCES kg_nodes(id),
    target_node_id  UUID REFERENCES kg_nodes(id),
    edge_type       VARCHAR(100),  -- WRITTEN_BY, PUBLISHED_IN, STUDIES, USES_METHOD, CITES, ACCESSIBLE_VIA
    weight          FLOAT DEFAULT 1.0,
    properties      JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT now()
);
```

### 4.11 subscriptions

```sql
CREATE TABLE subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID UNIQUE REFERENCES users(id),
    plan                    planenum,   -- ENUM: starter, professional, agentic_pro, enterprise
    stripe_sub_id           VARCHAR(255),
    paypal_sub_id           VARCHAR(255),
    status                  VARCHAR(50) DEFAULT 'active',  -- active, cancelled, past_due
    current_period_start    TIMESTAMP,
    current_period_end      TIMESTAMP,
    cancel_at_period_end    BOOLEAN DEFAULT false,
    created_at              TIMESTAMP DEFAULT now(),
    updated_at              TIMESTAMP DEFAULT now()
);
```

### 4.12 orders

```sql
CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    assignment_id   UUID REFERENCES assignments(id),
    amount          NUMERIC(10,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'USD',
    description     TEXT,
    review_type     reviewtypeenum,     -- agent_only, agent_professor
    professor_fee   NUMERIC(10,2) DEFAULT 0,
    status          orderstatus,        -- ENUM: pending, paid, refunded, failed
    stripe_pi_id    VARCHAR(255),       -- Stripe Payment Intent ID
    paypal_order_id VARCHAR(255),       -- PayPal order ID
    paid_at         TIMESTAMP,
    created_at      TIMESTAMP DEFAULT now()
);
```

### 4.13 dom_graphs

```sql
CREATE TABLE dom_graphs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site        VARCHAR(100) NOT NULL,  -- 'moodle', 'canvas', 'blackboard'
    lms_url     TEXT,
    page_type   VARCHAR(100),           -- 'assignment_edit', 'course_view'
    scraped_at  TIMESTAMP DEFAULT now(),
    metadata    JSONB DEFAULT '{}'
);
```

### 4.14 dom_selectors

```sql
CREATE TABLE dom_selectors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_id        UUID REFERENCES dom_graphs(id),
    key             VARCHAR(100),   -- 'username', 'password', 'login_btn', 'file_input'
    selector        TEXT,           -- '#username', 'input[name=password]', etc.
    selector_type   VARCHAR(30),    -- 'css', 'xpath', 'text'
    fallbacks       JSONB DEFAULT '[]',
    last_verified   TIMESTAMP
);
```

### ENUMs

```sql
CREATE TYPE academiclevel    AS ENUM ('high_school', 'undergraduate', 'postgraduate', 'phd');
CREATE TYPE deliverymethod   AS ENUM ('download', 'lms_upload', 'email');
CREATE TYPE reviewtype       AS ENUM ('agent_only', 'agent_professor');
CREATE TYPE reviewtypeenum   AS ENUM ('agent_only', 'agent_professor');
CREATE TYPE assignmentstatus AS ENUM ('pending', 'researching', 'writing', 'qa_check', 'prof_review', 'completed', 'failed');
CREATE TYPE planenum         AS ENUM ('starter', 'professional', 'agentic_pro', 'enterprise');
CREATE TYPE orderstatus      AS ENUM ('pending', 'paid', 'refunded', 'failed');
```

---

## 5. API Layer (FastAPI)

### Application Setup (`api/main.py`)

```python
app = FastAPI(title="ASA v2 - Agentic Scholar Assistant", version="2.0.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://app.scholarassistant.ai"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Router registration — all prefixed with /api/v1
app.include_router(auth_router,        prefix="/api/v1")   # /api/v1/auth/*
app.include_router(assignments_router, prefix="/api/v1")   # /api/v1/assignments/*
app.include_router(billing_router,     prefix="/api/v1")   # /api/v1/billing/*
app.include_router(research_router,    prefix="/api/v1")   # /api/v1/research/*
app.include_router(webhook_router,     prefix="/api/v1")   # /api/v1/webhook/*

@app.on_event("startup")
async def startup():
    create_all_tables()   # calls Base.metadata.create_all(bind=engine)

@app.get("/health")
def health(): return {"status": "ok", "service": "ASA v2 API"}
```

### Complete API Endpoint Catalogue

#### Auth (`/api/v1/auth`)

| Method | Path | Auth | Request Body | Response | Description |
|---|---|---|---|---|---|
| POST | `/auth/register` | None | `{email, password, full_name, academic_level?, institution?}` | `UserOut` 201 | Register new user; creates wallet |
| POST | `/auth/login` | None | `{email, password}` | `{access_token, refresh_token, token_type}` | Returns JWT pair |
| POST | `/auth/refresh` | None | `{refresh_token}` | `{access_token, refresh_token}` | Rotate tokens |
| GET | `/auth/me` | Bearer | — | `UserOut` | Current user info |

#### Assignments (`/api/v1/assignments`)

| Method | Path | Auth | Request Body | Response | Description |
|---|---|---|---|---|---|
| POST | `/assignments` | Bearer | `AssignmentCreate` | `AssignmentOut` 201 | Create assignment, fires pipeline |
| GET | `/assignments` | Bearer | — | `[AssignmentOut]` | List user's assignments |
| GET | `/assignments/{id}` | Bearer | — | `AssignmentOut` | Get one assignment |
| GET | `/assignments/{id}/status` | Bearer | — | `AssignmentStatusOut` | Pipeline status + log |
| GET | `/assignments/{id}/download` | Bearer | — | File (DOCX) | Download completed DOCX |

**AssignmentCreate schema:**
```python
class AssignmentCreate(BaseModel):
    title:            str
    module_code:      Optional[str] = None
    topic:            str
    instructions:     Optional[str] = None
    focus_area:       Optional[str] = None     # e.g. "focus specifically on insurance sector"
    word_count:       int = 2000
    academic_level:   str = "undergraduate"    # high_school|undergraduate|postgraduate|phd
    deadline:         Optional[datetime] = None
    citation_style:   str = "Harvard"          # Harvard|APA|MLA|Chicago

    # LMS credentials (only needed for lms_upload delivery)
    lms_url:          Optional[str] = None     # e.g. "https://vle-uel.unicaf.org"
    lms_username:     Optional[str] = None     # e.g. "user17076418"
    lms_password:     Optional[str] = None     # plaintext — encrypted to lms_password_enc in DB
    lms_assignment_id: Optional[str] = None   # Moodle assign id (numeric)

    delivery_method:  DeliveryMethodEnum = "download"  # download|lms_upload|email
    delivery_email:   Optional[EmailStr] = None
    review_type:      ReviewTypeEnum = "agent_only"     # agent_only|agent_professor
```

#### Billing (`/api/v1/billing`)

| Method | Path | Auth | Request Body | Response | Description |
|---|---|---|---|---|---|
| GET | `/billing/pricing` | None | — | pricing dict | Returns plans + addons |
| POST | `/billing/checkout/stripe` | Bearer | `{assignment_id?, review_type}` | `{checkout_url, order_id, amount}` | Create Stripe Checkout Session |
| POST | `/billing/checkout/paypal` | Bearer | `{assignment_id?, review_type}` | `{checkout_url, order_id, amount}` | Create PayPal order |
| POST | `/billing/webhook/stripe` | Stripe-Signature | raw bytes | `{status: ok}` | Stripe webhook handler |
| GET | `/billing/orders` | Bearer | — | `[{id, amount, status, description}]` | List user orders |

**Pricing tiers:**
```
Starter:       $199/mo — High School,    12–15 assignments, 800–1200 words
Professional:  $299/mo — Undergraduate, 16–20 assignments, 1500–3000 words
Agentic Pro:   $399/mo — Postgraduate,   4–8 assignments,  5000–10000 words
Enterprise:    Custom  — PhD/Research,   1–2 chapters,     10000+ words
Add-on: Professor Review +$20 per assignment
```

#### Research (`/api/v1/research`)

| Method | Path | Auth | Request Body | Response | Description |
|---|---|---|---|---|---|
| POST | `/research/search` | Bearer | `{query, limit?}` | `[{title, abstract, doi, year, authors}]` | Semantic search over stored papers |

#### Webhook (`/api/v1/webhook`)

| Method | Path | Auth | Request Body | Description |
|---|---|---|---|---|
| POST | `/webhook/n8n/status` | X-N8N-SECRET header | `{assignment_id, stage, status, result}` | Pipeline status callback (used in v2) |

---

## 6. Authentication System

**Token type**: JWT (HS256)
**Access token lifetime**: 60 minutes
**Refresh token lifetime**: 30 days

### Token payload structure

```python
# Access token
{"sub": "<user_uuid>", "exp": <unix_timestamp>, "type": "access"}

# Refresh token
{"sub": "<user_uuid>", "exp": <unix_timestamp>, "type": "refresh"}
```

### Password hashing

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# bcrypt==4.0.1 required (passlib 1.7.4 is incompatible with bcrypt 5.x)
hash = pwd_context.hash(password)
verified = pwd_context.verify(plain_password, hash)
```

### LMS password encryption

```python
from cryptography.fernet import Fernet
# WARNING: in production, load key from env/secrets manager
_FERNET_KEY = Fernet.generate_key()  # must persist across restarts
_fernet = Fernet(_FERNET_KEY)

encrypted = _fernet.encrypt(lms_password.encode()).decode()
decrypted = _fernet.decrypt(encrypted.encode()).decode()
```

> **Production note**: Store `FERNET_KEY` in `.env` — not generated at startup. If generated
> at startup, encrypted passwords cannot be decrypted after a restart.

### Authorization pattern in routes

```python
def current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    try:
        return get_current_user(token, db)   # raises ValueError on invalid token
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

---

## 7. Assignment Pipeline — 13 Stages

The pipeline is in `orchestrator/pipeline.py`. It is a pure Python async function — no n8n,
no Celery. It runs in a `threading.Thread` (daemon) spawned by the assignments route so the
HTTP response is returned immediately.

### Launch pattern (assignments route)

```python
import threading
t = threading.Thread(
    target=_run_pipeline_bg,
    args=(str(assignment.id), lms_password),
    daemon=True
)
t.start()
```

Inside `_run_pipeline_bg`:
```python
result = asyncio.run(run_pipeline(job))
```

### Stage 1: Assignment Analysis Agent (`orchestrator/analysis_agent.py`)

**Input**: title, topic, instructions, focus_area, word_count, academic_level, citation_style, module_code

**Logic**:
1. Calls DeepSeek `deepseek-chat` with structured prompt asking to extract:
   - `keywords`: list of 5–10 search terms
   - `methodology`: qualitative / quantitative / mixed / theoretical
   - `required_sources`: integer (e.g. 15 for 2000 words)
   - `region_focus`: geographic region if mentioned ("Kenya", "EU", "global")
   - `time_range`: publication year range (e.g. "2015-2024")
   - `academic_scope`: level of analysis depth
2. Falls back to heuristic extraction if DeepSeek returns malformed JSON

**Output dict**:
```python
{
    "keywords": ["data science", "insurance", "machine learning"],
    "methodology": "quantitative",
    "required_sources": 15,
    "region_focus": "global",
    "time_range": "2015-2024",
    "academic_scope": "postgraduate",
    "citation_style": "Harvard",
    "word_count": 2000,
}
```

### Stage 2: Query Expansion Engine (`orchestrator/query_expansion.py`)

**Input**: analysis dict from Stage 1

**Generates 6 query types**:
```python
queries = {
    "keyword_queries": [
        "data science research methods",
        "machine learning insurance applications",
        ...
    ],
    "boolean_queries": [
        'TITLE-ABS-KEY("data science" AND "insurance" AND "machine learning")',
        ...
    ],
    "author_queries": [...],      # if specific authors mentioned
    "journal_queries": [...],     # relevant journals
    "dataset_queries": [...],     # if data sources mentioned
    "oa_queries": [...],          # open-access versions
    "all_queries": [...],         # union of all above
}
```

### Stage 3: Parallel Research (`agents/research/`)

**Runs two agents concurrently via `asyncio.gather()`**:

#### Web Agent (`web_agent.py`)

Runs 4 sources concurrently:
```python
results = await asyncio.gather(
    _perplexity_search(queries),     # sonar-pro API, return_citations: true
    _crossref_search(queries),       # api.crossref.org/works (free)
    _arxiv_search(queries),          # export.arxiv.org/api/query (free, Atom XML)
    _doaj_search(queries),           # doaj.org/api/search/articles (free)
    return_exceptions=True
)
```

**Paper object schema** (standardised across all sources):
```python
{
    "title":        str,
    "authors":      [str],          # ["Smith, J.", "Doe, A."]
    "journal":      str,
    "doi":          str | None,
    "url":          str,
    "abstract":     str,
    "year":         int | None,
    "source_agent": str,            # "perplexity" | "crossref" | "arxiv" | "doaj"
    "access_method": str | None,    # set by classifier in Stage 5
}
```

**Mock fallback**: when no API keys are set, returns 3 dummy papers so the pipeline can run
end-to-end in development without any credentials.

#### Institutional Agent (`institutional_agent.py`)

Runs only if `institutional_credentials` are provided in the job dict. Uses:
- **Scopus**: `TITLE-ABS-KEY(...)` boolean query, returns JSON with `prism:doi`, `prism:coverDate`
- **Springer Nature**: `/meta/v2/json?q=...` API
- **IEEE Xplore**: `/api/v1/search/articles?querytext=...` API
- **CrossRef fallback**: free institution-agnostic search if other keys missing

### Stage 4: Source Normalisation (`agents/research/normalizer.py`)

**Input**: raw papers from Stage 3 (mixed formats from different sources)

**Operations**:
1. Deduplication by normalised title (lowercased, stripped)
2. Standardise all fields to the Paper schema
3. 3-strategy DOI extraction:
   - Strategy 1: direct `doi` field
   - Strategy 2: parse DOI from URL (`/10.xxxx/` pattern)
   - Strategy 3: regex scan of abstract/title + CrossRef lookup
4. APA 7th edition citation formatting:
   ```
   Smith, J., & Doe, A. (2023). Paper title. Journal Name, 15(2), 123–145. https://doi.org/10.xxxx/xxxxx
   ```

### Stage 5: Access Intelligence Classification (`agents/research/access_classifier.py`)

**7-rule priority chain** (evaluated in order):
1. OA domain in URL? (`arxiv.org`, `pubmedcentral.nih.gov`, `doaj.org`, `plos.org`, `mdpi.com`)
   → `OPEN_ACCESS`
2. Author-copy URL pattern? (`.edu/~`, `/papers/`, GitHub, ResearchGate)
   → `AUTHOR_COPY`
3. Institutional domain? (`.ac.uk`, `.edu`, `.uni-`, Scopus/Springer/IEEE agent)
   → `INSTITUTIONAL`
4. Source agent is `perplexity`?
   → `WEB_SOURCE`
5. OA DOI prefix? (`10.1371/` PLoS, `10.3390/` MDPI, `10.1155/` Hindawi, etc.)
   → `OPEN_ACCESS`
6. Has DOI but type unknown?
   → `INSTITUTIONAL` (assume journal access needed)
7. No DOI, no OA indicators?
   → `WEB_SOURCE`

**Also triggers CrossRef DOI lookup** for any paper that has a title but no DOI.

### Stages 6 & 7: Knowledge Graph + Embeddings (parallel, non-fatal)

Both run as `asyncio.create_task()` concurrently. Failures do NOT stop the pipeline.

```python
kg_task  = asyncio.create_task(_stage_knowledge_graph(classified, analysis))
emb_task = asyncio.create_task(_stage_embeddings(classified, assignment_id))
kg_ok, emb_ok = await asyncio.gather(kg_task, emb_task)
```

### Stage 8: Context Builder (`orchestrator/context_builder.py`)

**Input**: classified papers, analysis dict

**Operations**:
1. **Theme grouping**: clusters papers by topic overlap (keyword matching)
2. **Paper scoring**: scores each paper by citation count + recency + source quality
3. **Key papers selection**: top 10 by score
4. **Argument extraction**: finds supporting claims from abstracts
5. **Contradiction detection**: finds papers with opposing findings
6. **Methodology extraction**: lists research methods used across papers
7. **Source formatting**: formats all papers as citation strings for the writing prompt

**Output dict**:
```python
{
    "themes":           ["data governance", "machine learning in insurance", "ethical AI"],
    "key_papers":       [paper_dict, ...],     # top 10 scored papers
    "arguments":        ["Smith (2023) argues that ...", ...],
    "contradictions":   ["While Smith (2023) argues X, Jones (2022) found Y"],
    "methodologies":    ["regression analysis", "qualitative interview", "survey"],
    "formatted_sources": ["Smith, J. (2023). Title. Journal.", ...],  # all papers APA
    "region_focus":     "global",
}
```

### Stage 9: Writing Agent (`agents/writing_agent.py`)

**Model**: `deepseek-reasoner` (deepseek-r1 family)

**Prompt construction**:
```
System: You are an expert academic writer at [academic_level] level.

Write a {word_count}-word essay titled "{title}" on "{topic}".

Focus area: {focus_area}
Citation style: {citation_style}

THEMES identified in the literature:
{themes}

KEY ARGUMENTS from the sources:
{arguments}

CONTRADICTIONS and debates in the literature:
{contradictions}

METHODOLOGIES used in source papers:
{methodologies}

SOURCES (cite these throughout, do not invent references):
{formatted_sources}

Requirements:
- Academic register appropriate for {academic_level}
- {word_count} words ± 10%
- Use {citation_style} in-text citations (Author, Year)
- Include a References section at the end
- DO NOT include a bibliography of sources you did not cite
- Structure: Introduction (10%), Main Body (80%), Conclusion (10%)
```

**`max_tokens`** scales dynamically: `word_count * 1.8` (capped at 8000)

**TONE_PROMPTS** dict:
```python
{
    "human_academic":  "natural, varied-sentence academic prose",
    "professional":    "formal professional register for industry/policy",
    "critical":        "critically analytical, evaluates evidence rigorously",
    "reflective":      "first-person reflective practice style",
}
```

**LEVEL_EXPECTATIONS** dict:
```python
{
    "high_school":    {"min_sources": 5,  "writing_style": "clear and accessible"},
    "undergraduate":  {"min_sources": 10, "writing_style": "analytical and structured"},
    "postgraduate":   {"min_sources": 20, "writing_style": "critical and nuanced"},
    "phd":            {"min_sources": 40, "writing_style": "highly original and scholarly"},
}
```

### Stage 10: QA Agent (`agents/qa_agent.py`)

**3 sub-stages** (with optional Stage 4):

#### Sub-stage A: Plagiarism Detection
1. Primary: Copyleaks API
   - Base64-encode essay text
   - POST to `https://api.copyleaks.com/v3/education/submit/file/{scan_id}`
   - GET results from `https://api.copyleaks.com/v3/downloads/{scan_id}/results`
   - Timeout: 15s submit, 20s result fetch
2. Fallback (no API key or timeout): Jaccard similarity heuristic
   - Split essay into 2-sentence shingles
   - Compare shingles against source abstracts in DB
   - Flag if similarity > 0.60
   - Returns `score: 0, method: "heuristic"` with `low/medium/high risk` label

#### Sub-stage B: Tone Adjustment
1. Count AI-signature phrases:
   - "It is worth noting", "In conclusion,", "Furthermore,", "Moreover,",
     "It should be noted", "Firstly,", "Secondly,", "Lastly,"
2. If count >= 3 and DEEPSEEK_API_KEY set:
   - POST to DeepSeek `deepseek-chat` with prompt to rewrite removing AI patterns
   - Human-academic register
3. If count < 3: skip (no unnecessary API call)
4. Fallback `_basic_phrase_replacement()`: string substitution map

#### Sub-stage C: Citation Validation
1. Regex to find all `(Author, Year)` patterns in essay text
   - Handles: `(Smith, 2023)`, `(Smith & Jones, 2023)`, `(López, 2023)`
2. For each citation, check if a matching reference exists in the References section
3. Returns:
   - `issues`: citations with no reference entry (costs 12 pts each)
   - `warnings`: references with no in-text citation (costs 3 pts each)
   - `quality_score`: `100 - (issues * 12) - (warnings * 3)`

#### Sub-stage D (optional): Section Rewrite
- If `quality_score < 65` AND `ai_phrase_count >= 2`:
  - Extract the Introduction section
  - Rewrite via DeepSeek `deepseek-chat` with target quality criteria
  - Re-run citation validation on new text
  - Update quality_score

### Stage 11: Professor Review Branch (optional)

Triggered when `review_type == "agent_professor"`. In v2.5 this is a **stub**:
- Logs "Professor review queued"
- In production: pauses pipeline, stores essay in DB, notifies professor via email,
  resumes when professor calls `POST /assignments/{id}/approve-review`

### Stage 12: Delivery (`agents/delivery_agent.py`)

#### 1. DOCX Generation (`markdown_to_docx()`)

```
Cover page:
  - Module code (bold, 18pt, centered)
  - Title (14pt, centered)
  - Student name
  - "Generated by ASA v2 — Agentic Scholar Assistant"
  - Page break

Body:
  - ## Heading → Heading 1 (Word style)
  - ### Heading → Heading 2
  - - bullet → List Bullet style
  - ```code``` → Courier New 9pt
  - **bold** text → bold run
  - Normal paragraph → justified, 11pt Calibri

Page margins: 1" top/bottom, 1.25" left/right
```

**Output path**: `{OUTPUT_DIR}/{title_slug}_{assignment_id[:8]}.docx`

#### 2. LMS Upload (Moodle via Playwright)

```javascript
// Proven Moodle repository API approach (bypasses YUI lightbox)
// 1. Navigate to /mod/assign/view.php?id={assignId}&action=editsubmission
// 2. Extract: sesskey, itemid, contextid, clientid from page scripts
// 3. Upload via fetch() inside page.evaluate():
const fd = new FormData();
fd.append('repo_id', '4');            // "Upload a file" repository (NOT 3 = Recent Files)
fd.append('repo_upload_file', blob, fileName);
fd.append('itemid', itemId);
fd.append('sesskey', sesskey);
fd.append('contextid', ctxId);
fd.append('component', 'assignsubmission_file');
fd.append('filearea', 'submission_files');
const r = await fetch('/repository/repository_ajax.php?action=upload', {method:'POST', body:fd});
// 4. Click Save changes (input[name=savechanges])
// 5. Click Submit assignment (input[name=submitbutton])
// 6. Confirm modal (button[data-action="save"] or input[value="Continue"])
```

**Fallback**: try `repo_id=3` if `repo_id=4` fails.

#### 3. Email Delivery

```python
msg = MIMEMultipart()
msg['Subject'] = f"Your assignment: {title}"
msg.attach(MIMEText(body_html, 'html'))
# Attach DOCX
part = MIMEBase('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document')
part.set_payload(open(docx_path, 'rb').read())
encoders.encode_base64(part)
msg.attach(part)
# Send via SMTP TLS
with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
    s.starttls()
    s.login(SMTP_USERNAME, SMTP_PASSWORD)
    s.send_message(msg)
```

### Stage 13: Pipeline Result

```python
{
    "assignment_id":    str,
    "status":           "completed" | "failed",
    "docx_path":        "/tmp/asa-outputs/Title_abc123.docx",
    "plagiarism_score": "12%",
    "quality_score":    82,
    "sources_used":     36,
    "elapsed_seconds":  45.2,
    "stages":           [{stage, status, data, ts}, ...],
    "error":            str | None,
}
```

---

## 8. Research Agents

### Web Agent (`agents/research/web_agent.py`)

**Entry point**: `async def run_web_agent_async(queries: list, query_dict: dict) -> list`

**Perplexity Sonar** (`sonar-pro`):
```python
payload = {
    "model": "sonar-pro",
    "messages": [{"role": "user", "content": f"Find recent academic papers on: {query}"}],
    "return_citations": True,
    "search_domain_filter": ["scholar.google.com", "researchgate.net", "arxiv.org"],
}
r = await client.post("https://api.perplexity.ai/chat/completions", json=payload,
                      headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"})
# Extract citations from r.json()["citations"]
```

**CrossRef** (free, no key):
```
GET https://api.crossref.org/works
  ?query={encoded_query}
  &rows=8
  &select=DOI,title,author,published-print,container-title,abstract,URL
  &filter=type:journal-article
  &mailto=asa@scholarassistant.ai
```

**arXiv** (free, no key):
```
GET https://export.arxiv.org/api/query
  ?search_query=all:{query}
  &max_results=6
  &sortBy=relevance
  &sortOrder=descending
# Response: Atom XML — parse with xml.etree.ElementTree
# Namespace: {http://www.w3.org/2005/Atom}
```

**DOAJ** (free, no key):
```
GET https://doaj.org/api/search/articles
  ?q={query}
  &pageSize=6
# Note: DOAJ API v2 is at /api/v2/search/ — v1 returns 404
```

### Institutional Agent (`agents/research/institutional_agent.py`)

**Entry point**: `async def run_institutional_agent_async(queries: list, credentials: dict) -> list`

**Scopus** (Elsevier):
```python
headers = {"X-ELS-APIKey": SCOPUS_API_KEY, "Accept": "application/json"}
url = "https://api.elsevier.com/content/search/scopus"
params = {
    "query": f'TITLE-ABS-KEY("{keyword1}" AND "{keyword2}")',
    "count": 10,
    "field": "dc:title,dc:creator,prism:publicationName,prism:doi,prism:coverDate,dc:description",
}
```

**Springer Nature**:
```
GET https://api.springernature.com/meta/v2/json
  ?q={query}
  &api_key={SPRINGER_API_KEY}
  &p=10
```

**IEEE Xplore**:
```
GET https://ieeexploreapi.ieee.org/api/v1/search/articles
  ?querytext={query}
  &apikey={IEEE_API_KEY}
  &max_records=10
  &datatype=json
```

---

## 9. Writing Agent

**File**: `agents/writing_agent.py`

**Key functions**:
- `analyze_assignment(...)` → `dict` — legacy; use `orchestrator/analysis_agent.py` in v2.5
- `build_writing_prompt(...)` → `str` — constructs the full system + user prompt
- `call_deepseek(prompt, max_tokens)` → `str` — HTTP POST to DeepSeek API
- `run_writing_pipeline(title, topic, instructions, focus_area, word_count, academic_level, citation_style, sources, context)` → `dict`

**DeepSeek API call**:
```python
payload = {
    "model":       "deepseek-reasoner",
    "messages":    [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}],
    "temperature": 0.7,
    "max_tokens":  min(int(word_count * 1.8), 8000),
}
r = httpx.post(DEEPSEEK_API_URL, json=payload,
               headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
               timeout=120)
return r.json()["choices"][0]["message"]["content"]
```

**Output dict**:
```python
{
    "essay_markdown": str,   # full essay with ## headings, refs section
    "word_count":     int,
    "model_used":     "deepseek-reasoner",
}
```

---

## 10. QA Agent

**File**: `agents/qa_agent.py`

**Entry point**: `run_qa_pipeline(essay_md: str, sources: list, assignment_id: str) -> dict`

**Output dict**:
```python
{
    "essay_markdown": str,        # final (potentially rewritten) essay
    "plagiarism": {
        "score":  float,          # 0-100 (percentage)
        "risk":   str,            # "low" | "medium" | "high"
        "method": str,            # "copyleaks" | "heuristic"
    },
    "tone_adjusted": bool,
    "citations": {
        "found":    int,
        "issues":   [str],        # citations with no reference
        "warnings": [str],        # references with no citation
    },
    "quality_score": int,         # 0-100
    "ai_phrase_count": int,
}
```

---

## 11. Delivery Agent

**File**: `agents/delivery_agent.py`

**Entry point**:
```python
def run_delivery_pipeline(
    essay_md:        str,
    title:           str,
    student_name:    str,
    module_code:     str,
    assignment_id:   str,
    delivery_method: str,     # "download" | "lms_upload" | "email"
    delivery_email:  str,
    lms_url:         str,
    lms_username:    str,
    lms_password:    str,
) -> dict:
```

**Returns**:
```python
{
    "status":    "ready_for_download" | "lms_uploaded" | "emailed" | "failed",
    "docx_path": "/tmp/asa-outputs/...",
    "message":   str,
}
```

---

## 12. Knowledge Graph

**File**: `knowledge_graph/graph_service.py`

### Node types

| Node type | `name` field | `properties` |
|---|---|---|
| Paper | paper title | `{doi, year, abstract, url}` |
| Author | "Last, F." | `{institution, orcid}` |
| Journal | journal name | `{issn, publisher}` |
| Topic | topic keyword | `{frequency}` |
| Method | method name | `{type: "quantitative\|qualitative"}` |
| AccessMethod | "OPEN_ACCESS" etc. | `{url_pattern}` |
| Institution | institution name | `{country}` |

### Edge types

| Edge | Source | Target |
|---|---|---|
| WRITTEN_BY | Paper | Author |
| PUBLISHED_IN | Paper | Journal |
| STUDIES | Paper | Topic |
| USES_METHOD | Paper | Method |
| ACCESSIBLE_VIA | Paper | AccessMethod |
| CITES | Paper | Paper |

### Upsert pattern

```python
async def upsert_research_batch(sources: list, analysis: dict) -> dict:
    """Non-blocking wrapper — runs sync DB work in thread pool."""
    return await asyncio.to_thread(_upsert_research_batch_sync, sources, analysis)

def _upsert_node(db, node_type: str, name: str, source_id=None, properties=None):
    """Find-or-create — grow the graph over time, never duplicate."""
    existing = db.query(KGNode).filter(
        KGNode.node_type == node_type,
        KGNode.name == name
    ).first()
    if existing:
        return existing
    node = KGNode(node_type=node_type, name=name,
                  source_id=source_id, properties=properties or {})
    db.add(node)
    db.flush()
    return node
```

---

## 13. Vector Embeddings

**File**: `embeddings/pipeline.py`

### Chunking strategy

```python
CHUNK_SIZE    = 600     # tokens (~450 words)
CHUNK_OVERLAP = 0.20    # 20% overlap between chunks

def chunk_paper(paper: dict) -> list[dict]:
    """Generate chunks from paper content."""
    # 1. Try full_text (PyMuPDF-extracted PDF text)
    # 2. Fall back to title + abstract
    text = paper.get("full_text") or f"{paper['title']}\n\n{paper.get('abstract', '')}"
    words = text.split()
    stride = int(CHUNK_SIZE * (1 - CHUNK_OVERLAP))
    chunks = []
    for i in range(0, len(words), stride):
        chunk_words = words[i:i + CHUNK_SIZE]
        chunk_text  = " ".join(chunk_words)
        section     = _guess_section(chunk_text, i, len(words))
        chunks.append({"text": chunk_text, "index": len(chunks), "section": section})
    return chunks

def _guess_section(text: str, position: int, total: int) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["introduction", "background", "overview"]): return "introduction"
    if any(w in text_lower for w in ["method", "approach", "design"]):           return "methodology"
    if any(w in text_lower for w in ["result", "finding", "data show"]):         return "results"
    if any(w in text_lower for w in ["conclusion", "summary", "future work"]):   return "conclusion"
    if position < total * 0.15:  return "introduction"
    if position > total * 0.85:  return "conclusion"
    return "body"
```

### Embedding API call

```python
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://api.openai.com/v1/embeddings")
# text-embedding-3-large produces 1536-dim vectors (matches pgvector column)

async def get_embedding_async(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        r = await client.post(EMBEDDING_API_URL,
            json={"model": "text-embedding-3-large", "input": text},
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}, timeout=30)
    return r.json()["data"][0]["embedding"]
```

### Semantic search

```python
async def semantic_search_async(query: str, limit: int = 10) -> list[dict]:
    q_embedding = await get_embedding_async(query)
    # pgvector cosine similarity
    sql = text("""
        SELECT re.chunk_text, rs.title, rs.doi, rs.year, rs.citation_apa,
               1 - (re.embedding <=> :q_emb) AS similarity
        FROM research_embeddings re
        JOIN research_sources rs ON re.paper_id = rs.id
        ORDER BY re.embedding <=> :q_emb
        LIMIT :limit
    """)
    # returns list of {chunk_text, title, doi, year, citation_apa, similarity}
```

---

## 14. Billing System

### Pricing calculation

```python
def calculate_order_amount(plan: str, review_type: str) -> float:
    base = {"starter": 199.0, "professional": 299.0, "agentic_pro": 399.0, "enterprise": 0.0}[plan]
    professor_fee = 20.0 if review_type == "agent_professor" else 0.0
    return round(base + professor_fee, 2)
```

### Stripe Checkout Session

```python
session = stripe.checkout.Session.create(
    payment_method_types=["card"],
    line_items=[{
        "price_data": {
            "currency": "usd",
            "product_data": {"name": f"ASA {plan.title()} — {review_type}"},
            "unit_amount": int(amount * 100),  # Stripe uses cents
        },
        "quantity": 1,
    }],
    mode="payment",
    success_url="https://app.scholarassistant.ai/billing/success?order_id={order.id}",
    cancel_url="https://app.scholarassistant.ai/billing/cancel",
    metadata={"order_id": str(order.id), "user_id": str(user_id)},
)
```

### Stripe Webhook Handler

```python
event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
if event["type"] == "checkout.session.completed":
    order_id = event["data"]["object"]["metadata"]["order_id"]
    order = db.query(Order).filter(Order.id == order_id).first()
    order.status = OrderStatus.paid
    order.paid_at = datetime.utcnow()
    db.commit()
```

### PayPal REST API v2

```python
# Step 1: Get bearer token
POST https://api-m.sandbox.paypal.com/v1/oauth2/token
Authorization: Basic base64(CLIENT_ID:CLIENT_SECRET)
Body: grant_type=client_credentials

# Step 2: Create order
POST https://api-m.sandbox.paypal.com/v2/checkout/orders
{
    "intent": "CAPTURE",
    "purchase_units": [{"amount": {"currency_code": "USD", "value": "299.00"}}],
    "application_context": {
        "return_url": "https://app.scholarassistant.ai/billing/success",
        "cancel_url": "https://app.scholarassistant.ai/billing/cancel"
    }
}
# Response: links[rel="approve"].href → redirect student here
```

---

## 15. LMS Submission Agent

The LMS agent uses **Node.js Playwright** (not Python Playwright) for LMS interaction.
This is because the scholar-agent directory has its own `node_modules/` with playwright installed.

**Location**: `/home/dbm/AssignmentOnline/scholar-agent/`

### Login pattern (works on Moodle)

```javascript
await page.goto(`${LMS_URL}/login/index.php`, {waitUntil: 'domcontentloaded'});
await page.fill('#username', USERNAME);
await page.fill('#password', PASSWORD);
await page.click('#loginbtn');
await page.waitForTimeout(3000);
```

### File upload pattern (repo_id=4, bypasses YUI lightbox)

**Key insight**: Do NOT interact with Moodle's UI file picker (it has a YUI lightbox that blocks
clicks). Instead, call the internal Moodle repository API directly via `fetch()` inside
`page.evaluate()` — this inherits the session cookies automatically.

```javascript
const fileBase64 = fs.readFileSync(docxPath).toString('base64');
const uploadResult = await page.evaluate(async ({base64, fileName, sesskey, itemId, ctxId, clientId}) => {
    const bytes = new Uint8Array(atob(base64).split('').map(c => c.charCodeAt(0)));
    const blob  = new Blob([bytes], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    });
    const fd = new FormData();
    fd.append('repo_id',          '4');         // IMPORTANT: 4 = "Upload a file"; 3 = "Recent Files" (fails)
    fd.append('repo_upload_file', blob, fileName);
    fd.append('itemid',           itemId);
    fd.append('author',           'Student Name');
    fd.append('sesskey',          sesskey);
    fd.append('contextid',        ctxId);
    fd.append('component',        'assignsubmission_file');
    fd.append('filearea',         'submission_files');
    fd.append('clientid',         clientId || '');
    fd.append('savepath',         '/');
    const r = await fetch('/repository/repository_ajax.php?action=upload', {method: 'POST', body: fd});
    return {status: r.status, body: await r.text()};
}, {base64: fileBase64, fileName, sesskey, itemId, ctxId, clientId});
```

### Context data extraction (sesskey, itemId, ctxId, clientId)

```javascript
const ctx = await page.evaluate(() => {
    const scripts = Array.from(document.querySelectorAll('script'));
    let c = {sesskey: null, itemId: null, ctxId: null, clientId: null};
    for (const s of scripts) {
        let m;
        m = s.textContent.match(/"clientid"\s*:\s*"([^"]+)"/);  if (m && !c.clientId) c.clientId = m[1];
        m = s.textContent.match(/"itemid"\s*:\s*(\d+)/);         if (m && !c.itemId)   c.itemId   = m[1];
        m = s.textContent.match(/"contextid"\s*:\s*(\d+)/);      if (m && !c.ctxId)    c.ctxId    = m[1];
    }
    const sk = document.querySelector('input[name=sesskey]');
    if (sk) c.sesskey = sk.value;
    return c;
});
```

### Submit assignment (after upload)

```javascript
// 1. Click Save changes
await page.evaluate(() => {
    document.querySelector('input[name=savechanges]').click();
});
await page.waitForLoadState('domcontentloaded');
await page.waitForTimeout(3000);

// 2. Click "Submit assignment" button (on the view page)
await page.evaluate(() => {
    const btn = document.querySelector('input[name=submitbutton]');
    if (btn) btn.click();
});

// 3. Confirm modal
await page.evaluate(() => {
    const btn = document.querySelector('button[data-action="save"], input[value="Continue"]');
    if (btn) btn.click();
    window.confirm = () => true;  // auto-confirm any JS dialogs
});
```

### Moodle assignment URL structure

```
View:   https://<lms>/mod/assign/view.php?id=<assignId>
Edit:   https://<lms>/mod/assign/view.php?id=<assignId>&action=editsubmission
Submit: https://<lms>/mod/assign/view.php?id=<assignId>&action=submit
```

### Finding assignment IDs

Assignment IDs are specific to each course enrolment. Strategy:
1. Navigate to `/my/` — check timeline for upcoming deadlines
2. Use AJAX: `POST /lib/ajax/service.php` with `core_course_get_enrolled_courses_by_timeline_classification`
3. Navigate to known course `/course/view.php?id=<courseId>` — scrape `a[href*="/mod/assign/view"]`
4. Brute-force adjacent IDs (usually sequential per course section)

---

## 16. Frontend (Next.js)

**Port**: 4000 (dev: `next dev -p 4000`)
**Framework**: Next.js 14 App Router, TypeScript, Tailwind CSS

### Pages

| Route | File | Description |
|---|---|---|
| `/auth/login` | `app/auth/login/page.tsx` | Email/password login form |
| `/auth/register` | `app/auth/register/page.tsx` | Registration form |
| `/dashboard` | `app/dashboard/page.tsx` | Assignment list + status cards |
| `/assignments/new` | `app/assignments/new/page.tsx` | 4-step assignment creation wizard |
| `/billing` | `app/billing/page.tsx` | Plan selection, Stripe/PayPal checkout |

### 4-Step Assignment Wizard (`app/assignments/new/page.tsx`)

**Step 1 — Assignment Details**:
- `title` (text input)
- `module_code` (text input, e.g. "DS 7001")
- `topic` (text area)
- `instructions` (text area)
- `word_count` (number, default 2000)
- `deadline` (date picker, optional)

**Step 2 — Research Focus**:
- `focus_area` (text area)
  - Helper text: "Optionally specify a focus — e.g. 'focus specifically on insurance sector'"
- `academic_level` (select: High School / Undergraduate / Postgraduate / PhD)
- `citation_style` (select: Harvard / APA / MLA / Chicago)

**Step 3 — LMS & Delivery**:
- `delivery_method` (radio: Download / LMS Upload / Email)
- If `lms_upload` selected, show:
  - `lms_url` (text input, e.g. "https://vle-uel.unicaf.org")
  - `lms_username` (text input)
  - `lms_password` (password input)
  - `lms_assignment_id` (text input, optional — numeric Moodle ID)
- If `email` selected, show `delivery_email`

**Step 4 — Review & Payment**:
- `review_type` radio:
  - "AI Agent Only" (default)
  - "AI Agent + Professor Review" (+$20 badge)
- Summary of order
- CTA buttons: "Pay with Stripe" / "Pay with PayPal"

### API client (`frontend/lib/api.ts`)

```typescript
const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1',
    headers: {'Content-Type': 'application/json'},
});

// JWT auto-refresh interceptor
api.interceptors.response.use(
    r => r,
    async error => {
        if (error.response?.status === 401 && !error.config._retry) {
            error.config._retry = true;
            const refreshToken = localStorage.getItem('refresh_token');
            const {data} = await api.post('/auth/refresh', {refresh_token: refreshToken});
            localStorage.setItem('access_token', data.access_token);
            error.config.headers['Authorization'] = `Bearer ${data.access_token}`;
            return api(error.config);
        }
        return Promise.reject(error);
    }
);
```

---

## 17. Infrastructure & Deployment

### Docker Compose (`infrastructure/docker/docker-compose.yml`)

**5 services**:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16       # PostgreSQL 16 with pgvector extension
    environment:
      POSTGRES_USER: asa
      POSTGRES_PASSWORD: asa_secure_password
      POSTGRES_DB: asa_platform
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  api:
    build:
      context: ../../
      dockerfile: api/Dockerfile
    env_file: ../../.env
    depends_on: [postgres, redis]
    environment:
      DATABASE_URL: postgresql+psycopg2://asa:asa_secure_password@postgres:5432/asa_platform
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ../../frontend
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: http://api:8000/api/v1
    ports:
      - "4000:4000"

  nginx:
    image: nginx:alpine
    volumes:
      - ../configs/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on: [api, frontend]
```

### Nginx (`infrastructure/configs/nginx.conf`)

```nginx
events { worker_connections 1024; }

http {
  # Student Portal
  server {
    listen 80;
    server_name app.scholarassistant.ai localhost;

    location / {
      proxy_pass       http://frontend:4000;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
      proxy_pass         http://api:8000;
      proxy_set_header   Host $host;
      proxy_read_timeout 120s;           # pipeline can take up to 2 minutes
    }

    location /ws/ {
      proxy_pass         http://api:8000;
      proxy_http_version 1.1;
      proxy_set_header   Upgrade $http_upgrade;
      proxy_set_header   Connection "upgrade";
    }
  }
}
```

### API Dockerfile (`api/Dockerfile`)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install playwright && playwright install chromium --with-deps
COPY api /app/api
COPY agents /app/agents
COPY orchestrator /app/orchestrator
COPY embeddings /app/embeddings
COPY knowledge_graph /app/knowledge_graph
ENV PYTHONPATH=/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile (`frontend/Dockerfile`)

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build         # output: .next/standalone

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 4000
CMD ["node", "server.js"]
```

### Native (non-Docker) setup

```bash
# Prerequisites: PostgreSQL 16, Redis 7, Node.js 20, Python 3.11+

# 1. Create database
sudo -u postgres psql -c "CREATE USER asa WITH PASSWORD 'asa';"
sudo -u postgres createdb -O asa asa_platform
sudo -u postgres psql -d asa_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 2. Install Python deps
python3 -m venv venv
source venv/bin/activate
pip install -r api/requirements.txt
pip install playwright
playwright install chromium

# 3. Create .env from .env.example
cp .env.example .env   # fill in real values

# 4. Start API (port 8001 to avoid conflict)
DATABASE_URL=postgresql+psycopg2://asa:asa@127.0.0.1:5432/asa_platform \
REDIS_URL=redis://localhost:6379/1 \
SECRET_KEY=your-long-secret-key \
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload &> /tmp/asa-api.log &

# 5. Start frontend
cd frontend
npm install
npm run dev   # starts on port 4000
```

---

## 18. Environment Variables

```bash
# ── App ──────────────────────────────────────────────────────────────────────
SECRET_KEY=changeme-use-a-very-long-random-string-here   # JWT signing key
DEBUG=false

# ── Database ─────────────────────────────────────────────────────────────────
POSTGRES_USER=asa
POSTGRES_PASSWORD=asa_secure_password
POSTGRES_DB=asa_platform
DATABASE_URL=postgresql+psycopg2://asa:asa_secure_password@localhost:5432/asa_platform

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── AI APIs ──────────────────────────────────────────────────────────────────
PERPLEXITY_API_KEY=pplx-xxxxxxxx       # https://perplexity.ai — sonar-pro model
DEEPSEEK_API_KEY=sk-xxxxxxxx           # https://platform.deepseek.com
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions

# ── Institutional Research APIs (optional — enables Scopus/Springer/IEEE) ──────
SCOPUS_API_KEY=xxxxxxxx                # https://dev.elsevier.com
SPRINGER_API_KEY=xxxxxxxx             # https://dev.springernature.com
IEEE_API_KEY=xxxxxxxx                 # https://developer.ieee.org

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_API_URL=https://api.openai.com/v1/embeddings
OPENAI_API_KEY=sk-xxxxxxxx            # for text-embedding-3-large

# ── Plagiarism ────────────────────────────────────────────────────────────────
COPYLEAKS_EMAIL=your@email.com
COPYLEAKS_API_KEY=xxxxxxxx

# ── Payments ──────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_test_xxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxx  # from Stripe Dashboard > Webhooks
PAYPAL_CLIENT_ID=xxxxxxxx
PAYPAL_CLIENT_SECRET=xxxxxxxx
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com   # change to live for production

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your_app_password        # Google App Password (not account password)

# ── File Storage ──────────────────────────────────────────────────────────────
OUTPUT_DIR=/tmp/asa-outputs            # local DOCX output directory
S3_ENDPOINT=                           # leave empty for local; set for MinIO/S3
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=asa-documents

# ── LMS encryption key (CRITICAL — must persist across restarts) ────────────
# Generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=your-base64-fernet-key-here
```

---

## 19. Data Flow — End to End

```
Student fills 4-step wizard
        │
        ▼
POST /api/v1/assignments  (FastAPI)
   │  → create_assignment() — encrypts lms_password, stores in DB
   │  → spawns daemon Thread with _run_pipeline_bg()
   └→ returns {id, status: "researching"} in < 100ms

         Thread: asyncio.run(run_pipeline(job))
                 │
                 ├─ Stage 1: analysis_agent.py ──────── DeepSeek (deepseek-chat)
                 │  → {keywords, methodology, required_sources, region_focus}
                 │
                 ├─ Stage 2: query_expansion.py ──────── local (no API)
                 │  → {keyword_queries, boolean_queries, all_queries}
                 │
                 ├─ Stage 3: asyncio.gather() ─────────── PARALLEL
                 │  ├─ web_agent.py
                 │  │   ├─ Perplexity sonar-pro
                 │  │   ├─ CrossRef (api.crossref.org)
                 │  │   ├─ arXiv (export.arxiv.org)
                 │  │   └─ DOAJ (doaj.org)
                 │  └─ institutional_agent.py (if creds provided)
                 │      ├─ Scopus (api.elsevier.com)
                 │      ├─ Springer (api.springernature.com)
                 │      └─ IEEE Xplore (ieeexploreapi.ieee.org)
                 │  → merged + deduplicated by DOI: ~30–50 papers
                 │
                 ├─ Stage 4: normalizer.py ───────────── local + CrossRef (DOI lookup)
                 │  → standardised Paper objects, APA citations
                 │
                 ├─ Stage 5: access_classifier.py ────── local + CrossRef
                 │  → OPEN_ACCESS / INSTITUTIONAL / AUTHOR_COPY / WEB_SOURCE
                 │
                 ├─ Stages 6+7: asyncio.gather() ──────── PARALLEL (non-fatal)
                 │  ├─ knowledge_graph/graph_service.py ── PostgreSQL
                 │  └─ embeddings/pipeline.py ─────────── pgvector + OpenAI embeddings
                 │
                 ├─ Stage 8: context_builder.py ──────── local
                 │  → {themes, key_papers, arguments, contradictions}
                 │
                 ├─ Stage 9: writing_agent.py ────────── DeepSeek (deepseek-reasoner)
                 │  → 2000-word essay in markdown, harvard citations
                 │
                 ├─ Stage 10: qa_agent.py ────────────── Copyleaks + DeepSeek (chat)
                 │  → plagiarism check + tone rewrite + citation validation
                 │
                 ├─ Stage 11: professor review (stub) ── DB + email (future)
                 │
                 └─ Stage 12: delivery_agent.py
                     ├─ markdown_to_docx() → /tmp/asa-outputs/*.docx
                     ├─ [if lms_upload] → Playwright → Moodle repo API upload
                     └─ [if email] → aiosmtplib SMTP

         DB update: assignment.status = completed, docx_path = /tmp/...

Student polls GET /api/v1/assignments/{id}/status
   → status: "completed", docx_path: "/tmp/asa-outputs/..."

Student downloads GET /api/v1/assignments/{id}/download
   → FileResponse (DOCX binary)
```

---

## 20. Replication Checklist

To build a new instance of this system:

### Infrastructure
- [ ] PostgreSQL 16 server with `pgvector` extension installed
  - Ubuntu: `apt install postgresql-16-pgvector`
- [ ] Redis 7 server
- [ ] Node.js 20 (for Playwright LMS agent)
- [ ] Python 3.11+ with venv
- [ ] playwright install chromium (both npm and pip versions)

### Database
- [ ] Create user `asa` with password
- [ ] Create database `asa_platform` owned by `asa`
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] Run `create_all_tables()` (automatic on API startup)

### Code structure
- [ ] `/api/` — FastAPI application (models, routes, services, schemas)
- [ ] `/orchestrator/` — pipeline.py + analysis_agent + query_expansion + context_builder
- [ ] `/agents/research/` — web_agent, institutional_agent, normalizer, access_classifier
- [ ] `/agents/` — writing_agent, qa_agent, delivery_agent, scraping_agent
- [ ] `/embeddings/` — pipeline.py (chunking + pgvector)
- [ ] `/knowledge_graph/` — graph_service.py
- [ ] `/frontend/` — Next.js 14 app

### API keys (minimum to run with mock fallbacks)
- [ ] `DEEPSEEK_API_KEY` — for writing (required for real essays)
- [ ] `PERPLEXITY_API_KEY` — for web research (has mock fallback)
- [ ] `SECRET_KEY` — long random string for JWT signing (required)

### API keys (optional enhancements)
- [ ] `SCOPUS_API_KEY`, `SPRINGER_API_KEY`, `IEEE_API_KEY` — institutional research
- [ ] `COPYLEAKS_EMAIL` + `COPYLEAKS_API_KEY` — plagiarism (Jaccard fallback available)
- [ ] `OPENAI_API_KEY` — semantic embeddings (optional, KG/embeddings stages non-fatal)
- [ ] `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` — payments
- [ ] `PAYPAL_CLIENT_ID` + `PAYPAL_CLIENT_SECRET` — PayPal payments
- [ ] `SMTP_USERNAME` + `SMTP_PASSWORD` — email delivery
- [ ] `FERNET_KEY` — LMS password encryption (generate once, store permanently)

### Deployment
- [ ] Copy `.env.example` to `.env` and fill all values
- [ ] Build and start with `docker compose up -d` (Docker path)
- [ ] Or start natively: uvicorn + npm run dev

### Test the pipeline
```bash
# 1. Register
curl -X POST http://localhost:8001/api/v1/auth/register \
  -d '{"email":"test@test.com","password":"Test1234","full_name":"Test User","academic_level":"undergraduate"}'

# 2. Login
curl -X POST http://localhost:8001/api/v1/auth/login \
  -d '{"email":"test@test.com","password":"Test1234"}'

# 3. Create assignment (pipeline fires immediately)
curl -X POST http://localhost:8001/api/v1/assignments \
  -H "Authorization: Bearer <token>" \
  -d '{"title":"Test Essay","topic":"Machine Learning","word_count":500,"delivery_method":"download"}'

# 4. Poll status
curl http://localhost:8001/api/v1/assignments/<id>/status \
  -H "Authorization: Bearer <token>"

# 5. Download DOCX when status == "completed"
curl http://localhost:8001/api/v1/assignments/<id>/download \
  -H "Authorization: Bearer <token>" -o essay.docx
```

---

*Document generated by Claude Sonnet 4.6 — ASA v2.5 architecture as of 2026-03-10*
*GitHub: https://github.com/derrickbotha/version-1/tree/v.03*
