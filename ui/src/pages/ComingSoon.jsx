/**
 * ComingSoon.jsx — Placeholder for pages under construction
 * Used by: /portfolios, /universe (model portfolios view)
 * Props: title, description, eta
 */

import NavBar from '../components/NavBar'
import { useNavigate } from 'react-router-dom'

export default function ComingSoon({
  title       = 'Coming Soon',
  description = 'This feature is currently being built.',
  eta         = 'Q3 2026',
}) {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar />
      <div style={{
        maxWidth: 480, margin: '0 auto', padding: '80px 24px',
        textAlign: 'center',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: 'rgba(201,168,76,0.1)', border: '0.5px solid rgba(201,168,76,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 20px', fontSize: 22,
        }}>🔧</div>
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em',
          textTransform: 'uppercase', color: '#c9a84c', marginBottom: 10 }}>
          In Development
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 500, margin: '0 0 12px' }}>{title}</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: '0 0 24px' }}>
          {description}
        </p>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          fontSize: 12, color: 'var(--text-muted)',
          background: 'var(--navy-800)', border: '0.5px solid var(--border)',
          borderRadius: 6, padding: '6px 16px', marginBottom: 28,
        }}>
          <span>📅</span> Expected: {eta}
        </div>
        <div>
          <button
            onClick={() => navigate(-1)}
            style={{
              background: 'none', border: '0.5px solid var(--border)',
              borderRadius: 6, color: 'var(--text-secondary)', fontSize: 13,
              padding: '8px 20px', cursor: 'pointer',
            }}
          >← Go back</button>
        </div>
      </div>
    </div>
  )
}
