const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// ── Backend envelope ──────────────────────────────────────────────────────────
export interface BackendResponse<T> {
  status: 'success' | 'error'
  data: T
  message?: string
}

// ── Auth types ────────────────────────────────────────────────────────────────
export interface RegisterPayload {
  email: string
  password: string
  first_name: string
  last_name: string
  role: 'student' | 'researcher'
  phone?: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserData {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_verified: boolean
  created_at: string
}

// ── Job types ─────────────────────────────────────────────────────────────────
export interface JobCreatePayload {
  title: string
  description: string
  subject: string
  academic_level: string
  proposed_price: string
  deadline: string
}

export interface JobData {
  id: string
  title: string
  description: string
  subject: string
  academic_level: string
  proposed_price: string
  status: string
  deadline: string
  student_id: string
  created_at: string
}

export interface JobListData {
  items: JobData[]
  total: number
  page: number
  page_size: number
}

export interface JobFilters {
  status?: string
  subject?: string
  min_price?: number
  max_price?: number
  page?: number
  page_size?: number
}

// ── Bid types ─────────────────────────────────────────────────────────────────
export interface BidPayload {
  proposed_price: string
  message: string
}

export interface BidData {
  id: string
  job_id: string
  researcher_id: string
  proposed_price: string
  message: string | null
  status: string
  created_at: string
}

export interface BidListData {
  items: BidData[]
  total: number
}

// ── Contract types ────────────────────────────────────────────────────────────
export interface ContractData {
  id: string
  job_id: string
  student_id: string
  researcher_id: string
  agreed_price: string
  start_date: string | null
  deadline: string | null
  status: string
  created_at: string
}

export interface ContractListData {
  items: ContractData[]
  total: number
}

// ── Payment types ─────────────────────────────────────────────────────────────
export interface EscrowPayload {
  contract_id: string
  payment_provider: string
  provider_reference: string
}

export interface WalletDepositPayload {
  amount: number
}

export interface WalletData {
  user_id: string
  balance: string
}

export interface PaymentData {
  id: string
  contract_id: string
  student_id: string
  researcher_id: string
  amount: string
  status: string
  payment_provider: string | null
  created_at: string
}

export interface WalletTransaction {
  id: string
  amount: string
  transaction_type: string
  created_at: string
}

// ── Submission types ──────────────────────────────────────────────────────────
export interface SubmissionData {
  id: string
  contract_id: string
  researcher_id: string
  submission_notes: string | null
  status: string
  submitted_at: string
  files: string[]
}

export interface SubmissionListData {
  items: SubmissionData[]
  total: number
}

// ── Dispute types ─────────────────────────────────────────────────────────────
export interface DisputeData {
  id: string
  contract_id: string
  opened_by: string
  reason: string
  status: string
  resolution: string | null
  resolved_by: string | null
  created_at: string
}

// ── Message types ─────────────────────────────────────────────────────────────
export interface MessagePayload {
  conversation_id: string
  content: string
}

// ── Core client ───────────────────────────────────────────────────────────────
async function apiClient<T>(path: string, options: RequestInit = {}): Promise<BackendResponse<T>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token')
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    const msg = body?.message || body?.detail || `Request failed: ${response.status}`
    throw new Error(msg)
  }

  return body as BackendResponse<T>
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function register(payload: RegisterPayload) {
  return apiClient<UserData>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function login(payload: LoginPayload) {
  return apiClient<TokenData>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getMe() {
  return apiClient<UserData>('/auth/me')
}

export async function refreshToken(token: string) {
  return apiClient<TokenData>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: token }),
  })
}

// ── Jobs ──────────────────────────────────────────────────────────────────────
export async function getJobs(filters?: JobFilters) {
  const params = new URLSearchParams()
  if (filters) {
    if (filters.status) params.append('status', filters.status)
    if (filters.subject) params.append('subject', filters.subject)
    if (filters.min_price != null) params.append('min_price', String(filters.min_price))
    if (filters.max_price != null) params.append('max_price', String(filters.max_price))
    if (filters.page != null) params.append('page', String(filters.page))
    if (filters.page_size != null) params.append('page_size', String(filters.page_size))
  }
  const query = params.toString() ? `?${params.toString()}` : ''
  return apiClient<JobListData>(`/jobs${query}`)
}

