'use client'

import { useEffect, useState } from 'react'
import { User, Save, RefreshCw, CheckCircle, AlertTriangle, Plus, X } from 'lucide-react'
import { api, ProfProfile } from '@/lib/api'

const STATUS_STYLE: Record<string, string> = {
  pending:   'bg-yellow-100 text-yellow-700',
  approved:  'bg-green-100 text-green-700',
  rejected:  'bg-red-100 text-red-700',
  suspended: 'bg-gray-100 text-gray-600',
}

export default function AccountPage() {
  const [profile, setProfile]   = useState<ProfProfile | null>(null)
  const [loading, setLoading]   = useState(true)
  const [saving,  setSaving]    = useState(false)
  const [flash,   setFlash]     = useState('')
  const [error,   setError]     = useState('')

  /* editable fields */
  const [bio,           setBio]           = useState('')
  const [institution,   setInstitution]   = useState('')
  const [title,         setTitle]         = useState('')
  const [expertise,     setExpertise]     = useState<string[]>([])
  const [subjects,      setSubjects]      = useState<string[]>([])
  const [feePerJob,     setFeePerJob]     = useState<number>(25)
  const [expertiseInput, setExpertiseInput] = useState('')
  const [subjectInput,   setSubjectInput]   = useState('')

  async function load() {
    setLoading(true)
    try {
      const p = await api.getProfile()
      setProfile(p)
      setBio(p.bio ?? '')
      setInstitution('')
      setTitle(p.title ?? '')
      setExpertise(p.expertise_areas ?? [])
      setSubjects(p.review_subjects ?? [])
      setFeePerJob(p.review_fee_per_job ?? 25)
    } catch {
      /* profile may not exist yet */
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function save() {
    setSaving(true)
    setError('')
    try {
      if (profile) {
        await api.updateProfile({
          bio,
          title: title || undefined,
          expertise_areas: expertise,
          review_subjects: subjects,
          review_fee_per_job: feePerJob,
        })
      } else {
        await api.createProfile({
          bio,
          title: title || undefined,
          expertise_areas: expertise,
          review_subjects: subjects,
          review_fee_per_job: feePerJob,
        })
      }
      setFlash('Profile saved successfully')
      load()
    } catch (err: any) {
      setError(err.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  function addExpertise() {
    const v = expertiseInput.trim()
    if (v && !expertise.includes(v)) setExpertise(ex => [...ex, v])
    setExpertiseInput('')
  }

  function addSubject() {
    const v = subjectInput.trim()
    if (v && !subjects.includes(v)) setSubjects(s => [...s, v])
    setSubjectInput('')
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">My Account</h1>
          <p className="text-medGrey text-sm mt-1">Manage your professor profile</p>
        </div>
        {profile && (
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_STYLE[profile.status] ?? 'bg-gray-100 text-gray-600'}`}>
            {profile.status.toUpperCase()}
          </span>
        )}
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />{flash}
        </div>
      )}

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />{error}
        </div>
      )}

      {!profile && !loading && (
        <div className="mb-5 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
          <strong>No profile yet.</strong> Fill in the form below to create your professor profile. An admin will review and approve it.
        </div>
      )}

      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading…
        </div>
      ) : (
        <div className="space-y-5">

          {/* Academic Title */}
          <div className="bg-white border border-divider rounded-xl p-5">
            <label className="block text-sm font-semibold text-charcoal mb-1.5">Academic Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. Associate Professor, Dr., Prof."
              className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal"
            />
          </div>

          {/* Institution */}
          {!profile && (
            <div className="bg-white border border-divider rounded-xl p-5">
              <label className="block text-sm font-semibold text-charcoal mb-1.5">Institution ID</label>
              <input
                type="text"
                value={institution}
                onChange={e => setInstitution(e.target.value)}
                placeholder="Institution UUID (optional)"
                className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal font-mono"
              />
              <p className="text-xs text-medGrey mt-1">Leave blank if your institution is not listed.</p>
            </div>
          )}

          {/* Bio */}
          <div className="bg-white border border-divider rounded-xl p-5">
            <label className="block text-sm font-semibold text-charcoal mb-1.5">Professional Bio</label>
            <textarea
              rows={4}
              value={bio}
              onChange={e => setBio(e.target.value)}
              placeholder="Briefly describe your academic background, research interests, and areas of expertise…"
              className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal resize-none"
            />
          </div>

          {/* Expertise Areas */}
          <div className="bg-white border border-divider rounded-xl p-5">
            <label className="block text-sm font-semibold text-charcoal mb-2">Expertise Areas</label>
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={expertiseInput}
                onChange={e => setExpertiseInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addExpertise())}
                placeholder="e.g. Machine Learning"
                className="flex-1 px-3 py-2 border border-divider rounded-lg text-sm text-charcoal"
              />
              <button
                type="button"
                onClick={addExpertise}
                className="px-3 py-2 bg-profTeal text-white rounded-lg text-sm hover:bg-profDark transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {expertise.map(e => (
                <span key={e} className="flex items-center gap-1 px-3 py-1 bg-profLight text-profTeal rounded-full text-xs font-medium">
                  {e}
                  <button onClick={() => setExpertise(ex => ex.filter(x => x !== e))} className="hover:text-profDark">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              {expertise.length === 0 && <span className="text-xs text-medGrey">No expertise areas added yet</span>}
            </div>
          </div>

          {/* Review Subjects */}
          <div className="bg-white border border-divider rounded-xl p-5">
            <label className="block text-sm font-semibold text-charcoal mb-2">Review Subjects</label>
            <p className="text-xs text-medGrey mb-2">Subjects you are qualified to review student work in</p>
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={subjectInput}
                onChange={e => setSubjectInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addSubject())}
                placeholder="e.g. Computer Science"
                className="flex-1 px-3 py-2 border border-divider rounded-lg text-sm text-charcoal"
              />
              <button
                type="button"
                onClick={addSubject}
                className="px-3 py-2 bg-profTeal text-white rounded-lg text-sm hover:bg-profDark transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {subjects.map(s => (
                <span key={s} className="flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                  {s}
                  <button onClick={() => setSubjects(sub => sub.filter(x => x !== s))} className="hover:text-blue-900">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              {subjects.length === 0 && <span className="text-xs text-medGrey">No review subjects added yet</span>}
            </div>
          </div>

          {/* Review Fee */}
          <div className="bg-white border border-divider rounded-xl p-5">
            <label className="block text-sm font-semibold text-charcoal mb-1.5">
              Review Fee per Job: <span className="text-profTeal font-bold">${feePerJob}</span>
            </label>
            <input
              type="range" min={5} max={200} step={5} value={feePerJob}
              onChange={e => setFeePerJob(Number(e.target.value))}
              className="w-full accent-profTeal"
            />
            <div className="flex justify-between text-xs text-medGrey mt-1">
              <span>$5 minimum</span>
              <span>$200 maximum</span>
            </div>
          </div>

          {/* Save */}
          <button
            onClick={save}
            disabled={saving}
            className="w-full py-3 bg-profTeal text-white rounded-xl font-semibold text-sm hover:bg-profDark disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving…' : profile ? 'Save Changes' : 'Create Profile'}
          </button>

          {/* Profile status info */}
          {profile?.status === 'pending' && (
            <div className="px-4 py-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
              <strong>Pending approval.</strong> Your profile is awaiting admin review. You will be notified once approved.
            </div>
          )}
          {profile?.status === 'rejected' && (
            <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <strong>Profile rejected.</strong> Please update your information and save to re-submit for review.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
