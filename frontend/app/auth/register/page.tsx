"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { register as apiRegister, login } from "@/lib/api";
import toast from "react-hot-toast";
import { GraduationCap } from "lucide-react";
import Link from "next/link";

const LEVELS = [
  { value: "high_school",    label: "High School"   },
  { value: "undergraduate",  label: "Undergraduate" },
  { value: "postgraduate",   label: "Postgraduate"  },
  { value: "phd",            label: "PhD / Research"},
];

type Form = { email: string; password: string; confirm: string; full_name: string; academic_level: string; institution?: string; };

export default function Register() {
  const router   = useRouter();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, watch, formState: { errors } } = useForm<Form>({
    defaultValues: { academic_level: "undergraduate" },
  });

  async function onSubmit(data: Form) {
    if (data.password !== data.confirm) { toast.error("Passwords do not match"); return; }
    setLoading(true);
    try {
      await apiRegister(data.email, data.password, data.full_name, data.academic_level, data.institution);
      await login(data.email, data.password);
      toast.success("Account created! Welcome to ASA.");
      router.push("/dashboard");
    } catch (e: any) {
      toast.error(e.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-brand-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
          <p className="text-gray-500 mt-1">Join ASA v2 — Agentic Scholar Assistant</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Full Name *</label>
              <input className="input" placeholder="Derrick Botha"
                {...register("full_name", { required: "Full name is required" })} />
              {errors.full_name && <p className="text-red-500 text-xs mt-1">{errors.full_name.message}</p>}
            </div>
            <div>
              <label className="label">Email *</label>
              <input type="email" className="input" placeholder="you@university.edu"
                {...register("email", { required: "Email is required" })} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Password *</label>
                <input type="password" className="input" placeholder="••••••••"
                  {...register("password", { required: true, minLength: { value: 8, message: "Min 8 characters" } })} />
                {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
              </div>
              <div>
                <label className="label">Confirm Password *</label>
                <input type="password" className="input" placeholder="••••••••"
                  {...register("confirm", { required: true })} />
              </div>
            </div>
            <div>
              <label className="label">Academic Level</label>
              <select className="input" {...register("academic_level")}>
                {LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Institution (optional)</label>
              <input className="input" placeholder="University of East London"
                {...register("institution")} />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-4">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-brand-600 hover:underline font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
