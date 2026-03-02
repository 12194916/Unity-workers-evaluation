'use client'

import { useRouter, usePathname } from 'next/navigation'
import { createClient } from '@/lib/supabase'

export default function DashboardLayout({ children }) {
  const router = useRouter()
  const pathname = usePathname()
  const supabase = createClient()

  async function handleLogout() {
    await supabase.auth.signOut()
    router.push('/')
  }

  const links = [
    { href: '/dashboard', label: 'Overview', icon: '📊' },
    { href: '/dashboard/categories', label: 'Categories', icon: '📁' },
    { href: '/dashboard/workers', label: 'Workers', icon: '🧑‍💼' },
    { href: '/dashboard/polls', label: 'Polls', icon: '🗳️' },
    { href: '/dashboard/results', label: 'Results', icon: '🏆' },
  ]

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="s-logo">U</div>
          <div className="s-name"><span>Unity</span></div>
        </div>
        <nav>
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className={pathname === link.href ? 'active' : ''}
            >
              <span>{link.icon}</span>
              {link.label}
            </a>
          ))}
        </nav>
        <button className="logout-btn" onClick={handleLogout}>
          Sign Out
        </button>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}
