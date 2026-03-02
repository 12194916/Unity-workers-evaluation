'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

export default function AuthPage() {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const supabase = createClient()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    if (mode === 'signup') {
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) {
        setError(error.message)
      } else {
        setSuccess('Account created! Check your email to confirm, then sign in.')
        setMode('signin')
      }
      setLoading(false)
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) {
        setError(error.message)
      } else {
        router.push('/dashboard')
      }
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {/* Left side — branding */}
      <div className="auth-left">
        <div className="auth-brand">
          <div className="logo">
            <div className="logo-icon">U</div>
            <div className="logo-text"><span>Unity</span></div>
          </div>
          <h2>Employee Evaluation Platform</h2>
          <p>
            Recognize and reward outstanding performance across your team.
            Vote for the best dispatchers, updaters, and more — every month.
          </p>

          <div className="auth-features">
            <div className="feature">
              <div className="feature-icon">📊</div>
              <span>Monthly performance polls with live results</span>
            </div>
            <div className="feature">
              <div className="feature-icon">🗳️</div>
              <span>Telegram-integrated voting for easy participation</span>
            </div>
            <div className="feature">
              <div className="feature-icon">📋</div>
              <span>Detailed voter tracking and historical analytics</span>
            </div>
            <div className="feature">
              <div className="feature-icon">🏆</div>
              <span>Custom categories — Best Dispatch, Best Update, and more</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right side — form */}
      <div className="auth-right">
        <h1>{mode === 'signin' ? 'Welcome back' : 'Create account'}</h1>
        <p className="subtitle">
          {mode === 'signin'
            ? 'Sign in to manage your employee evaluations'
            : 'Set up your admin account to get started'}
        </p>

        <div className="tab-switcher">
          <button
            className={mode === 'signin' ? 'active' : ''}
            onClick={() => { setMode('signin'); setError(''); setSuccess('') }}
          >
            Sign In
          </button>
          <button
            className={mode === 'signup' ? 'active' : ''}
            onClick={() => { setMode('signup'); setError(''); setSuccess('') }}
          >
            Sign Up
          </button>
        </div>

        {error && <p className="error-msg">{error}</p>}
        {success && <p className="success-msg">{success}</p>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@unity.com"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'signup' ? 'Create a password (min 6 chars)' : 'Your password'}
              minLength={6}
              required
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading
              ? (mode === 'signin' ? 'Signing in...' : 'Creating account...')
              : (mode === 'signin' ? 'Sign In' : 'Sign Up')
            }
          </button>
        </form>
      </div>
    </div>
  )
}
