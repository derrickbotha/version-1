'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Briefcase, Search, Filter, DollarSign, Clock, BookOpen, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { api, Job, JobListResponse } from '@/lib/api'

const SUBJECTS = ['All', 'Mathematics', 'Computer Science', 'Physics', 'Chemistry', 'Biology', 'Economics', 'Psychology', 'History', 'Literature', 'Engineering', 'Law', 'Medicine', 'Statistics']
const LEVELS   = ['All', 'High School', 'Undergraduate', 'Masters', 'PhD', 'Professional']

function timeLeft(deadline: string) {
  const diff = new Date(deadline).getTime() - Date.now()
  if (diff < 0) return { label: 'Expired', urgent: true }
  const days = Math.floor(diff / 86400000)
  if (days > 0) return { label: `${days}d left`, urgent: days <= 2 }
  const hrs = Math.floor(diff / 3600000)
  return { label: `${hrs}h left`, urgent: true }
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'open'        ? 'bg-green-100 text-green-700'  :
    status === 'negotiation' ? 'bg-yellow-100 text-yellow-700' :
    status === 'awarded'     ? 'bg-blue-100 text-blue-700'    :
                               'bg-gray-100 text-gray-500'
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${cls}`}>{status}</span>
}

export default function JobsPage() {
  const router = useRouter()
  const [result,   setResult]   = useState<JobListResponse | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [search,   setSearch]   = useState('')
  const [subject,  setSubject]  = useState('All')
  const [level,    setLevel]    = useState('All')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [page,     setPage]     = useState(1)

  async function load(p = page) {
    setLoading(true)
    try {
      const data = await api.getJobs({
        status:    'open',
        subject:   subject !== 'All' ? subject : undefined,
        min_price: minPrice ? Number(minPrice) : undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        page:      p,
        page_size: 12,
      })
      setResult(data)
    } catch (e: any) {
      if (e.message?.includes('401')) router.push('/auth/login')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(1); setPage(1) }, [subject, minPrice, maxPrice])
  useEffect(() => { load(page) }, [page])

  const filtered = result?.items.filter(j =>
    !search || j.title.toLowerCase().includes(search.toLowerCase()) ||
    j.description.toLowerCase().includes(search.toLowerCase())
  ) ?? []

  const totalPages = result ? Math.ceil(result.total / 12) : 1

  return (
    <div className="p-8 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-charcoal flex items-center gap-2">
          <Briefcase className="w-6 h-6 text-profTeal" /> Job Marketplace
        </h1>
        <p className="text-medGrey text-sm mt-1">Browse open research jobs and place your bid</p>
      </div>

      {/* Filters */}
      <div className="bg-white border border-divider rounded-xl p-5 mb-6">
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-medGrey" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search jobs…"
              className="w-full pl-9 pr-4 py-2 text-sm border border-divider rounded-lg focus:outline-none focus:border-profTeal"
            />
          </div>

          {/* Subject */}
          <select
            value={subject}
            onChange={e => { setSubject(e.target.value); setPage(1) }}
            className="px-3 py-2 text-sm border border-divider rounded-lg focus:outline-none focus:border-profTeal bg-white"
          >
            {SUBJECTS.map(s => <option key={s}>{s}</option>)}
          </select>

          {/* Price range */}
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-medGrey flex-shrink-0" />
            <input
              value={minPrice}
              onChange={e => { setMinPrice(e.target.value); setPage(1) }}
              placeholder="Min"
              type="number"
              className="w-20 px-2 py-2 text-sm border border-divider rounded-lg focus:outline-none focus:border-profTeal"
            />
            <span className="text-medGrey text-sm">–</span>
            <input
              value={maxPrice}
              onChange={e => { setMaxPrice(e.target.value); setPage(1) }}
              placeholder="Max"
              type="number"
              className="w-20 px-2 py-2 text-sm border border-divider rounded-lg focus:outline-none focus:border-profTeal"
            />
          </div>

          <button
            onClick={() => load(page)}
            className="px-4 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {/* Stats bar */}
      {result && (
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-medGrey">
            <span className="font-semibold text-charcoal">{result.total}</span> open jobs
            {search && ` · ${filtered.length} matching "${search}"`}
          </p>
          {totalPages > 1 && (
            <p className="text-sm text-medGrey">Page {page} of {totalPages}</p>
          )}
        </div>
      )}

      {/* Job cards */}
      {loading ? (
        <div className="flex items-center gap-3 text-medGrey py-20 justify-center">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading jobs…
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-divider rounded-xl py-20 text-center text-medGrey">
          <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No jobs found</p>
          <p className="text-sm mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(job => {
            const t = timeLeft(job.deadline)
            return (
              <div
                key={job.id}
                className="bg-white border border-divider rounded-xl p-5 flex flex-col hover:border-profTeal hover:shadow-sm transition-all cursor-pointer"
                onClick={() => router.push(`/jobs/${job.id}`)}
              >
                {/* Title + status */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h3 className="text-sm font-semibold text-charcoal leading-snug line-clamp-2 flex-1">
                    {job.title}
                  </h3>
                  <StatusBadge status={job.status} />
                </div>

                {/* Description */}
                <p className="text-xs text-medGrey leading-relaxed line-clamp-3 mb-4 flex-1">
                  {job.description}
                </p>

                {/* Meta */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {job.subject && (
                    <span className="flex items-center gap-1 px-2 py-1 bg-lightGrey rounded-lg text-[11px] text-charcoal font-medium">
                      <BookOpen className="w-3 h-3 text-profTeal" /> {job.subject}
                    </span>
                  )}
                  {job.academic_level && (
                    <span className="px-2 py-1 bg-lightGrey rounded-lg text-[11px] text-charcoal font-medium">
                      {job.academic_level}
                    </span>
                  )}
                </div>

                {/* Price + deadline */}
                <div className="flex items-center justify-between pt-3 border-t border-divider">
                  <div className="flex items-center gap-1 text-profTeal font-bold">
                    <DollarSign className="w-4 h-4" />
                    <span>{Number(job.proposed_price).toFixed(2)}</span>
                  </div>
                  <div className={`flex items-center gap-1 text-xs font-medium ${t.urgent ? 'text-red-500' : 'text-medGrey'}`}>
                    <Clock className="w-3.5 h-3.5" /> {t.label}
                  </div>
                </div>

                {/* CTA */}
                <button
                  onClick={e => { e.stopPropagation(); router.push(`/jobs/${job.id}`) }}
                  className="mt-3 w-full py-2 bg-profTeal text-white rounded-lg text-xs font-semibold hover:bg-profDark transition-colors"
                >
                  View & Bid →
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-3">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 rounded-lg border border-divider hover:border-profTeal disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-medGrey">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-2 rounded-lg border border-divider hover:border-profTeal disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}
