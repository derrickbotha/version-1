'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Sidebar from './Sidebar'

interface StoredUser { id: string; email: string; first_name: string; last_name: string; role: string }

const PUBLIC = ['/auth/login']

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router   = useRouter()
  const [user, setUser]       = useState<StoredUser | null>(null)
  const [status, setStatus]   = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const token = localStorage.getItem('prof_token')
    const raw   = localStorage.getItem('prof_user')

    if (!token && !PUBLIC.includes(pathname)) {
      router.push('/auth/login')
      return
    }
    if (raw) {
      try { setUser(JSON.parse(raw)) } catch { /* ignore */ }
    }
    const prof = localStorage.getItem('prof_profile')
    if (prof) {
      try { setStatus(JSON.parse(prof).status) } catch { /* ignore */ }
    }
  }, [pathname])

  const isPublic = PUBLIC.includes(pathname)

  if (!mounted) return <div className="min-h-screen bg-lightGrey" />

  if (isPublic) return <>{children}</>

  return (
    <div className="flex min-h-screen bg-lightGrey">
      <Sidebar
        name={user ? `${user.first_name} ${user.last_name}` : ''}
        email={user?.email ?? ''}
        status={status}
      />
      <main className="flex-1 pl-64 min-w-0 min-h-screen">
        {children}
      </main>
    </div>
  )
}
