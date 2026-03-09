'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Search, Filter, Clock, DollarSign, ChevronRight, RefreshCw } from 'lucide-react'
import { getJobs } from '@/lib/api'
import { formatCurrency, formatRelativeDate } from '@/lib/utils'

interface Job {
  id: string
  title: string
  description: string
  subject: string
  academic_level: string
  deadline: string
  proposed_price: string
  status: string
  created_at: string
}

const statusColors: Record<string, string> = {
  open: 'bg-green-100 text-green-700',
  accepted: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-indigo-100 text-indigo-700',
  submitted: 'bg-purple-100 text-purple-700',
  revision_requested: 'bg-orange-100 text-orange-700',
  completed: 'bg-gray-100 text-gray-600',
  disputed: 'bg-red-100 text-red-600',
  cancelled: 'bg-gray-100 text-gray-500',
}

const statusLabels: Record<string, string> = {
  open: 'Open',
  accepted: 'Accepted',
  in_progress: 'In Progress',
  submitted: 'Submitted',
  revision_requested: 'Revision',
  completed: 'Completed',
  disputed: 'Disputed',
  cancelled: 'Cancelled',
}

function JobCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-divider p-6 animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <div className="h-5 w-3/5 bg-divider rounded" />
        <div className="h-5 w-16 bg-divider rounded-full" />
      </div>
      <div className="space-y-2 mb-4">
        <div className="h-3.5 w-full bg-divider rounded" />
        <div className="h-3.5 w-4/5 bg-divider rounded" />
      </div>
      <div className="flex gap-3">
        <div className="h-4 w-20 bg-divider rounded" />
        <div className="h-4 w-20 bg-divider rounded" />
        <div className="h-4 w-20 bg-divider rounded" />
      </div>
    </div>
  )
}

