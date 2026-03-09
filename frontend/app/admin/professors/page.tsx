'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Award, CheckCircle, XCircle, Clock, RefreshCw, ChevronDown } from 'lucide-react'

interface Professor {
  id: string
  user_id: string
  user_email: string
  user_name: string
  institution_name: string | null
  department: string | null
  academic_rank: string | null
  status: string
  total_reviews_completed: number
  review_subjects: string[] | null
  created_at: string
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending: <Clock className="w-4 h-4 text-yellow-500" />,
  approved: <CheckCircle className="w-4 h-4 text-green-500" />,
  rejected: <XCircle className="w-4 h-4 text-red-500" />,
  suspended: <XCircle className="w-4 h-4 text-orange-500" />,
}

export default function AdminProfessors() {
  const router = useRouter()
  const [profs, setProfs] = useState<Professor[]>([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [loading, setLoading] = useState(true)
  const [flash, setFlash] = useState('')
  const [actioning, setActioning] = useState<string | null>(null)

  async function load() {
    const token = localStorage.getItem('auth_token')
    if (!token) { router.push('/auth/login'); return }
    setLoading(true)
    const params = new URLSearchParams({ page: '1', page_size: '50' })
    if (statusFilter) params.set('status_filter', statusFilter)
    try {
      const res = await fetch(`${API}/admin/professors?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) { router.push('/dashboard'); return }
      const data = await res.json()
      setProfs(data.data.items)
      setTotal(data.data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [statusFilter])

  async function actionProfessor(profId: string, action: 'approve' | 'reject') {
    const token = localStorage.getItem('auth_token')
    setActioning(profId)
    const res = await fetch(`${API}/admin/professors/${profId}/action`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    })
    setActioning(null)
    if (res.ok) {
      setFlash(`Professor ${action}d successfully`)
      load()
    }
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Professor Management</h1>
          <p className="text-medGrey text-sm mt-1">{total} professors in this view</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-white border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          {flash}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2 mb-5">
        {['pending', 'approved', 'rejected', 'suspended'].map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              statusFilter === s
                ? 'bg-steelBlue text-white'
                : 'bg-white border border-divider text-charcoal hover:bg-lightGrey'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-12 text-center text-medGrey flex items-center justify-center gap-2">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading...
        </div>
      ) : profs.length === 0 ? (
        <div className="py-12 text-center text-medGrey">
          No professors with status &ldquo;{statusFilter}&rdquo;
        </div>
      ) : (
        <div className="space-y-4">
          {profs.map(prof => (
            <div key={prof.id} className="bg-white border border-divider rounded-xl p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-teal-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Award className="w-5 h-5 text-teal-600" />
                  </div>
                  <div>
                    <div className="font-semibold text-charcoal flex items-center gap-2">
                      {prof.user_name}
                      {STATUS_ICON[prof.status]}
                    </div>
                    <div className="text-sm text-medGrey">{prof.user_email}</div>
                    {prof.institution_name && (
                      <div className="text-sm text-charcoal mt-1">
                        {prof.department && <span>{prof.department}, </span>}
                        {prof.institution_name}
                      </div>
                    )}
                    {prof.academic_rank && (
                      <div className="text-xs text-medGrey mt-0.5 capitalize">
                        {prof.academic_rank.replace(/_/g, ' ')}
                      </div>
                    )}
                    {prof.review_subjects && prof.review_subjects.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {prof.review_subjects.slice(0, 4).map(s => (
                          <span key={s} className="px-2 py-0.5 bg-lightGrey text-charcoal rounded-full text-xs">{s}</span>
                        ))}
                        {prof.review_subjects.length > 4 && (
                          <span className="px-2 py-0.5 bg-lightGrey text-medGrey rounded-full text-xs">
                            +{prof.review_subjects.length - 4} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {prof.status === 'pending' && (
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => actionProfessor(prof.id, 'approve')}
                      disabled={actioning === prof.id}
                      className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" /> Approve
                    </button>
                    <button
                      onClick={() => actionProfessor(prof.id, 'reject')}
                      disabled={actioning === prof.id}
                      className="flex items-center gap-1.5 px-4 py-2 bg-white border border-divider text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-divider flex gap-6 text-xs text-medGrey">
                <span>Reviews completed: <strong className="text-charcoal">{prof.total_reviews_completed}</strong></span>
                <span>Applied: <strong className="text-charcoal">{new Date(prof.created_at).toLocaleDateString()}</strong></span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
