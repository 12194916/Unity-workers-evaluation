'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function PollsPage() {
  const supabase = createClient()
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())
  const [categories, setCategories] = useState([])
  const [polls, setPolls] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    loadData()
  }, [month, year])

  async function loadData() {
    setLoading(true)
    setError('')
    setSuccess('')

    const [catRes, pollRes] = await Promise.all([
      supabase.from('categories').select('*').order('created_at', { ascending: true }),
      supabase.from('polls').select('*, categories(name)').eq('month', month).eq('year', year),
    ])

    setCategories(catRes.data || [])
    setPolls(pollRes.data || [])
    setLoading(false)
  }

  async function createPoll(categoryId) {
    setError('')
    setSuccess('')

    const { error: err } = await supabase.from('polls').insert({
      category_id: categoryId,
      month,
      year,
      status: 'active',
    })

    if (err) {
      if (err.message.includes('duplicate') || err.message.includes('unique')) {
        setError('A poll for this category already exists for this month.')
      } else {
        setError(err.message)
      }
    } else {
      setSuccess('Poll created! The bot will pick it up and post it in the group.')
      loadData()
    }
  }

  async function closePoll(pollId) {
    if (!confirm('Close this poll? Voting will stop.')) return
    setError('')

    const { error: err } = await supabase
      .from('polls')
      .update({ status: 'closed', closed_at: new Date().toISOString() })
      .eq('id', pollId)

    if (err) {
      setError(err.message)
    } else {
      loadData()
    }
  }

  async function reopenPoll(pollId) {
    setError('')

    // Clear old poll messages so bot sends fresh polls to all users
    await supabase.from('poll_messages').delete().eq('poll_id', pollId)

    const { error: err } = await supabase
      .from('polls')
      .update({ status: 'active', closed_at: null, broadcast_at: null, worker_ids_order: null })
      .eq('id', pollId)

    if (err) {
      setError(err.message)
    } else {
      setSuccess('Poll reopened! Bot will send it to all users shortly.')
      loadData()
    }
  }

  function getPollForCategory(categoryId) {
    return polls.find((p) => p.category_id === categoryId)
  }

  return (
    <div>
      <h1>Polls</h1>

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

      {error && <p className="error-msg">{error}</p>}
      {success && <p className="success-msg">{success}</p>}

      {loading ? (
        <p className="loading">Loading...</p>
      ) : categories.length === 0 ? (
        <p className="empty">
          No categories found. <a href="/dashboard/categories">Create categories first.</a>
        </p>
      ) : (
        <div>
          {categories.map((cat) => {
            const poll = getPollForCategory(cat.id)
            return (
              <div className="poll-card" key={cat.id}>
                <h3>
                  {cat.name}
                  {poll && (
                    <span className={`status ${poll.status}`}>
                      {poll.status}
                    </span>
                  )}
                </h3>

                {poll ? (
                  <div style={{ display: 'flex', gap: 10 }}>
                    {poll.status === 'active' ? (
                      <button className="btn btn-danger btn-sm" onClick={() => closePoll(poll.id)}>
                        Close Poll
                      </button>
                    ) : (
                      <button className="btn btn-primary btn-sm" onClick={() => reopenPoll(poll.id)}>
                        Reopen Poll
                      </button>
                    )}
                  </div>
                ) : (
                  <button className="btn btn-primary btn-sm" onClick={() => createPoll(cat.id)}>
                    Create Poll for {MONTHS[month - 1]} {year}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
