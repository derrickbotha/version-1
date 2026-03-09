'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, ChevronLeft, ChevronRight, Shield, UserCheck, Ban, RefreshCw } from 'lucide-react'

interface AdminUser {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  status: string
  is_verified: boolean
  created_at: string
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

const ROLE_COLORS: Record<string, string> = {
  student: 'bg-purple-100 text-purple-700',
  researcher: 'bg-orange-100 text-orange-700',
  professor: 'bg-teal-100 text-teal-700',
  admin: 'bg-blue-100 text-blue-700',
  super_admin: 'bg-red-100 text-red-700',
}
const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  suspended: 'bg-yellow-100 text-yellow-700',
  deleted: 'bg-red-100 text-red-700',
}

export default function AdminUsers() {
  const router = useRouter()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [flash, setFlash] = useState('')

  async function load() {
    const token = localStorage.getItem('auth_token')
    if (!token) { router.push('/auth/login'); return }
    setLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: '20' })
    if (search) params.set('search', search)
    if (roleFilter) params.set('role', roleFilter)
    if (statusFilter) params.set('status', statusFilter)
    try {
      const res = await fetch(`${API}/admin/users?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 403) { router.push('/dashboard'); return }
      const data = await res.json()
      setUsers(data.data.items)
      setTotal(data.data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, roleFilter, statusFilter])

  async function verifyUser(userId: string) {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API}/admin/users/${userId}/verify`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) { setFlash('User verified'); load() }
  }

  async function suspendUser(userId: string) {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API}/admin/users/${userId}/suspend`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'Suspended by admin' }),
    })
    if (res.ok) { setFlash('User suspended'); load() }
  }

  async function unsuspendUser(userId: string) {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API}/admin/users/${userId}/unsuspend`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) { setFlash('User re-activated'); load() }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div className="p-8 max-w-7xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">User Management</h1>
          <p className="text-medGrey text-sm mt-1">{total.toLocaleString()} total users</p>
        </div>
      </div>

      {flash && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          {flash}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="flex items-center gap-2 px-3 py-2 bg-white border border-divider rounded-lg flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-medGrey flex-shrink-0" />
          <input
            className="flex-1 text-sm outline-none text-charcoal placeholder:text-medGrey"
            placeholder="Search name or email..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
          />
        </div>
        <select
          className="px-3 py-2 bg-white border border-divider rounded-lg text-sm text-charcoal"
          value={roleFilter}
          onChange={e => { setRoleFilter(e.target.value); setPage(1) }}
        >
          <option value="">All Roles</option>
          <option value="student">Student</option>
          <option value="researcher">Researcher</option>
          <option value="professor">Professor</option>
          <option value="admin">Admin</option>
        </select>
        <select
          className="px-3 py-2 bg-white border border-divider rounded-lg text-sm text-charcoal"
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="deleted">Deleted</option>
        </select>
        <button onClick={load} className="px-3 py-2 bg-white border border-divider rounded-lg text-sm hover:bg-lightGrey transition-colors">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Table */}
      <div className="bg-white border border-divider rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-lightGrey border-b border-divider">
              <th className="text-left px-4 py-3 text-xs font-semibold text-medGrey uppercase">User</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-medGrey uppercase">Role</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-medGrey uppercase">Status</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-medGrey uppercase">Verified</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-medGrey uppercase">Joined</th>
              <th className="text-right px-4 py-3 text-xs font-semibold text-medGrey uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-divider">
            {loading ? (
              <tr><td colSpan={6} className="py-12 text-center text-medGrey">Loading...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="py-12 text-center text-medGrey">No users found</td></tr>
            ) : users.map(u => (
              <tr key={u.id} className="hover:bg-lightGrey/50 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-medium text-charcoal">{u.first_name} {u.last_name}</div>
                  <div className="text-xs text-medGrey">{u.email}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[u.role] || 'bg-gray-100 text-gray-700'}`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[u.status] || ''}`}>
                    {u.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {u.is_verified
                    ? <span className="text-green-600 text-xs font-medium">✓ Verified</span>
                    : <span className="text-medGrey text-xs">Unverified</span>
                  }
                </td>
                <td className="px-4 py-3 text-xs text-medGrey">
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    {!u.is_verified && (
                      <button
                        onClick={() => verifyUser(u.id)}
                        className="p-1.5 rounded hover:bg-green-50 text-green-600 transition-colors"
                        title="Verify user"
                      >
                        <UserCheck className="w-4 h-4" />
                      </button>
                    )}
                    {u.status === 'active' && (
                      <button
                        onClick={() => suspendUser(u.id)}
                        className="p-1.5 rounded hover:bg-yellow-50 text-yellow-600 transition-colors"
                        title="Suspend user"
                      >
                        <Shield className="w-4 h-4" />
                      </button>
                    )}
                    {u.status === 'suspended' && (
                      <button
                        onClick={() => unsuspendUser(u.id)}
                        className="p-1.5 rounded hover:bg-green-50 text-green-600 transition-colors"
                        title="Re-activate user"
                      >
                        <UserCheck className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-divider">
            <span className="text-xs text-medGrey">Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded border border-divider hover:bg-lightGrey disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded border border-divider hover:bg-lightGrey disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
