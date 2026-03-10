import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const api = axios.create({ baseURL: BASE });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("asa_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem("asa_refresh");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh`, { refresh_token: refresh });
          localStorage.setItem("asa_token", data.access_token);
          localStorage.setItem("asa_refresh", data.refresh_token);
          err.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api(err.config);
        } catch {
          localStorage.clear();
          window.location.href = "/auth/login";
        }
      }
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────────────────────────

export async function register(email: string, password: string, fullName: string,
                                academicLevel: string, institution?: string) {
  const { data } = await api.post("/auth/register", { email, password, full_name: fullName, academic_level: academicLevel, institution });
  return data;
}

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/login", { email, password });
  localStorage.setItem("asa_token", data.access_token);
  localStorage.setItem("asa_refresh", data.refresh_token);
  return data;
}

export async function getMe() {
  const { data } = await api.get("/auth/me");
  return data;
}

export function logout() {
  localStorage.clear();
  window.location.href = "/auth/login";
}

// ─── Assignments ───────────────────────────────────────────────────────────

export async function createAssignment(form: AssignmentForm) {
  const { data } = await api.post("/assignments", form);
  return data;
}

export async function listAssignments() {
  const { data } = await api.get("/assignments");
  return data;
}

export async function getAssignment(id: string) {
  const { data } = await api.get(`/assignments/${id}`);
  return data;
}

export async function getAssignmentStatus(id: string) {
  const { data } = await api.get(`/assignments/${id}/status`);
  return data;
}

export function downloadUrl(id: string) {
  return `${BASE}/assignments/${id}/download?token=${localStorage.getItem("asa_token")}`;
}

// ─── Billing ───────────────────────────────────────────────────────────────

export async function getPricing() {
  const { data } = await api.get("/billing/pricing");
  return data;
}

export async function checkoutStripe(assignmentId: string, reviewType: string) {
  const { data } = await api.post("/billing/checkout/stripe", { assignment_id: assignmentId, review_type: reviewType, payment_method: "stripe" });
  return data;
}

export async function checkoutPaypal(assignmentId: string, reviewType: string) {
  const { data } = await api.post("/billing/checkout/paypal", { assignment_id: assignmentId, review_type: reviewType, payment_method: "paypal" });
  return data;
}

export async function getOrders() {
  const { data } = await api.get("/billing/orders");
  return data;
}

// ─── Research ──────────────────────────────────────────────────────────────

export async function getResearchStats() {
  const { data } = await api.get("/research/graph/stats");
  return data;
}

// ─── Types ─────────────────────────────────────────────────────────────────

export interface AssignmentForm {
  title: string;
  module_code?: string;
  topic: string;
  instructions?: string;
  focus_area?: string;
  word_count: number;
  academic_level: string;
  deadline?: string;
  citation_style: string;
  lms_url?: string;
  lms_username?: string;
  lms_password?: string;
  lms_assignment_id?: string;
  delivery_method: "download" | "lms_upload" | "email";
  delivery_email?: string;
  review_type: "agent_only" | "agent_professor";
}

export interface Assignment {
  id: string;
  title: string;
  topic: string;
  status: string;
  review_type: string;
  delivery_method: string;
  word_count: number;
  plagiarism_score?: string;
  quality_score?: number;
  docx_path?: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  academic_level: string;
  institution?: string;
  is_verified: boolean;
}
