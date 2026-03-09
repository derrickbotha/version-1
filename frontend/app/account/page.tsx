'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { User, Mail, MapPin, Shield, BookOpen, Loader2, CheckCircle, AlertCircle, ChevronRight } from 'lucide-react'
import {
  getAccount, updateProfile, updateContact, updateLocation, changePassword,
  updateStudentProfile, updateResearcherProfile,
  type AccountData,
} from '@/lib/api'

type Tab = 'profile' | 'contact' | 'location' | 'security' | 'role'

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'profile',  label: 'Profile',   icon: User    },
  { id: 'contact',  label: 'Contact',   icon: Mail    },
  { id: 'location', label: 'Location',  icon: MapPin  },
  { id: 'security', label: 'Security',  icon: Shield  },
  { id: 'role',     label: 'My Details', icon: BookOpen },
]

const inputClass = 'w-full border border-divider rounded-lg px-4 py-3 text-sm text-charcoal placeholder:text-medGrey/60 outline-none focus:border-steelBlue focus:ring-2 focus:ring-steelBlue/20 transition-all bg-white'
const labelClass = 'block text-sm font-medium text-charcoal mb-1.5'

function Alert({ type, msg }: { type: 'success' | 'error'; msg: string }) {
  return (
    <div className={`flex items-center gap-2 text-sm px-4 py-3 rounded-lg mb-4 ${type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'}`}>
      {type === 'success' ? <CheckCircle className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
      {msg}
    </div>
  )
}

export default function AccountPage() {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('profile')
  const [account, setAccount] = useState<AccountData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  // Profile tab
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName]   = useState('')
  const [phone, setPhone]         = useState('')
  const [whatsapp, setWhatsapp]   = useState('')

  // Contact tab
  const [email, setEmail] = useState('')

  // Location tab
  const [country, setCountry]     = useState('')
  const [city, setCity]           = useState('')
  const [postal, setPostal]       = useState('')
  const [timezone, setTimezone]   = useState('')

  // Security tab
  const [curPwd, setCurPwd]   = useState('')
  const [newPwd, setNewPwd]   = useState('')
  const [confPwd, setConfPwd] = useState('')

  // Role-specific
  const [university, setUniversity]     = useState('')
  const [degreeProgram, setDegreeProgram] = useState('')
  const [bio, setBio]                   = useState('')
  const [expertise, setExpertise]       = useState('')

  useEffect(() => {
    if (!localStorage.getItem('auth_token')) { router.push('/auth/login'); return }
    getAccount().then(res => {
      const d = res.data
      setAccount(d)
      setFirstName(d.profile.first_name)
      setLastName(d.profile.last_name)
      setPhone(d.profile.phone ?? '')
      setWhatsapp(d.profile.whatsapp_number ?? '')
      setEmail(d.profile.email)
      setCountry(d.student_profile?.country ?? '')
      setUniversity(d.student_profile?.university ?? '')
      setDegreeProgram(d.student_profile?.degree_program ?? '')
      setBio(d.researcher_profile?.bio ?? '')
      setExpertise((d.researcher_profile?.expertise ?? []).join(', '))
    }).catch(() => router.push('/auth/login')).finally(() => setLoading(false))
  }, [router])

  function flash(type: 'success' | 'error', msg: string) {
    setAlert({ type, msg })
    setTimeout(() => setAlert(null), 4000)
  }

  async function save(fn: () => Promise<unknown>) {
    setSaving(true)
    try {
      await fn()
      flash('success', 'Saved successfully.')
      const res = await getAccount()
      setAccount(res.data)
    } catch (err) {
      flash('error', err instanceof Error ? err.message : 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-ctaBlue" />
    </div>
  )
  if (!account) return null

  const isStudent    = account.profile.role === 'student'
  const isResearcher = account.profile.role === 'researcher'

  return (
    <div className="min-h-screen bg-lightGrey">
      <div className="max-w-[1000px] mx-auto px-6 py-10">
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <h1 className="font-display text-3xl font-semibold text-charcoal mb-1">Account Settings</h1>
          <p className="text-medGrey text-sm mb-8">Manage your profile, contact info, and security settings.</p>

          <div className="flex flex-col lg:flex-row gap-6">
            {/* Sidebar nav */}
            <nav className="w-full lg:w-56 flex-shrink-0">
              <div className="bg-white rounded-2xl border border-divider overflow-hidden">
                {TABS.map(t => (
                  <button
                    key={t.id}
                    onClick={() => { setTab(t.id); setAlert(null) }}
                    className={`flex items-center gap-3 w-full px-4 py-3.5 text-sm font-medium transition-colors text-left border-b border-divider last:border-0 ${tab === t.id ? 'bg-blue-50 text-ctaBlue' : 'text-charcoal hover:bg-lightGrey'}`}
                  >
                    <t.icon className="w-4 h-4 flex-shrink-0" />
                    {t.label}
                    {tab === t.id && <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-40" />}
                  </button>
                ))}
              </div>

              {/* User card */}
              <div className="mt-4 bg-white rounded-2xl border border-divider p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-steelBlue/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-steelBlue font-semibold">{account.profile.first_name[0]?.toUpperCase()}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-charcoal truncate">{account.profile.first_name} {account.profile.last_name}</p>
                    <p className="text-xs text-medGrey capitalize">{account.profile.role}</p>
                    {account.profile.is_verified && (
                      <span className="text-[10px] text-green-600 font-medium">✓ Verified</span>
                    )}
                  </div>
                </div>
              </div>
            </nav>

            {/* Tab content */}
            <div className="flex-1 bg-white rounded-2xl border border-divider p-6">
              {alert && <Alert type={alert.type} msg={alert.msg} />}

              {/* Profile */}
              {tab === 'profile' && (
                <div>
                  <h2 className="font-semibold text-charcoal mb-5">Profile Information</h2>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className={labelClass}>First Name</label>
                      <input className={inputClass} value={firstName} onChange={e => setFirstName(e.target.value)} />
                    </div>
                    <div>
                      <label className={labelClass}>Last Name</label>
                      <input className={inputClass} value={lastName} onChange={e => setLastName(e.target.value)} />
                    </div>
                  </div>
                  <div className="mb-4">
                    <label className={labelClass}>Phone</label>
                    <input className={inputClass} value={phone} onChange={e => setPhone(e.target.value)} placeholder="+1 555 000 0000" />
                  </div>
                  <div className="mb-6">
                    <label className={labelClass}>WhatsApp Number</label>
                    <input className={inputClass} value={whatsapp} onChange={e => setWhatsapp(e.target.value)} placeholder="+1 555 000 0000" />
                  </div>
                  <button
                    onClick={() => save(() => updateProfile({ first_name: firstName, last_name: lastName, phone: phone || undefined, whatsapp_number: whatsapp || undefined }))}
                    disabled={saving}
                    className="bg-ctaBlue text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center gap-2"
                  >
                    {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Save Profile
                  </button>
                </div>
              )}

              {/* Contact */}
              {tab === 'contact' && (
                <div>
                  <h2 className="font-semibold text-charcoal mb-1">Contact Information</h2>
                  <p className="text-xs text-medGrey mb-5">Changing your email will require re-verification.</p>
                  <div className="mb-4">
                    <label className={labelClass}>Email Address</label>
                    <input type="email" className={inputClass} value={email} onChange={e => setEmail(e.target.value)} />
                  </div>
                  <div className="mb-4">
                    <label className={labelClass}>Phone</label>
                    <input className={inputClass} value={phone} onChange={e => setPhone(e.target.value)} placeholder="+1 555 000 0000" />
                  </div>
                  <div className="mb-6">
                    <label className={labelClass}>WhatsApp Number</label>
                    <input className={inputClass} value={whatsapp} onChange={e => setWhatsapp(e.target.value)} placeholder="+1 555 000 0000" />
                  </div>
                  <button
                    onClick={() => save(() => updateContact({ email, phone: phone || undefined, whatsapp_number: whatsapp || undefined }))}
                    disabled={saving}
                    className="bg-ctaBlue text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center gap-2"
                  >
                    {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Save Contact
                  </button>
                </div>
              )}

              {/* Location */}
              {tab === 'location' && (
                <div>
                  <h2 className="font-semibold text-charcoal mb-5">Location & Timezone</h2>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className={labelClass}>Country</label>
                      <input className={inputClass} value={country} onChange={e => setCountry(e.target.value)} placeholder="United States" />
                    </div>
                    <div>
                      <label className={labelClass}>City</label>
                      <input className={inputClass} value={city} onChange={e => setCity(e.target.value)} placeholder="New York" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div>
                      <label className={labelClass}>Postal Code</label>
                      <input className={inputClass} value={postal} onChange={e => setPostal(e.target.value)} placeholder="10001" />
                    </div>
                    <div>
                      <label className={labelClass}>Timezone</label>
                      <input className={inputClass} value={timezone} onChange={e => setTimezone(e.target.value)} placeholder="America/New_York" />
                    </div>
                  </div>
                  <button
                    onClick={() => save(() => updateLocation({ country: country || undefined, city: city || undefined, postal_code: postal || undefined, timezone: timezone || undefined }))}
                    disabled={saving}
                    className="bg-ctaBlue text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center gap-2"
                  >
                    {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Save Location
                  </button>
                </div>
              )}

              {/* Security */}
              {tab === 'security' && (
                <div>
                  <h2 className="font-semibold text-charcoal mb-5">Security Settings</h2>
                  <div className="mb-4">
                    <label className={labelClass}>Current Password</label>
                    <input type="password" className={inputClass} value={curPwd} onChange={e => setCurPwd(e.target.value)} />
                  </div>
                  <div className="mb-4">
                    <label className={labelClass}>New Password</label>
                    <input type="password" className={inputClass} value={newPwd} onChange={e => setNewPwd(e.target.value)} />
                    <p className="text-xs text-medGrey mt-1">Minimum 8 characters.</p>
                  </div>
                  <div className="mb-6">
                    <label className={labelClass}>Confirm New Password</label>
                    <input type="password" className={inputClass} value={confPwd} onChange={e => setConfPwd(e.target.value)} />
                    {confPwd && newPwd !== confPwd && (
                      <p className="text-xs text-red-500 mt-1">Passwords do not match.</p>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      if (newPwd !== confPwd) { flash('error', 'Passwords do not match.'); return }
                      save(() => changePassword({ current_password: curPwd, new_password: newPwd }))
                        .then(() => { setCurPwd(''); setNewPwd(''); setConfPwd('') })
                    }}
                    disabled={saving || !curPwd || !newPwd || newPwd !== confPwd}
                    className="bg-ctaBlue text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center gap-2"
                  >
                    {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Change Password
                  </button>

                  <div className="mt-8 border-t border-divider pt-6">
                    <h3 className="font-semibold text-charcoal mb-2 text-sm">Account Status</h3>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${account.profile.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {account.profile.status}
                      </span>
                      <span className="text-xs text-medGrey">Member since {new Date(account.profile.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Role details */}
              {tab === 'role' && (
                <div>
                  <h2 className="font-semibold text-charcoal mb-5">
                    {isStudent ? 'Student Profile' : 'Researcher Profile'}
                  </h2>

                  {isStudent && (
                    <>
                      <div className="mb-4">
                        <label className={labelClass}>University / Institution</label>
                        <input className={inputClass} value={university} onChange={e => setUniversity(e.target.value)} placeholder="e.g. MIT" />
                      </div>
                      <div className="mb-6">
                        <label className={labelClass}>Degree Program</label>
                        <input className={inputClass} value={degreeProgram} onChange={e => setDegreeProgram(e.target.value)} placeholder="e.g. BSc Computer Science" />
                      </div>
                      <button
                        onClick={() => save(() => updateStudentProfile({ university, degree_program: degreeProgram }))}
                        disabled={saving}
                        className="bg-ctaBlue text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center gap-2"
                      >
                        {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Save
                      </button>
                    </>
                  )}

                  {isResearcher && (
                    <>
                      <div className="mb-4">
                        <label className={labelClass}>Bio</label>
                        <textarea className={inputClass + ' h-28 resize-none'} value={bio} onChange={e => setBio(e.target.value)} placeholder="Tell students about your expertise and background..." />
                      </div>
                      <div className="mb-4">
                        <label className={labelClass}>Areas of Expertise</label>
                        <input className={inputClass} value={expertise} onChange={e => setExpertise(e.target.value)} placeholder="Machine Learning, Econometrics, Biostatistics" />
                        <p className="text-xs text-medGrey mt-1">Comma-separated list.</p>
                      </div>
                      <div className="flex items-center gap-4 mb-6">
                        <div className="bg-lightGrey rounded-xl px-4 py-3 text-center">
                          <p className="text-2xl font-bold text-ctaBlue">{account.researcher_profile?.rating?.toFixed(1) ?? '—'}</p>
                          <p className="text-xs text-medGrey">Rating</p>
                        </div>
                        <div className="bg-lightGrey rounded-xl px-4 py-3 text-center">
                          <p className="text-2xl font-bold text-ctaBlue">{account.researcher_profile?.total_jobs_completed ?? 0}</p>
                          <p className="text-xs text-medGrey">Jobs Done</p>
                        </div>
                      </div>
                      <button
                        onClick={() => save(() => updateResearcherProfile({ bio, expertise: expertise.split(',').map(s => s.trim()).filter(Boolean) }))}
                        disabled={saving}
                        className="bg-ctaBlue text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-600 disabled:opacity-60 transition-all flex items-center gap-2"
                      >
                        {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Save
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
