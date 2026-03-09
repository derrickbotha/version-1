'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { PlusCircle, Clock, DollarSign, ChevronRight, Loader2 } from 'lucide-react'
import { getMyJobs, type JobData } from '@/lib/api'
import { formatCurrency, formatRelativeDate } from '@/lib/utils'

const statusColors: Record<string, string> = {
  open: 'bg-green-100 text-green-700',
  draft: 'bg-gray-100 text-gray-500',
  negotiation: 'bg-yellow-100 text-yellow-700',
  accepted: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-indigo-100 text-indigo-700',
  submitted: 'bg-purple-100 text-purple-700',
  revision_requested: 'bg-orange-100 text-orange-700',
  completed: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

export default function MyJobsPage() {
  const router = useRouter()
  const [jobs, setJobs] = useState<JobData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!localStorage.getItem('auth_token')) { router.push('/auth/login'); return }
    getMyJobs()
      .then(res => setJobs(res.data?.items || []))
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load jobs.'))
      .finally(() => setLoading(false))
  }, [router])

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[900px] mx-auto px-6 py-10">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-display text-3xl font-semibold text-charcoal">My Jobs</h1>
            <p className="text-medGrey mt-1 text-sm">All research assignments you&apos;ve posted</p>
          </div>
          <Link
            href="/jobs/new"
            className="flex items-center gap-2 bg-ctaBlue text-white text-sm font-semibold px-4 py-2.5 rounded-xl hover:bg-blue-600 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            Post New Job
          </Link>
        </motion.div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-5">{error}</div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-ctaBlue" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="bg-white rounded-2xl border border-divider p-12 text-center">
            <div className="w-16 h-16 bg-lightGrey rounded-full flex items-center justify-center mx-auto mb-4">
              <PlusCircle className="w-7 h-7 text-medGrey" />
            </div>
            <h3 className="font-display text-xl font-semibold text-charcoal mb-2">No jobs posted yet</h3>
            <p className="text-medGrey text-sm mb-5">Post your first research assignment to get started.</p>
            <Link href="/jobs/new" className="inline-flex items-center gap-2 bg-ctaBlue text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:bg-blue-600 transition-all">
              <PlusCircle className="w-4 h-4" /> Post a Job
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job, i) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="bg-white rounded-2xl border border-divider p-6 hover:border-steelBlue/40 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h3 className="font-display text-lg font-semibold text-charcoal">{job.title}</h3>
                  <span className={`flex-shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${statusColors[job.status] || 'bg-gray-100 text-gray-600'}`}>
                    {job.status.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-sm text-medGrey mb-4 line-clamp-2">{job.description}</p>
                <div className="flex items-center gap-4 text-sm text-medGrey">
                  <span className="flex items-center gap-1"><DollarSign className="w-3.5 h-3.5" />{formatCurrency(Number(job.proposed_price))}</span>
                  <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{formatRelativeDate(job.deadline)}</span>
                  <span className="bg-lightGrey text-xs text-charcoal font-medium px-2.5 py-1 rounded-full">{job.subject}</span>
                </div>
                <Link
                  href={`/jobs/${job.id}`}
                  className="mt-4 flex items-center justify-end gap-1 text-sm font-medium text-ctaBlue hover:text-steelBlue transition-colors"
                >
                  View Bids <ChevronRight className="w-4 h-4" />
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
