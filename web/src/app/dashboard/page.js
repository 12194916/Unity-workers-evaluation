'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'

export default function DashboardPage() {
  const supabase = createClient()
  const [stats, setStats] = useState({ categories: 0, workers: 0, activePolls: 0, totalVotes: 0 })

  useEffect(() => {
    async function loadStats() {
      const [catRes, workRes, pollRes, voteRes] = await Promise.all([
        supabase.from('categories').select('id', { count: 'exact', head: true }),
        supabase.from('workers').select('id', { count: 'exact', head: true }),
        supabase.from('polls').select('id', { count: 'exact', head: true }).eq('status', 'active'),
        supabase.from('votes').select('id', { count: 'exact', head: true }),
      ])
      setStats({
        categories: catRes.count || 0,
        workers: workRes.count || 0,
        activePolls: pollRes.count || 0,
        totalVotes: voteRes.count || 0,
      })
    }
    loadStats()
  }, [])

  const cards = [
    { label: 'Categories', value: stats.categories, icon: '📁' },
    { label: 'Workers', value: stats.workers, icon: '🧑‍💼' },
    { label: 'Active Polls', value: stats.activePolls, icon: '🗳️' },
    { label: 'Total Votes', value: stats.totalVotes, icon: '🏆' },
  ]

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="stat-grid">
        {cards.map((c) => (
          <div key={c.label} className="stat-card">
            <div style={{ fontSize: 28, marginBottom: 8 }}>{c.icon}</div>
            <div className="stat-value">{c.value}</div>
            <div className="stat-label">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
