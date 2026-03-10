'use client'

import { useEffect, useState } from 'react'
import { BookOpen, Plus, Pencil, Trash2, RefreshCw, X, CheckCircle } from 'lucide-react'
import { api, Assignment } from '@/lib/api'

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [loading, setLoading]         = useState(true)
  const [showForm, setShowForm]       = useState(false)
  const [editing, setEditing]         = useState<Assignment | null>(null)
  const [flash, setFlash]             = useState('')

  const empty: Partial<Assignment> = {
    title: '', description: '', subject: '', academic_level: '',
    rubric: '', review_required: false, suggested_price: undefined, deadline_hours: undefined,
  }
  const [form, setForm] = useState<Partial<Assignment>>(empty)

  async function load() {
    setLoading(true)
    try { setAssignments(await api.getAssignments()) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  function openNew()  { setForm(empty); setEditing(null); setShowForm(true)  }
  function openEdit(a: Assignment) { setForm(a); setEditing(a); setShowForm(true) }

  async function save() {
    try {
      if (editing) {
        await api.updateAssignment(editing.id, form)
      } else {
        await api.createAssignment(form)
      }
      setFlash(editing ? 'Assignment updated' : 'Assignment created')
      setShowForm(false)
      load()
    } catch (err: any) { setFlash(err.message) }
  }

  async function remove(id: string) {
    if (!confirm('Deactivate this assignment?')) return
    try { await api.deleteAssignment(id); load() }
    catch (err: any) { setFlash(err.message) }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Course Assignments</h1>
          <p className="text-medGrey text-sm mt-1">Templates students use to post jobs</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 bg-white border border-divider rounded-lg hover:bg-lightGrey transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={openNew}
            className="flex items-center gap-2 px-4 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark transition-colors"
          >
            <Plus className="w-4 h-4" /> New Assignment
          </button>
        </div>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />{flash}
        </div>
      )}

      {/* Form modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-divider">
              <h2 className="font-semibold text-charcoal">{editing ? 'Edit Assignment' : 'New Assignment'}</h2>
              <button onClick={() => setShowForm(false)} className="p-1 hover:bg-lightGrey rounded"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-6 space-y-4">
              {[
                { label: 'Title *', key: 'title', type: 'text', placeholder: 'e.g. Literature Review: ML Ethics' },
                { label: 'Subject *', key: 'subject', type: 'text', placeholder: 'e.g. Computer Science' },
                { label: 'Academic Level', key: 'academic_level', type: 'text', placeholder: 'e.g. Postgraduate' },
                { label: 'Suggested Price ($)', key: 'suggested_price', type: 'number', placeholder: '150' },
                { label: 'Deadline (hours)', key: 'deadline_hours', type: 'number', placeholder: '168' },
                { label: 'Min Quality Score (0–100)', key: 'min_quality_score', type: 'number', placeholder: '75' },
              ].map(({ label, key, type, placeholder }) => (
                <div key={key}>
                  <label className="block text-xs font-semibold text-charcoal mb-1.5">{label}</label>
                  <input
                    type={type}
                    placeholder={placeholder}
                    value={(form as any)[key] ?? ''}
                    onChange={e => setForm(f => ({ ...f, [key]: type === 'number' ? Number(e.target.value) || undefined : e.target.value }))}
                    className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal"
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1.5">Description *</label>
                <textarea rows={3} value={form.description ?? ''} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal resize-none" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-charcoal mb-1.5">Rubric (Markdown)</label>
                <textarea rows={5} value={form.rubric ?? ''} onChange={e => setForm(f => ({ ...f, rubric: e.target.value }))}
                  placeholder="## Grading Criteria&#10;1. Coverage (30pts)&#10;2. Critical Analysis (40pts)&#10;3. References (30pts)"
                  className="w-full px-3 py-2 border border-divider rounded-lg text-sm text-charcoal font-mono resize-none" />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.review_required ?? false}
                  onChange={e => setForm(f => ({ ...f, review_required: e.target.checked }))}
                  className="w-4 h-4 accent-profTeal" />
                <span className="text-sm text-charcoal">Require professor review before payment release</span>
              </label>
            </div>
            <div className="flex gap-3 px-6 py-4 border-t border-divider">
              <button onClick={() => setShowForm(false)} className="flex-1 py-2 border border-divider rounded-lg text-sm text-charcoal hover:bg-lightGrey transition-colors">
                Cancel
              </button>
              <button onClick={save} className="flex-1 py-2 bg-profTeal text-white rounded-lg text-sm font-medium hover:bg-profDark transition-colors">
                {editing ? 'Save Changes' : 'Create Assignment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="py-12 flex items-center justify-center gap-2 text-medGrey">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading…
        </div>
      ) : assignments.length === 0 ? (
        <div className="py-16 text-center">
          <BookOpen className="w-12 h-12 text-medGrey mx-auto mb-3 opacity-30" />
          <p className="text-charcoal font-medium">No assignments yet</p>
          <p className="text-medGrey text-sm mt-1">Create a template to help students post better jobs</p>
        </div>
      ) : (
        <div className="space-y-4">
          {assignments.map(a => (
            <div key={a.id} className={`bg-white border rounded-xl p-5 ${a.is_active ? 'border-divider' : 'border-divider opacity-50'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-charcoal truncate">{a.title}</h3>
                    {!a.is_active && <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">Inactive</span>}
                    {a.review_required && <span className="px-2 py-0.5 bg-profLight text-profTeal rounded-full text-xs font-medium">Review Required</span>}
                  </div>
                  <p className="text-sm text-medGrey line-clamp-2">{a.description}</p>
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-medGrey">
                    <span>Subject: <strong className="text-charcoal">{a.subject}</strong></span>
                    {a.academic_level && <span>Level: <strong className="text-charcoal">{a.academic_level}</strong></span>}
                    {a.suggested_price && <span>Price: <strong className="text-charcoal">${a.suggested_price}</strong></span>}
                    {a.deadline_hours && <span>Deadline: <strong className="text-charcoal">{a.deadline_hours}h</strong></span>}
                    {a.min_quality_score && <span>Min Score: <strong className="text-charcoal">{a.min_quality_score}/100</strong></span>}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button onClick={() => openEdit(a)} className="p-2 hover:bg-lightGrey rounded-lg text-medGrey hover:text-charcoal transition-colors">
                    <Pencil className="w-4 h-4" />
                  </button>
                  {a.is_active && (
                    <button onClick={() => remove(a.id)} className="p-2 hover:bg-red-50 rounded-lg text-medGrey hover:text-red-600 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
