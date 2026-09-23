import { useEffect, useState } from 'react'
import { supabase, isConfigured } from './supabaseClient'

const TABLE = 'contacts'

export default function App() {
  if (!isConfigured) {
    return (
      <main className="wrap">
        <h1>Contacts</h1>
        <p className="sub">React + Supabase · full CRUD · persistent history</p>
        <div className="card">
          <p className="error">Supabase is not configured.</p>
          <p className="muted">
            Create a <code>.env</code> file in <code>hm1/</code> (copy{' '}
            <code>.env.example</code>) with your <code>VITE_SUPABASE_URL</code> and{' '}
            <code>VITE_SUPABASE_ANON_KEY</code>, then restart <code>npm run dev</code>.
          </p>
        </div>
      </main>
    )
  }
  return <ContactsApp />
}

function ContactsApp() {
  const [name, setName] = useState('')
  const [contact, setContact] = useState('')
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)

  // READ
  async function load() {
    setLoading(true)
    setError('')
    const { data, error } = await supabase
      .from(TABLE)
      .select('*')
      .order('created_at', { ascending: false })
    if (error) setError(error.message)
    else setRows(data ?? [])
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  function resetForm() {
    setName('')
    setContact('')
    setEditingId(null)
  }

  // CREATE + UPDATE
  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const payload = { name: name.trim(), contact: contact.trim() }
    if (!payload.name || !payload.contact) {
      setError('Name and contact number are both required.')
      return
    }

    if (editingId) {
      const { error } = await supabase.from(TABLE).update(payload).eq('id', editingId)
      if (error) return setError(error.message)
    } else {
      const { error } = await supabase.from(TABLE).insert(payload)
      if (error) return setError(error.message)
    }
    resetForm()
    load()
  }

  // DELETE
  async function handleDelete(id) {
    if (!confirm('Delete this record?')) return
    const { error } = await supabase.from(TABLE).delete().eq('id', id)
    if (error) return setError(error.message)
    if (editingId === id) resetForm()
    load()
  }

  function startEdit(row) {
    setEditingId(row.id)
    setName(row.name)
    setContact(row.contact)
  }

  return (
    <main className="wrap">
      <h1>Contacts</h1>
      <p className="sub">React + Supabase · full CRUD · persistent history</p>

      <form onSubmit={handleSubmit} className="card">
        <div className="field">
          <label htmlFor="name">Name</label>
          <input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Jane Doe"
          />
        </div>
        <div className="field">
          <label htmlFor="contact">Contact number</label>
          <input
            id="contact"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            placeholder="+1 555 010 1234"
          />
        </div>
        <div className="actions">
          <button type="submit">{editingId ? 'Update' : 'Submit'}</button>
          {editingId && (
            <button type="button" className="ghost" onClick={resetForm}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {error && <p className="error">{error}</p>}

      <h2>History</h2>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="muted">No records yet.</p>
      ) : (
        <ul className="list">
          {rows.map((row) => (
            <li key={row.id} className="row">
              <div>
                <strong>{row.name}</strong>
                <span className="num">{row.contact}</span>
              </div>
              <div className="rowActions">
                <button className="ghost" onClick={() => startEdit(row)}>
                  Edit
                </button>
                <button className="danger" onClick={() => handleDelete(row.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
