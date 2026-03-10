"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import Sidebar from "@/components/Sidebar";
import { createAssignment, type AssignmentForm } from "@/lib/api";
import toast from "react-hot-toast";
import {
  BookOpen, Target, Settings, Truck, CreditCard,
  ChevronRight, ChevronLeft, CheckCircle, Info
} from "lucide-react";
import clsx from "clsx";

const STEPS = [
  { id: 1, label: "Assignment Details", icon: BookOpen },
  { id: 2, label: "Research Focus",     icon: Target },
  { id: 3, label: "LMS & Delivery",     icon: Truck },
  { id: 4, label: "Review & Payment",   icon: CreditCard },
];

const ACADEMIC_LEVELS = [
  { value: "high_school",    label: "High School",    price: "$199/mo",  words: "800–1,200 words" },
  { value: "undergraduate",  label: "Undergraduate",  price: "$299/mo",  words: "1,500–3,000 words" },
  { value: "postgraduate",   label: "Postgraduate",   price: "$399/mo",  words: "5,000–10,000 words" },
  { value: "phd",            label: "PhD / Research", price: "Custom",   words: "10,000+ words" },
];

const CITATION_STYLES = ["Harvard", "APA", "MLA", "Chicago"];

export default function NewAssignment() {
  const router   = useRouter();
  const [step, setStep]       = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<AssignmentForm>({
    defaultValues: {
      word_count:       2000,
      academic_level:   "undergraduate",
      citation_style:   "Harvard",
      delivery_method:  "download",
      review_type:      "agent_only",
    },
  });

  const deliveryMethod  = watch("delivery_method");
  const reviewType      = watch("review_type");
  const academicLevel   = watch("academic_level");

  const planPrice = ACADEMIC_LEVELS.find(l => l.value === academicLevel)?.price ?? "$299/mo";
  const profExtra  = reviewType === "agent_professor" ? " + $20 professor review" : "";

  async function onSubmit(data: AssignmentForm) {
    setSubmitting(true);
    try {
      const assignment = await createAssignment(data);
      toast.success("Assignment submitted! Redirecting to checkout...");
      router.push(`/billing?assignment_id=${assignment.id}&review_type=${data.review_type}`);
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? "Failed to create assignment");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-surface">
        <div className="max-w-3xl mx-auto px-6 py-8">

          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">New Assignment</h1>
            <p className="text-gray-500 mt-1">Let ASA research, write, and deliver your assignment.</p>
          </div>

          {/* Step indicator */}
          <div className="flex items-center mb-8">
            {STEPS.map((s, idx) => (
              <div key={s.id} className="flex items-center">
                <button
                  type="button"
                  onClick={() => step > s.id && setStep(s.id)}
                  className={clsx(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                    step === s.id  ? "bg-brand-600 text-white" :
                    step > s.id   ? "bg-green-100 text-green-700 cursor-pointer hover:bg-green-200" :
                                    "text-gray-400"
                  )}
                >
                  {step > s.id ? <CheckCircle className="w-4 h-4" /> : <s.icon className="w-4 h-4" />}
                  <span className="hidden sm:inline">{s.label}</span>
                </button>
                {idx < STEPS.length - 1 && (
                  <ChevronRight className="w-4 h-4 text-gray-300 mx-1" />
                )}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit(onSubmit)}>

            {/* ── STEP 1: Assignment Details ─────────────────────────────── */}
            {step === 1 && (
              <div className="card space-y-5">
                <h2 className="font-semibold text-gray-900">Assignment Details</h2>

                <div>
                  <label className="label">Assignment Title *</label>
                  <input
                    className="input"
                    placeholder="e.g. Data Repositories in Data Ecology"
                    {...register("title", { required: "Title is required" })}
                  />
                  {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title.message}</p>}
                </div>

                <div>
                  <label className="label">Module Code</label>
                  <input className="input" placeholder="e.g. DS-7001" {...register("module_code")} />
                </div>

                <div>
                  <label className="label">Topic / Subject *</label>
                  <textarea
                    className="input h-24 resize-none"
                    placeholder="Describe the assignment topic in detail. The more specific, the better the research."
                    {...register("topic", { required: "Topic is required" })}
                  />
                  {errors.topic && <p className="text-red-500 text-xs mt-1">{errors.topic.message}</p>}
                </div>

                <div>
                  <label className="label">Assignment Instructions</label>
                  <textarea
                    className="input h-24 resize-none"
                    placeholder="Paste the full assignment brief or rubric here..."
                    {...register("instructions")}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Target Word Count</label>
                    <input
                      type="number" className="input"
                      {...register("word_count", { valueAsNumber: true, min: 200, max: 20000 })}
                    />
                  </div>
                  <div>
                    <label className="label">Citation Style</label>
                    <select className="input" {...register("citation_style")}>
                      {CITATION_STYLES.map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="label">Academic Level</label>
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    {ACADEMIC_LEVELS.map((l) => {
                      const selected = academicLevel === l.value;
                      return (
                        <label key={l.value} className={clsx(
                          "border rounded-lg p-3 cursor-pointer transition-all",
                          selected ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"
                        )}>
                          <input type="radio" value={l.value} {...register("academic_level")} className="sr-only" />
                          <p className={clsx("font-medium text-sm", selected ? "text-brand-700" : "text-gray-900")}>{l.label}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{l.words}</p>
                          <p className={clsx("text-xs font-semibold mt-1", selected ? "text-brand-600" : "text-gray-400")}>{l.price}</p>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="label">Deadline (optional)</label>
                  <input type="datetime-local" className="input" {...register("deadline")} />
                </div>

                <div className="flex justify-end">
                  <button type="button" onClick={() => setStep(2)} className="btn-primary flex items-center gap-2">
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 2: Research Focus ─────────────────────────────────── */}
            {step === 2 && (
              <div className="card space-y-5">
                <h2 className="font-semibold text-gray-900">Research Focus</h2>
                <p className="text-sm text-gray-500">
                  Guide the AI researcher to focus on specific areas within your topic.
                  The more specific your focus, the more targeted and high-quality the sources.
                </p>

                <div>
                  <label className="label">Specific Focus Area</label>
                  <textarea
                    className="input h-28 resize-none"
                    placeholder="e.g. 'Focus specifically on the application of FAIR data principles in insurance industry data management. Emphasise regulatory compliance and real-world case studies from Lloyd's of London and Swiss Re.'"
                    {...register("focus_area")}
                  />
                  <div className="flex items-start gap-2 mt-2 p-3 bg-blue-50 rounded-lg">
                    <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-blue-700">
                      Examples: "Focus on insurance sector applications", "Emphasise postgraduate-level analysis",
                      "Include UK-specific regulatory frameworks", "Prioritise 2020–2024 publications"
                    </p>
                  </div>
                </div>

                <div className="flex justify-between">
                  <button type="button" onClick={() => setStep(1)} className="btn-secondary flex items-center gap-2">
                    <ChevronLeft className="w-4 h-4" /> Back
                  </button>
                  <button type="button" onClick={() => setStep(3)} className="btn-primary flex items-center gap-2">
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 3: LMS & Delivery ─────────────────────────────────── */}
            {step === 3 && (
              <div className="card space-y-5">
                <h2 className="font-semibold text-gray-900">Delivery Options</h2>

                {/* Delivery method */}
                <div>
                  <label className="label">How should ASA deliver your assignment?</label>
                  <div className="space-y-3 mt-2">
                    {[
                      { value: "download",   label: "Download Report",      desc: "Get a download link to save the DOCX yourself" },
                      { value: "email",      label: "Send to Email",         desc: "ASA emails the DOCX directly to you" },
                      { value: "lms_upload", label: "Auto-Submit to LMS",   desc: "ASA logs in and submits to your Moodle/Canvas assignment" },
                    ].map((opt) => {
                      const sel = deliveryMethod === opt.value;
                      return (
                        <label key={opt.value} className={clsx(
                          "flex items-start gap-3 border rounded-lg p-4 cursor-pointer transition-all",
                          sel ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"
                        )}>
                          <input type="radio" value={opt.value} {...register("delivery_method")} className="mt-0.5" />
                          <div>
                            <p className={clsx("font-medium text-sm", sel ? "text-brand-700" : "text-gray-900")}>{opt.label}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{opt.desc}</p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>

                {/* Email delivery */}
                {deliveryMethod === "email" && (
                  <div>
                    <label className="label">Delivery Email Address *</label>
                    <input
                      type="email" className="input"
                      placeholder="your@email.com"
                      {...register("delivery_email", { required: deliveryMethod === "email" })}
                    />
                  </div>
                )}

                {/* LMS credentials */}
                {deliveryMethod === "lms_upload" && (
                  <div className="space-y-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm font-medium text-amber-800">
                      🔒 LMS Credentials — stored encrypted, used once for submission
                    </p>
                    <div>
                      <label className="label">LMS URL</label>
                      <input className="input" placeholder="https://vle-youruni.ac.uk" {...register("lms_url")} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="label">Username / Student ID</label>
                        <input className="input" placeholder="user12345678" {...register("lms_username")} />
                      </div>
                      <div>
                        <label className="label">Password</label>
                        <input type="password" className="input" placeholder="••••••••" {...register("lms_password")} />
                      </div>
                    </div>
                    <div>
                      <label className="label">Assignment URL or ID</label>
                      <input
                        className="input"
                        placeholder="https://vle.uni.ac.uk/mod/assign/view.php?id=680893"
                        {...register("lms_assignment_id")}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Paste the full URL of the specific assignment submission page.
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex justify-between">
                  <button type="button" onClick={() => setStep(2)} className="btn-secondary flex items-center gap-2">
                    <ChevronLeft className="w-4 h-4" /> Back
                  </button>
                  <button type="button" onClick={() => setStep(4)} className="btn-primary flex items-center gap-2">
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* ── STEP 4: Review & Payment ────────────────────────────────── */}
            {step === 4 && (
              <div className="space-y-5">
                <div className="card">
                  <h2 className="font-semibold text-gray-900 mb-4">Review Type</h2>
                  <div className="space-y-3">
                    {[
                      {
                        value: "agent_only",
                        label: "Agent Only",
                        badge: "Included in plan",
                        desc: "ASA researches, writes, checks plagiarism, adjusts tone, and delivers. No human involvement.",
                        color: "text-green-600 bg-green-50",
                      },
                      {
                        value: "agent_professor",
                        label: "Agent + Professor Review",
                        badge: "+$20 per assignment",
                        desc: "After ASA completes the assignment, a qualified professor reviews it, adds comments, and approves before delivery. Recommended for postgraduate and PhD work.",
                        color: "text-orange-600 bg-orange-50",
                      },
                    ].map((opt) => {
                      const sel = reviewType === opt.value;
                      return (
                        <label key={opt.value} className={clsx(
                          "flex items-start gap-3 border rounded-lg p-4 cursor-pointer transition-all",
                          sel ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"
                        )}>
                          <input type="radio" value={opt.value} {...register("review_type")} className="mt-0.5" />
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className={clsx("font-medium text-sm", sel ? "text-brand-700" : "text-gray-900")}>{opt.label}</p>
                              <span className={`badge ${opt.color}`}>{opt.badge}</span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">{opt.desc}</p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>

                {/* Order summary */}
                <div className="card bg-gradient-to-br from-brand-50 to-white border-brand-100">
                  <h2 className="font-semibold text-gray-900 mb-4">Order Summary</h2>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Plan</span>
                      <span className="font-medium">{ACADEMIC_LEVELS.find(l => l.value === academicLevel)?.label}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Monthly subscription</span>
                      <span className="font-medium">{planPrice}</span>
                    </div>
                    {reviewType === "agent_professor" && (
                      <div className="flex justify-between text-orange-700">
                        <span>Professor review add-on</span>
                        <span className="font-medium">+$20.00</span>
                      </div>
                    )}
                    <div className="border-t pt-2 mt-2 flex justify-between font-semibold">
                      <span>Total this assignment</span>
                      <span className="text-brand-700">{planPrice}{profExtra}</span>
                    </div>
                  </div>
                </div>

                <div className="card space-y-3">
                  <h2 className="font-semibold text-gray-900 mb-1">Payment Method</h2>
                  <p className="text-sm text-gray-500">After submitting, you will be redirected to a secure payment page.</p>
                  <div className="flex gap-3">
                    <div className="flex-1 border border-gray-200 rounded-lg p-3 text-center text-sm font-medium text-gray-700 hover:border-brand-400 cursor-pointer">
                      💳 Pay with Card (Stripe)
                    </div>
                    <div className="flex-1 border border-gray-200 rounded-lg p-3 text-center text-sm font-medium text-gray-700 hover:border-brand-400 cursor-pointer">
                      🅿️ Pay with PayPal
                    </div>
                  </div>
                </div>

                <div className="flex justify-between">
                  <button type="button" onClick={() => setStep(3)} className="btn-secondary flex items-center gap-2">
                    <ChevronLeft className="w-4 h-4" /> Back
                  </button>
                  <button type="submit" disabled={submitting} className="btn-primary flex items-center gap-2 min-w-[180px] justify-center">
                    {submitting ? (
                      <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                    ) : (
                      <>Submit & Pay <ChevronRight className="w-4 h-4" /></>
                    )}
                  </button>
                </div>
              </div>
            )}

          </form>
        </div>
      </main>
    </div>
  );
}
