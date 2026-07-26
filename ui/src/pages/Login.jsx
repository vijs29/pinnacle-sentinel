import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiPost } from '../api/client'
import NavBar from '../components/NavBar'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await apiPost('/api/auth/login', { email, password })
      localStorage.setItem('token', data.token)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar hideBackHome />
      <div style={{ maxWidth: 400, margin: '60px auto', padding: '0 20px' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Log in</h1>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <input
            type="email" placeholder="Email" value={email} required
            onChange={e => setEmail(e.target.value)}
            style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--border)',
              background: 'var(--navy-700)', color: 'var(--text-primary)', fontSize: 14 }}
          />
          <input
            type="password" placeholder="Password" value={password} required
            onChange={e => setPassword(e.target.value)}
            style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--border)',
              background: 'var(--navy-700)', color: 'var(--text-primary)', fontSize: 14 }}
          />
          {error && <div style={{ color: '#e24b4a', fontSize: 13 }}>{error}</div>}
          <button type="submit" disabled={loading} style={{
            background: 'var(--gold-400)', color: '#000', border: 'none',
            borderRadius: 6, padding: '12px', fontWeight: 700, fontSize: 14,
            cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1,
          }}>
            {loading ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <div style={{ marginTop: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
          Don't have an account? <a href="/register" style={{ color: 'var(--gold-400)' }}>Sign up</a>
        </div>
      </div>
    </div>
  )
}