export async function getMyJobs() {
  return apiClient<JobListData>('/jobs/mine')
}

export async function getJob(id: string) {
  return apiClient<JobData>(`/jobs/${id}`)
}

export async function createJob(payload: JobCreatePayload) {
  return apiClient<JobData>('/jobs', { method: 'POST', body: JSON.stringify(payload) })
}

// ── Bids ──────────────────────────────────────────────────────────────────────
export async function placeBid(jobId: string, payload: BidPayload) {
  return apiClient<BidData>(`/jobs/${jobId}/bids`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function getJobBids(jobId: string) {
  return apiClient<BidListData>(`/jobs/${jobId}/bids`)
}

export async function acceptBid(bidId: string) {
  return apiClient<ContractData>(`/bids/${bidId}/accept`, { method: 'POST' })
}

export async function rejectBid(bidId: string) {
  return apiClient<BidData>(`/bids/${bidId}/reject`, { method: 'POST' })
}

export async function getMyBids() {
  return apiClient<BidListData>('/bids/mine')
}

// ── Contracts ─────────────────────────────────────────────────────────────────
export async function getContracts() {
  return apiClient<ContractListData>('/contracts')
}

export async function getContract(id: string) {
  return apiClient<ContractData>(`/contracts/${id}`)
}

export async function startContract(contractId: string) {
  return apiClient<ContractData>(`/contracts/${contractId}/start`, { method: 'POST' })
}

// ── Payments ──────────────────────────────────────────────────────────────────
export async function depositToWallet(payload: WalletDepositPayload) {
  return apiClient<WalletData>('/payments/wallet/deposit', { method: 'POST', body: JSON.stringify(payload) })
}

export async function getWallet() {
  return apiClient<WalletData>('/payments/wallet')
}

export async function getWalletTransactions(page = 1) {
  return apiClient<{ items: WalletTransaction[]; total: number; page: number; page_size: number }>(
    `/payments/wallet/transactions?page=${page}`
  )
}

export async function createEscrow(payload: EscrowPayload) {
  return apiClient<PaymentData>('/payments/escrow', { method: 'POST', body: JSON.stringify(payload) })
}

export async function releasePayment(contract_id: string) {
  return apiClient<PaymentData>('/payments/release', {
    method: 'POST',
    body: JSON.stringify({ contract_id }),
  })
}

export async function getContractPayment(contractId: string) {
  return apiClient<PaymentData>(`/payments/contract/${contractId}`)
}

// ── Submissions ───────────────────────────────────────────────────────────────
export async function createSubmission(payload: { contract_id: string; submission_notes: string }) {
  return apiClient<SubmissionData>('/submissions', { method: 'POST', body: JSON.stringify(payload) })
}

export async function getContractSubmissions(contractId: string) {
  return apiClient<SubmissionListData>(`/contracts/${contractId}/submissions`)
}

export async function approveSubmission(submissionId: string) {
  return apiClient<SubmissionData>(`/submissions/${submissionId}/approve`, { method: 'POST' })
}

export async function requestRevision(submissionId: string, message: string) {
  return apiClient<{ id: string; message: string }>(`/submissions/${submissionId}/revision`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

// ── Disputes ──────────────────────────────────────────────────────────────────
export async function openDispute(payload: { contract_id: string; reason: string }) {
  return apiClient<DisputeData>('/disputes', { method: 'POST', body: JSON.stringify(payload) })
}

export async function getMyDisputes() {
  return apiClient<{ items: DisputeData[]; total: number }>('/disputes/mine')
}

// ── Account settings ─────────────────────────────────────────────────────────
export interface AccountProfile {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  phone: string | null
  whatsapp_number: string | null
  is_verified: boolean
  status: string
  created_at: string
}

export interface AccountData {
  profile: AccountProfile
  student_profile: { university: string | null; degree_program: string | null; country: string | null } | null
  researcher_profile: { bio: string | null; expertise: string[] | null; rating: number; total_jobs_completed: number } | null
}

export async function getAccount() {
  return apiClient<AccountData>('/account')
}

export async function updateProfile(payload: Partial<{ first_name: string; last_name: string; phone: string; whatsapp_number: string }>) {
  return apiClient<AccountProfile>('/account/profile', { method: 'PATCH', body: JSON.stringify(payload) })
}

export async function updateContact(payload: Partial<{ email: string; phone: string; whatsapp_number: string }>) {
  return apiClient<AccountProfile>('/account/contact', { method: 'PATCH', body: JSON.stringify(payload) })
}

export async function updateLocation(payload: Partial<{ country: string; city: string; postal_code: string; timezone: string }>) {
  return apiClient<AccountProfile>('/account/location', { method: 'PATCH', body: JSON.stringify(payload) })
}

export async function changePassword(payload: { current_password: string; new_password: string }) {
  return apiClient<{ message: string }>('/account/security/change-password', { method: 'POST', body: JSON.stringify(payload) })
}

export async function updateStudentProfile(payload: Partial<{ university: string; degree_program: string; country: string }>) {
  return apiClient('/account/student-profile', { method: 'PATCH', body: JSON.stringify(payload) })
}

export async function updateResearcherProfile(payload: Partial<{ bio: string; expertise: string[] }>) {
  return apiClient('/account/researcher-profile', { method: 'PATCH', body: JSON.stringify(payload) })
}

// ── Payment methods ───────────────────────────────────────────────────────────
export interface PaymentMethodData {
  id: string
  provider: string
  brand: string | null
  last4: string | null
  expiry_month: number | null
  expiry_year: number | null
  is_default: boolean
  created_at: string
}

export async function getPaymentMethods() {
  return apiClient<PaymentMethodData[]>('/payments/methods')
}

export async function deletePaymentMethod(id: string) {
  return apiClient<{ message: string }>(`/payments/methods/${id}`, { method: 'DELETE' })
}

export async function setDefaultPaymentMethod(payment_method_id: string) {
  return apiClient<PaymentMethodData>('/payments/methods/default', { method: 'POST', body: JSON.stringify({ payment_method_id }) })
}

// ── Stripe ────────────────────────────────────────────────────────────────────
export interface StripeIntentData {
  client_secret: string
  payment_intent_id: string
  publishable_key: string
}

export async function createStripeDepositIntent(amount: number, save_method = false) {
  return apiClient<StripeIntentData>('/payments/wallet/stripe-intent', {
    method: 'POST',
    body: JSON.stringify({ amount, save_method }),
  })
}

// ── Writer payouts ────────────────────────────────────────────────────────────
export interface WriterPayoutData {
  id: string
  writer_id: string
  amount: string
  currency: string
  status: string
  provider: string | null
  created_at: string
}

export async function requestPayout(amount: number, provider: 'stripe' | 'paypal') {
  return apiClient<WriterPayoutData>('/payments/payout', {
    method: 'POST',
    body: JSON.stringify({ amount, provider }),
  })
}

export async function getPayouts(page = 1) {
  return apiClient<{ items: WriterPayoutData[]; total: number; page: number; page_size: number }>(
    `/payments/payouts?page=${page}`
  )
}

// ── Messages ──────────────────────────────────────────────────────────────────
export async function getConversations() {
  return apiClient('/conversations')
}

export async function getMessages(conversationId: string, page = 1) {
  return apiClient(`/conversations/${conversationId}/messages?page=${page}`)
}

export async function sendMessage(payload: MessagePayload) {
  return apiClient('/messages', { method: 'POST', body: JSON.stringify(payload) })
}

export default apiClient
