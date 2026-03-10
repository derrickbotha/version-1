'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { GraduationCap, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'

export default function Login() {
  const router = useRouter()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await api.login(email, password)

      if (data.user.role !== 'professor' && data.user.role !== 'admin' && data.user.role !== 'super_admin') {
        setError('This portal is for professors only. Please use the student portal at localhost:3000.')
        return
      }

      localStorage.setItem('prof_token', data.access_token)
      localStorage.setItem('prof_user', JSON.stringify(data.user))

      // Try to load professor profile
      try {
        const prof = await api.getProfile()
        localStorage.setItem('prof_profile', JSON.stringify(prof))
      } catch { /* profile might not exist yet */ }

      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-profDark px-4">
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-profTeal rounded-2xl flex items-center justify-center mx-auto mb-4">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Professor Portal</h1>
          <p className="text-white/50 text-sm mt-1">ResearchPro Academic Review System</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl p-8 shadow-2xl"
        >
          <h2 className="text-lg font-semibold text-charcoal mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-5 flex items-start gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1.5">
                Institutional / Platform Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="professor@university.edu"
                className="w-full px-4 py-2.5 border border-divider rounded-lg text-sm text-charcoal placeholder:text-medGrey"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 border border-divider rounded-lg text-sm text-charcoal"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full py-3 bg-profTeal text-white rounded-lg font-semibold text-sm hover:bg-profDark disabled:opacity-60 transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>

          <p className="text-center text-xs text-medGrey mt-4">
            Student or researcher?{' '}
            <a href="http://localhost:3000/auth/login" className="text-profTeal font-medium hover:underline">
              Student portal →
            </a>
          </p>
        </form>
      </div>
    </div>
  )
}