export default function MarketplacePage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState({
    status: '',
    subject: '',
    min_budget: '',
    max_budget: '',
  })

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params: Record<string, string | number> = {}
      if (filters.status) params.status = filters.status
      if (filters.subject) params.subject = filters.subject
      if (filters.min_budget) params.min_price = Number(filters.min_budget)
      if (filters.max_budget) params.max_price = Number(filters.max_budget)

      const res = await getJobs(params)
      setJobs((res.data?.items as Job[]) || [])
    } catch {
      setError('Unable to load jobs. Please try again.')
      // Show sample data in preview mode
      setJobs([])
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  const filteredJobs = jobs.filter((job) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      job.title.toLowerCase().includes(q) ||
      job.description.toLowerCase().includes(q) ||
      job.subject.toLowerCase().includes(q)
    )
  })

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[1280px] mx-auto px-6 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <p className="text-sm text-medGrey uppercase tracking-wide font-medium mb-1">
            Research Marketplace
          </p>
          <h1 className="font-display text-4xl font-semibold text-charcoal">Browse Jobs</h1>
          <p className="text-medGrey mt-2">
            Find research assignments that match your expertise and bid to work on them.
          </p>
        </motion.div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar Filters */}
          <motion.aside
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="w-full lg:w-[260px] flex-shrink-0"
          >
            <div className="bg-white rounded-2xl border border-divider p-6 sticky top-24">
              <div className="flex items-center gap-2 mb-5">
                <Filter className="w-4 h-4 text-medGrey" />
                <h2 className="font-semibold text-charcoal text-sm">Filters</h2>
              </div>

              {/* Status filter */}
              <div className="mb-5">
                <label className="block text-xs font-medium text-medGrey uppercase tracking-wide mb-2">
                  Status
                </label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
                  className="w-full border border-divider rounded-lg px-3 py-2.5 text-sm text-charcoal outline-none focus:border-steelBlue transition-colors bg-white"
                >
                  <option value="">All Status</option>
                  <option value="open">Open</option>
                  <option value="accepted">Accepted</option>
                  <option value="in_progress">In Progress</option>
                  <option value="submitted">Submitted</option>
                  <option value="revision_requested">Revision Requested</option>
                  <option value="completed">Completed</option>
                  <option value="disputed">Disputed</option>
                </select>
              </div>

              {/* Subject filter */}
              <div className="mb-5">
                <label className="block text-xs font-medium text-medGrey uppercase tracking-wide mb-2">
                  Subject
                </label>
                <select
                  value={filters.subject}
                  onChange={(e) => setFilters((f) => ({ ...f, subject: e.target.value }))}
                  className="w-full border border-divider rounded-lg px-3 py-2.5 text-sm text-charcoal outline-none focus:border-steelBlue transition-colors bg-white"
                >
                  <option value="">All Subjects</option>
                  <option value="Economics">Economics</option>
                  <option value="Computer Science">Computer Science</option>
                  <option value="Medicine">Medicine</option>
                  <option value="Law">Law</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Physics">Physics</option>
                  <option value="Literature">Literature</option>
                  <option value="Psychology">Psychology</option>
                  <option value="History">History</option>
                  <option value="Business">Business</option>
                </select>
              </div>

              {/* Price range */}
              <div className="mb-5">
                <label className="block text-xs font-medium text-medGrey uppercase tracking-wide mb-2">
                  Budget Range
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={filters.min_budget}
                    onChange={(e) => setFilters((f) => ({ ...f, min_budget: e.target.value }))}
                    placeholder="Min $"
                    className="w-full border border-divider rounded-lg px-3 py-2 text-sm outline-none focus:border-steelBlue transition-colors"
                  />
                  <span className="text-medGrey text-xs">–</span>
                  <input
                    type="number"
                    value={filters.max_budget}
                    onChange={(e) => setFilters((f) => ({ ...f, max_budget: e.target.value }))}
                    placeholder="Max $"
                    className="w-full border border-divider rounded-lg px-3 py-2 text-sm outline-none focus:border-steelBlue transition-colors"
                  />
                </div>
              </div>

              {/* Reset */}
              <button
                onClick={() => setFilters({ status: '', subject: '', min_budget: '', max_budget: '' })}
                className="w-full text-sm text-medGrey hover:text-charcoal border border-divider rounded-lg py-2.5 hover:bg-lightGrey transition-colors"
              >
                Reset Filters
              </button>
            </div>
          </motion.aside>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Search bar */}
            <div className="relative mb-5">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-medGrey" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search jobs by title, subject, or description..."
                className="w-full bg-white border border-divider rounded-xl pl-11 pr-4 py-3 text-sm outline-none focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20 transition-all"
              />
            </div>

            {/* Results count */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-medGrey">
                {loading ? 'Loading...' : `${filteredJobs.length} job${filteredJobs.length !== 1 ? 's' : ''} found`}
              </p>
              <button
                onClick={fetchJobs}
                className="flex items-center gap-1.5 text-sm text-medGrey hover:text-charcoal transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm px-4 py-3 rounded-lg mb-5">
                {error} Showing sample data below.
              </div>
            )}

            {/* Jobs grid */}
            {loading ? (
              <div className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <JobCardSkeleton key={i} />
                ))}
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="bg-white rounded-2xl border border-divider p-12 text-center">
                <div className="w-16 h-16 bg-lightGrey rounded-full flex items-center justify-center mx-auto mb-4">
                  <Search className="w-7 h-7 text-medGrey" />
                </div>
                <h3 className="font-display text-xl font-semibold text-charcoal mb-2">
                  No jobs found
                </h3>
                <p className="text-medGrey text-sm">
                  Try adjusting your filters or search query.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredJobs.map((job, i) => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: i * 0.06 }}
                    className="bg-white rounded-2xl border border-divider p-6 hover:border-steelBlue/40 hover:shadow-md transition-all duration-300"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
                      <h3 className="font-display text-lg font-semibold text-charcoal leading-snug">
                        {job.title}
                      </h3>
                      <span
                        className={`flex-shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${
                          statusColors[job.status] || 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {statusLabels[job.status] || job.status}
                      </span>
                    </div>

                    <p className="text-sm text-medGrey leading-relaxed mb-4 line-clamp-2">
                      {job.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 mb-4">
                      <span className="flex items-center gap-1.5 text-sm text-medGrey">
                        <DollarSign className="w-3.5 h-3.5" />
                        <span className="font-medium text-charcoal">{formatCurrency(Number(job.proposed_price))}</span>
                      </span>
                      <span className="flex items-center gap-1.5 text-sm text-medGrey">
                        <Clock className="w-3.5 h-3.5" />
                        {formatRelativeDate(job.deadline)}
                      </span>
                      <span className="bg-lightGrey text-xs text-charcoal font-medium px-2.5 py-1 rounded-full">
                        {job.academic_level}
                      </span>
                      <span className="bg-lightGrey text-xs text-charcoal font-medium px-2.5 py-1 rounded-full">
                        {job.subject}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-medGrey">{new Date(job.created_at).toLocaleDateString()}</span>
                      <Link
                        href={`/jobs/${job.id}`}
                        className="flex items-center gap-1.5 text-sm font-medium text-ctaBlue hover:text-steelBlue transition-colors"
                      >
                        View & Bid
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
