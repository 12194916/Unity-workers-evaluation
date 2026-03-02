'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'

export default function WorkersPage() {
  const supabase = createClient()
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [workers, setWorkers] = useState([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadCategories() {
      const { data } = await supabase
        .from('categories')
        .select('*')
        .order('created_at', { ascending: true })
      setCategories(data || [])
      if (data && data.length > 0) {
        setSelectedCategory(data[0].id)
      }
      setLoading(false)
    }
    loadCategories()
  }, [])

  useEffect(() => {
    if (selectedCategory) loadWorkers()
  }, [selectedCategory])

  async function loadWorkers() {
    const { data } = await supabase
      .from('workers')
      .select('*')
      .eq('category_id', selectedCategory)
      .order('created_at', { ascending: true })
    setWorkers(data || [])
  }

  async function handleAdd(e) {
    e.preventDefault()
    if (!name.trim() || !selectedCategory) return
    setError('')

    const { error: err } = await supabase
      .from('workers')
      .insert({ name: name.trim(), category_id: selectedCategory })

    if (err) {
      setError(err.message)
    } else {
      setName('')
      loadWorkers()
    }
  }

  async function handleDelete(id) {
    if (!confirm('Remove this worker?')) return

    const { error: err } = await supabase.from('workers').delete().eq('id', id)
    if (err) {
      setError(err.message)
    } else {
      loadWorkers()
    }
  }

  return (
    <div>
      <h1>Workers</h1>

      {loading ? (
        <p className="loading">Loading...</p>
      ) : categories.length === 0 ? (
        <p className="empty">
          No categories found. <a href="/dashboard/categories">Create one first.</a>
        </p>
      ) : (
        <>
          <div className="form-group" style={{ maxWidth: 300, marginBottom: 20 }}>
            <label>Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          <form className="inline-form" onSubmit={handleAdd}>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Worker name"
            />
            <button className="btn btn-primary" type="submit" style={{ flex: 'none', width: 'auto' }}>
              Add Worker
            </button>
          </form>

          {error && <p className="error-msg">{error}</p>}

          {workers.length === 0 ? (
            <p className="empty">No workers in this category yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Added</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {workers.map((w) => (
                    <tr key={w.id}>
                      <td>{w.name}</td>
                      <td style={{ color: 'var(--text-muted)' }}>
                        {new Date(w.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(w.id)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
