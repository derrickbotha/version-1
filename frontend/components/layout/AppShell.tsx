'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import Footer from './Footer'

interface StoredUser {
  id: string
  role: string
  first_name: string
  last_name?: string
  email?: string
}

// Pages that are always public (no sidebar even if logged in)
const PUBLIC_PATHS = ['/', '/auth/login', '/auth/register', '/blog', '/services']

function isPublicPath(pathname: string) {
  if (PUBLIC_PATHS.includes(pathname)) return true
  if (pathname.startsWith('/services/')) return true
  if (pathname.startsWith('/blog/')) return true
  return false
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [user, setUser] = useState<StoredUser | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const token = localStorage.getItem('auth_token')
    const userData = localStorage.getItem('user')
    if (token && userData) {
      try {
        setUser(JSON.parse(userData))
      } catch {
        setUser(null)
      }
    }
  }, [pathname]) // re-check on route change so login/logout reflects immediately

  // Don't render anything auth-dependent until mounted (avoids hydration mismatch)
  const isPublic = isPublicPath(pathname)
  const showSidebar = mounted && !isPublic && !!user

  if (!mounted) {
    // SSR / first paint: render public layout to avoid flicker
    return (
      <>
        <Navbar />
        <div className="pt-20">{children}</div>
        {isPublic && <Footer />}
      </>
    )
  }

  if (showSidebar) {
    return (
      <div className="flex min-h-screen bg-lightGrey">
        <Sidebar user={user!} />
        <main className="flex-1 pl-64 min-w-0">
          {children}
        </main>
      </div>
    )
  }

  // Logged-out or public page
  return (
    <>
      <Navbar />
      <div className="pt-20">{children}</div>
      {isPublic && <Footer />}
    </>
  )
}
