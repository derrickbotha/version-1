'use client'

import { useState, FormEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { login, getMe } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({})

  function validate(): boolean {
    const errors: { email?: string; password?: string } = {}
    if (!email.trim()) {
      errors.email = 'Email is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Please enter a valid email address.'
    }
    if (!password) {
      errors.password = 'Password is required.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!validate()) return

    setLoading(true)
    try {
      const res = await login({ email: email.trim(), password })
      const tokens = res.data
      localStorage.setItem('auth_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      // Fetch user profile and store it
      const meRes = await getMe()
      localStorage.setItem('user', JSON.stringify(meRes.data))
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid email or password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-lightGrey flex items-center justify-center px-4 pt-20">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="w-full max-w-[480px] bg-white rounded-2xl shadow-xl border border-divider p-10"
      >
        <div className="text-center mb-8">
          <Link href="/" className="font-display text-2xl font-semibold text-charcoal hover:text-steelBlue transition-colors">
            ResearchPro
          </Link>
          <h1 className="font-display text-3xl font-semibold text-charcoal mt-4 mb-1">Welcome Back</h1>
          <p className="text-medGrey text-sm">Sign in to your account to continue</p>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-5"
            >
              {error}
            </motion.div>
          )}

          {/* Email */}
          <div className="mb-5">
            <label htmlFor="email" className="block text-sm font-medium text-charcoal mb-1.5">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setFieldErrors(p => ({ ...p, email: undefined })) }}
              autoComplete="email"
              placeholder="you@university.edu"
              className={`w-full border rounded-lg px-4 py-3 text-sm text-charcoal placeholder:text-medGrey/60 focus:ring-2 outline-none transition-all ${
                fieldErrors.email
                  ? 'border-red-400 focus:border-red-400 focus:ring-red-100'
                  : 'border-divider focus:border-steelBlue focus:ring-steelBlue/20'
              }`}
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red-500">{fieldErrors.email}</p>}
          </div>

          {/* Password */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="password" className="block text-sm font-medium text-charcoal">
                Password
              </label>
              <Link href="/auth/forgot-password" className="text-xs text-ctaBlue hover:text-steelBlue transition-colors">
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => { setPassword(e.target.value); setFieldErrors(p => ({ ...p, password: undefined })) }}
                autoComplete="current-password"
                placeholder="Enter your password"
                className={`w-full border rounded-lg px-4 py-3 pr-11 text-sm text-charcoal placeholder:text-medGrey/60 focus:ring-2 outline-none transition-all ${
                  fieldErrors.password
                    ? 'border-red-400 focus:border-red-400 focus:ring-red-100'
                    : 'border-divider focus:border-steelBlue focus:ring-steelBlue/20'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-medGrey hover:text-charcoal transition-colors"
                aria-label="Toggle password visibility"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {fieldErrors.password && <p className="mt-1 text-xs text-red-500">{fieldErrors.password}</p>}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ctaBlue text-white text-base font-semibold py-3.5 rounded-xl hover:bg-blue-600 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg flex items-center justify-center gap-2"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" />Signing in...</>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="text-center mt-6 pt-6 border-t border-divider">
          <p className="text-sm text-medGrey">
            Don&apos;t have an account?{' '}
            <Link href="/auth/register" className="text-ctaBlue font-medium hover:text-steelBlue transition-colors">
              Create an account
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
