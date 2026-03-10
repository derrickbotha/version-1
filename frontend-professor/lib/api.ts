const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

function authHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('prof_token') : ''
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: authHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.message || err.detail || 'Request failed')
  }
  const json = await res.json()
  // Unwrap backend envelope: { status: "success", data: {...} }
  return (json && json.data !== undefined ? json.data : json) as T
}

export const api = {
  // Auth
  login: async (email: string, password: string): Promise<{ access_token: string; user: ProfUser }> => {
    const data = await request<{ access_token: string; refresh_token: string }>('POST', '/auth/login', { email, password })
    // Temporarily store token to allow /auth/me call
    if (typeof window !== 'undefined') localStorage.setItem('prof_token', data.access_token)
    const user = await request<ProfUser>('GET', '/auth/me')
    return { access_token: data.access_token, user }
  },
  me: () => request<ProfUser>('GET', '/auth/me'),

  // Professor profile
  getProfile: () => request<ProfProfile>('GET', '/professor/profile'),
  createProfile: (data: Partial<ProfProfile>) => request<ProfProfile>('POST', '/professor/profile', data),
  updateProfile: (data: Partial<ProfProfile>) => request<ProfProfile>('PATCH', '/professor/profile', data),

  // Analytics
  getAnalytics: () => request<ProfAnalytics>('GET', '/professor/analytics'),

  // Review queue
  getQueue: (status?: string) =>
    request<QueueItem[]>('GET', `/professor/queue${status ? `?status_filter=${status}` : ''}`),
  acceptQueueItem: (id: string) => request<QueueItem>('POST', `/professor/queue/${id}/accept`),

  // Quality reviews
  getMyReviews: () => request<QualityReview[]>('GET', '/professor/reviews'),
  getContractReviews: (contractId: string) =>
    request<QualityReview[]>('GET', `/professor/reviews/contract/${contractId}`),
  submitReview: (contractId: string, data: SubmitReviewPayload) =>
    request<QualityReview>('POST', `/professor/reviews/contract/${contractId}`, data),

  // Assignments
  getAssignments: () => request<Assignment[]>('GET', '/professor/assignments'),
  createAssignment: (data: Partial<Assignment>) => request<Assignment>('POST', '/professor/assignments', data),
  updateAssignment: (id: string, data: Partial<Assignment>) =>
    request<Assignment>('PATCH', `/professor/assignments/${id}`, data),
  deleteAssignment: (id: string) => request<void>('DELETE', `/professor/assignments/${id}`),

  // Credentials
  getPendingCredentials: () => request<Credential[]>('GET', '/professor/credentials/pending'),
  actionCredential: (id: string, action: 'verify' | 'reject', rejection_reason?: string) =>
    request<Credential>('POST', `/professor/credentials/${id}/action`, { action, rejection_reason }),

  // Endorsements
  createEndorsement: (data: { researcher_id: string; subject_area: string; endorsement_text?: string }) =>
    request<Endorsement>('POST', '/professor/endorsements', data),

  // Disputes
  getDisputes: () => request<QueueItem[]>('GET', '/professor/disputes'),
  submitRuling: (disputeId: string, data: RulingPayload) =>
    request<DisputeRuling>('POST', `/professor/disputes/${disputeId}/ruling`, data),

  // Job marketplace (professor)
  getJobs: (params?: { status?: string; subject?: string; min_price?: number; max_price?: number; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status)    qs.set('status',    params.status)
    if (params?.subject)   qs.set('subject',   params.subject)
    if (params?.min_price) qs.set('min_price', String(params.min_price))
    if (params?.max_price) qs.set('max_price', String(params.max_price))
    qs.set('page',      String(params?.page      ?? 1))
    qs.set('page_size', String(params?.page_size ?? 20))
    return request<JobListResponse>('GET', `/professor/jobs?${qs}`)
  },
  getJob:    (id: string) => request<Job>('GET', `/professor/jobs/${id}`),
  bidOnJob:  (jobId: string, data: { proposed_price: string; message: string }) =>
    request<Bid>('POST', `/professor/jobs/${jobId}/bid`, data),
  getMyBids: () => request<{ items: Bid[]; total: number }>('GET', '/professor/my-bids'),
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProfUser {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
}

export interface ProfProfile {
  id: string
  user_id: string
  title?: string
  department?: string
  academic_rank?: string
  bio?: string
  expertise_areas?: string[]
  orcid_id?: string
  linkedin_url?: string
  institutional_email?: string
  status: string
  review_subjects?: string[]
  total_reviews_completed: number
  avg_review_score_given: number
  review_fee_per_job: number
  approved_at?: string
  created_at: string
}

export interface ProfAnalytics {
  total_reviews: number
  pending_reviews: number
  completed_reviews: number
  avg_score_given: number | null
  total_fees_earned: number
  disputes_arbitrated: number
  credentials_verified: number
  endorsements_given: number
  sla_compliance_rate: number
}

export interface QueueItem {
  id: string
  contract_id: string
  queue_type: string
  status: string
  priority: number
  sla_hours: number
  due_at?: string
  assigned_at?: string
  completed_at?: string
  notes?: string
  created_at: string
}

export interface QualityReview {
  id: string
  contract_id: string
  professor_id: string
  round_number: number
  status: string
  score?: number
  originality_score?: number
  feedback?: string
  payment_held: boolean
  reviewed_at?: string
  fee_amount: number
  fee_paid: boolean
  created_at: string
}

export interface SubmitReviewPayload {
  score: number
  originality_score?: number
  feedback: string
  rubric_scores?: Record<string, number>
  verdict: 'approved' | 'revision_required' | 'rejected'
}

export interface Assignment {
  id: string
  title: string
  description: string
  subject: string
  academic_level?: string
  rubric?: string
  min_quality_score?: number
  review_required: boolean
  suggested_price?: number
  deadline_hours?: number
  is_active: boolean
  created_at: string
}

export interface Credential {
  id: string
  researcher_id: string
  credential_type: string
  institution_name: string
  field_of_study?: string
  year_obtained?: number
  status: string
  verified_at?: string
  rejection_reason?: string
  created_at: string
}

export interface Endorsement {
  id: string
  professor_id: string
  researcher_id: string
  subject_area: string
  endorsement_text?: string
  is_active: boolean
  created_at: string
}

export interface DisputeRuling {
  id: string
  dispute_id: string
  professor_id: string
  ruling: string
  release_percentage?: number
  reasoning: string
  submitted_at?: string
}

export interface RulingPayload {
  ruling: 'full_release' | 'partial_release' | 'full_refund' | 'revision'
  release_percentage?: number
  reasoning: string
  evidence_reviewed?: string
}

export interface Job {
  id: string
  title: string
  description: string
  subject: string
  academic_level?: string
  proposed_price: string
  deadline: string
  status: string
  student_id: string
  created_at: string
}

export interface JobListResponse {
  items: Job[]
  total: number
  page: number
  page_size: number
}

export interface Bid {
  id: string
  job_id: string
  researcher_id: string
  proposed_price: string
  message: string
  status: string
  created_at: string
}
