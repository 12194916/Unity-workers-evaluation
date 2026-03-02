'use client'

import { useEffect, useState, useCallback } from 'react'
import { createClient } from '@/lib/supabase'

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function ResultsPage() {
  const supabase = createClient()
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedPolls, setExpandedPolls] = useState({})

  const loadResults = useCallback(async () => {
    setLoading(true)

    // Get polls for the selected month
    const { data: polls } = await supabase
      .from('polls')
      .select('*, categories(name)')
      .eq('month', month)
      .eq('year', year)
      .order('created_at', { ascending: true })

    if (!polls || polls.length === 0) {
      setResults([])
      setLoading(false)
      return
    }

    // For each poll, get workers and votes
    const pollResults = await Promise.all(
      polls.map(async (poll) => {
        const [workersRes, votesRes] = await Promise.all([
          supabase
            .from('workers')
            .select('*')
            .eq('category_id', poll.category_id)
            .order('name', { ascending: true }),
          supabase
            .from('votes')
            .select('*, workers(name)')
            .eq('poll_id', poll.id)
            .order('voted_at', { ascending: false }),
        ])

        const workers = workersRes.data || []
        const votes = votesRes.data || []

        // Count votes per worker
        const voteCounts = {}
        const votersByWorker = {}
        workers.forEach((w) => {
          voteCounts[w.id] = 0
          votersByWorker[w.id] = []
        })

        votes.forEach((v) => {
          voteCounts[v.worker_id] = (voteCounts[v.worker_id] || 0) + 1
          if (!votersByWorker[v.worker_id]) votersByWorker[v.worker_id] = []
          votersByWorker[v.worker_id].push({
            username: v.voter_username,
            firstName: v.voter_first_name,
            telegramId: v.voter_telegram_id,
            votedAt: v.voted_at,
          })
        })

        const maxVotes = Math.max(...Object.values(voteCounts), 1)

        return {
          poll,
          categoryName: poll.categories?.name || 'Unknown',
          totalVotes: votes.length,
          workers: workers.map((w) => ({
            ...w,
            votes: voteCounts[w.id] || 0,
            percentage: maxVotes > 0 ? ((voteCounts[w.id] || 0) / maxVotes) * 100 : 0,
            voters: votersByWorker[w.id] || [],
          })).sort((a, b) => b.votes - a.votes),
        }
      })
    )

    setResults(pollResults)
    setLoading(false)
  }, [month, year])

  useEffect(() => {
    loadResults()
  }, [loadResults])

  // Real-time subscription for live vote updates
  useEffect(() => {
    const channel = supabase
      .channel('votes-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'votes' }, () => {
        loadResults()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [loadResults])

  function toggleExpand(pollId) {
    setExpandedPolls((prev) => ({ ...prev, [pollId]: !prev[pollId] }))
  }

  return (
    <div>
      <h1>Results — {MONTHS[month - 1]} {year}</h1>

      <div className="month-picker">
        <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
          {MONTHS.map((m, i) => (
            <option key={i} value={i + 1}>{m}</option>
          ))}
        </select>
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          min="2024"
          max="2099"
          style={{ width: 90 }}
        />
      </div>

      {loading ? (
        <p className="loading">Loading...</p>
      ) : results.length === 0 ? (
        <p className="empty">No polls found for {MONTHS[month - 1]} {year}.</p>
      ) : (
        results.map(({ poll, categoryName, totalVotes, workers }) => (
          <div className="poll-card" key={poll.id}>
            <h3>
              {categoryName}
              <span className={`status ${poll.status}`}>{poll.status}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: 13, marginLeft: 10 }}>
                {totalVotes} vote{totalVotes !== 1 ? 's' : ''}
              </span>
            </h3>

            {workers.length === 0 ? (
              <p className="empty" style={{ textAlign: 'left' }}>No workers in this category.</p>
            ) : (
              <>
                {workers.map((w) => (
                  <div className="vote-bar" key={w.id}>
                    <span className="name">{w.name}</span>
                    <div className="bar-bg">
                      <div className="bar-fill" style={{ width: `${w.percentage}%` }} />
                    </div>
                    <span className="count">{w.votes}</span>
                  </div>
                ))}

                <button className="voters-toggle" onClick={() => toggleExpand(poll.id)}>
                  {expandedPolls[poll.id] ? 'Hide voter details' : 'Show who voted'}
                </button>

                {expandedPolls[poll.id] && (
                  <div style={{ marginTop: 12 }}>
                    {workers.filter((w) => w.voters.length > 0).map((w) => (
                      <div key={w.id} style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
                          {w.name} ({w.votes} vote{w.votes !== 1 ? 's' : ''}):
                        </div>
                        <ul className="voters-list">
                          {w.voters.map((voter, i) => (
                            <li key={i}>
                              {voter.firstName || 'Unknown'}
                              {voter.username ? ` (@${voter.username})` : ''}
                              <span style={{ color: 'var(--border)', marginLeft: 8, fontSize: 12 }}>
                                {new Date(voter.votedAt).toLocaleString()}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                    {workers.every((w) => w.voters.length === 0) && (
                      <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No votes yet.</p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        ))
      )}
    </div>
  )
}
