'use client'

import { useEffect, useState } from 'react'
import { Award, CheckCircle, XCircle, RefreshCw, AlertTriangle } from 'lucide-react'
import { api, Credential } from '@/lib/api'
import { fmtDate } from '@/lib/utils'

const TYPE_LABEL: Record<string, string> = {
  bachelors_degree:          "Bachelor's Degree",
  masters_degree:            "Master's Degree",
  phd:                       'PhD',
  postdoc:                   'Postdoc',
  professional_certification:'Professional Certification',
  publication:               'Publication',
  award:                     'Award',
  other:                     'Other',
}

export default function CredentialsPage() {
  const [creds, setCreds]       = useState<Credential[]>([])
  const [loading, setLoading]   = useState(true)
  const [flash, setFlash]       = useState('')
  const [actioning, setActioning] = useState<string | null>(null)
  const [rejectId, setRejectId]   = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  async function load() {
    setLoading(true)
    try { setCreds(await api.getPendingCredentials()) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function verify(id: string) {
    setActioning(id)
    try {
      await api.actionCredential(id, 'verify')
      setFlash('Credential verified ✓')
      load()
    } catch (err: any) { setFlash(err.message) }
    finally { setActioning(null) }
  }

  async function reject() {
    if (!rejectId || !rejectReason.trim()) return
    setActioning(rejectId)
    try {
      await api.actionCredential(rejectId, 'reject', rejectReason)
      setFlash('Credential rejected')
      setRejectId(null)
      setRejectReason('')
      load()
    } catch (err: any) { setFlash(err.message) }
    finally { setActioning(null) }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Credential Verification</h1>
          <p className="text-medGrey text-sm mt-1">{creds.length} pending credentials to review</p>
        </div>
        <button onClick={load} className="p-2 bg-white border border-divider rounded-lg hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">{flash}</div>
      )}

      {/* Reject modal */}
      {rejectId && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold text-charcoal mb-3">Rejection Reason</h3>
            <p className="text-sm text-medGrey mb-3">Please provide a clear reason for rejecting this credential.</p>
            <textarea
              rows={4}
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              placeholder="e.g. Document appears to be altered. Please resubmit a clear copy."
              className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => { setRejectId(null); setRejectReason('') }}
                className="flex-1 py-2 border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors">
                Cancel
              </button>
              <button onClick={reject} disabled={!rejectReason.trim() || !!actioning}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors">
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading…
        </div>
      ) : creds.length === 0 ? (
        <div className="py-16 text-center">
          <Award className="w-12 h-12 text-medGrey mx-auto mb-3 opacity-30" />
          <p className="text-charcoal font-medium">No pending credentials</p>
          <p className="text-medGrey text-sm mt-1">All researcher credentials have been actioned</p>
        </div>
      ) : (
        <div className="space-y-4">
          {creds.map(c => (
            <div key={c.id} className="bg-white border border-divider rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                      {TYPE_LABEL[c.credential_type] ?? c.credential_type}
                    </span>
                    <span className="text-xs text-medGrey">
                      Submitted {fmtDate(c.created_at)}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-charcoal">{c.institution_name}</div>
                  {c.field_of_study && <div className="text-sm text-medGrey">{c.field_of_study}</div>}
                  {c.year_obtained && <div className="text-xs text-medGrey">Year: {c.year_obtained}</div>}
                  <div className="text-xs text-medGrey mt-1">
                    Researcher ID: <span className="font-mono">{c.researcher_id.slice(0,8)}…</span>
                  </div>
                  {c.document_url && (
                    <a href={c.document_url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-profTeal underline mt-1 inline-block">
                      View Document →
                    </a>
                  )}
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => verify(c.id)}
                    disabled={!!actioning}
                    className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    <CheckCircle className="w-4 h-4" /> Verify
                  </button>
                  <button
                    onClick={() => { setRejectId(c.id); setRejectReason('') }}
                    disabled={!!actioning}
                    className="flex items-center gap-1.5 px-4 py-2 bg-white border border-divider text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
