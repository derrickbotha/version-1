'use client'

import { useState, FormEvent } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Loader2, GraduationCap, FlaskConical } from 'lucide-react'
import { register } from '@/lib/api'
import { Suspense } from 'react'

type Role = 'student' | 'researcher'

interface FormData {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

interface FormErrors {
  first_name?: string
  last_name?: string
  email?: string
  password?: string
  confirm_password?: string
  general?: string
}

function RegisterForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [role, setRole] = useState<Role>('student')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<FormErrors>({})

  const [form, setForm] = useState<FormData>({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
  })

  const updateField = (field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }

  function validate(): FormErrors {
    const errs: FormErrors = {}
    if (!form.first_name.trim()) errs.first_name = 'First name is required'
    if (!form.last_name.trim()) errs.last_name = 'Last name is required'
    if (!form.email.trim()) {
      errs.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      errs.email = 'Please enter a valid email address'
    }
    if (!form.password) {
      errs.password = 'Password is required'
    } else if (form.password.length < 10) {
      errs.password = 'Password must be at least 10 characters'
    }
    if (!form.confirm_password) {
      errs.confirm_password = 'Please confirm your password'
    } else if (form.password !== form.confirm_password) {
      errs.confirm_password = 'Passwords do not match'
    }
    return errs
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }

    setLoading(true)
    setErrors({})

    try {
      await register({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        password: form.password,
        role,
      })

      const plan = searchParams.get('plan')
      if (plan) {
        router.push(`/auth/login?registered=true&plan=${plan}`)
      } else {
        router.push('/auth/login?registered=true')
      }
    } catch (err) {
      setErrors({
        general: err instanceof Error ? err.message : 'Registration failed. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  const inputClass = (hasError: boolean) =>
    `w-full border rounded-lg px-4 py-3 text-sm text-charcoal placeholder:text-medGrey/60 outline-none transition-all ${
      hasError
        ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-200'
        : 'border-divider focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20'
    }`

  return (
    <div className="min-h-screen bg-lightGrey flex items-center justify-center px-4 pt-20 pb-10">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="w-full max-w-[520px] bg-white rounded-2xl shadow-xl border border-divider p-10"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <Link
            href="/"
            className="font-display text-2xl font-semibold text-charcoal hover:text-steelBlue transition-colors"
          >
            ResearchPro
          </Link>
          <h1 className="font-display text-3xl font-semibold text-charcoal mt-4 mb-1">
            Create Account
          </h1>
          <p className="text-medGrey text-sm">Join 52,000+ students and researchers</p>
        </div>

        {/* Role Tabs */}
        <div className="flex border border-divider rounded-xl p-1 mb-7 bg-lightGrey">
          {([
            { value: 'student' as Role, label: "I'm a Student", icon: GraduationCap },
            { value: 'researcher' as Role, label: "I'm a Researcher", icon: FlaskConical },
          ] as const).map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => setRole(value)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                role === value
                  ? 'bg-white shadow-sm text-charcoal border border-divider'
                  : 'text-medGrey hover:text-charcoal'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {/* General error */}
          {errors.general && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-5"
            >
              {errors.general}
            </motion.div>
          )}

          {/* Name row */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                First Name
              </label>
              <input
                type="text"
                value={form.first_name}
                onChange={(e) => updateField('first_name', e.target.value)}
                required
                autoComplete="given-name"
                placeholder="John"
                className={inputClass(!!errors.first_name)}
              />
              {errors.first_name && (
                <p className="text-red-500 text-xs mt-1">{errors.first_name}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Last Name
              </label>
              <input
                type="text"
                value={form.last_name}
                onChange={(e) => updateField('last_name', e.target.value)}
                required
                autoComplete="family-name"
                placeholder="Smith"
                className={inputClass(!!errors.last_name)}
              />
              {errors.last_name && (
                <p className="text-red-500 text-xs mt-1">{errors.last_name}</p>
              )}
            </div>
          </div>

          {/* Email */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-charcoal mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              required
              autoComplete="email"
              placeholder="you@university.edu"
              className={inputClass(!!errors.email)}
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
          </div>

          {/* Password */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-charcoal mb-1.5">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => updateField('password', e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Minimum 10 characters"
                className={inputClass(!!errors.password) + ' pr-11'}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-medGrey hover:text-charcoal transition-colors"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.password ? (
              <p className="text-red-500 text-xs mt-1">{errors.password}</p>
            ) : (
              <p className="text-medGrey text-xs mt-1">Must be at least 10 characters</p>
            )}
          </div>

          {/* Confirm Password */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-charcoal mb-1.5">
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={form.confirm_password}
                onChange={(e) => updateField('confirm_password', e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Repeat your password"
                className={inputClass(!!errors.confirm_password) + ' pr-11'}
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-medGrey hover:text-charcoal transition-colors"
              >
                {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.confirm_password && (
              <p className="text-red-500 text-xs mt-1">{errors.confirm_password}</p>
            )}
          </div>

          {/* Hidden role field (for clarity) */}
          <input type="hidden" name="role" value={role} />

          {/* Terms notice */}
          <p className="text-xs text-medGrey mb-5">
            By creating an account, you agree to our{' '}
            <Link href="/terms" className="text-ctaBlue hover:text-steelBlue">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="text-ctaBlue hover:text-steelBlue">
              Privacy Policy
            </Link>
            .
          </p>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ctaBlue text-white text-base font-semibold py-3.5 rounded-xl hover:bg-blue-600 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating account...
              </>
            ) : (
              `Create ${role === 'student' ? 'Student' : 'Researcher'} Account`
            )}
          </button>
        </form>

        <div className="text-center mt-6 pt-6 border-t border-divider">
          <p className="text-sm text-medGrey">
            Already have an account?{' '}
            <Link
              href="/auth/login"
              className="text-ctaBlue font-medium hover:text-steelBlue transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-lightGrey flex items-center justify-center pt-20"><div className="w-8 h-8 border-2 border-ctaBlue border-t-transparent rounded-full animate-spin" /></div>}>
      <RegisterForm />
    </Suspense>
  )
}
