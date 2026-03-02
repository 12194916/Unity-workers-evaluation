'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'

export default function CategoriesPage() {
  const supabase = createClient()
  const [categories, setCategories] = useState([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadCategories() {
    const { data } = await supabase
      .from('categories')
      .select('*')
      .order('created_at', { ascending: true })
    setCategories(data || [])
    setLoading(false)
  }

  useEffect(() => {
    loadCategories()
  }, [])

  async function handleAdd(e) {
    e.preventDefault()
    if (!name.trim()) return
    setError('')

    const { error: err } = await supabase.from('categories').insert({ name: name.trim() })
    if (err) {
      setError(err.message)
    } else {
      setName('')
      loadCategories()
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this category? This will also delete its workers and polls.')) return

    const { error: err } = await supabase.from('categories').delete().eq('id', id)
    if (err) {
      setError(err.message)
    } else {
      loadCategories()
    }
  }

  return (
    <div>
      <h1>Categories</h1>

      <form className="inline-form" onSubmit={handleAdd}>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New category name (e.g. Best Dispatch)"
        />
        <button className="btn btn-primary" type="submit" style={{ flex: 'none', width: 'auto' }}>
          Add
        </button>
      </form>

      {error && <p className="error-msg">{error}</p>}

      {loading ? (
        <p className="loading">Loading...</p>
      ) : categories.length === 0 ? (
        <p className="empty">No categories yet. Add one above.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr key={cat.id}>
                  <td>{cat.name}</td>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {new Date(cat.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(cat.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
