import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BASE_URL, authedFetch } from '../api/client'

const NAV_LINKS = [
  { path: '/screener', label: 'Screener', emphasize: true },
  { path: '/methodology', label: 'Methodology' },
  { path: '/watchlist', label: 'Watchlist' },
]

export default function NavBar({ subtitle, hideBackHome = false }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const storedToken = localStorage.getItem('token')
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (!storedToken) return
    authedFetch('/api/auth/me')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUser(data) })
      .catch(() => {})
  }, [])

  function handleLogout() {
    localStorage.clear()
    setUser(null)
    navigate('/login')
  }

  const GAP = 20

  return (
    <div style={{
      borderBottom: '1px solid var(--border)',
      background: 'var(--navy-800)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '12px 24px 8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: GAP }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: GAP }}>
          {!hideBackHome && (
            <>
              <button onClick={() => navigate(-1)} title="Previous page" style={{
                background: 'none', color: 'var(--text-secondary)',
                border: 'none', padding: '4px 0', fontSize: 13, fontWeight: 500,
                cursor: 'pointer', whiteSpace: 'nowrap',
              }}>‹ Back</button>
              <button onClick={() => navigate('/')} title="Home" style={{
                background: 'none', color: 'var(--text-secondary)',
                border: 'none', padding: '4px 0', fontSize: 13, fontWeight: 500,
                cursor: 'pointer', whiteSpace: 'nowrap',
              }}>⌂ Home</button>
            </>
          )}
          <img src="/pinnacle-logo.svg" alt="Pinnacle Sentinel" style={{ height: 28 }} />
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 1, whiteSpace: 'nowrap' }}>
            <span style={{ color: 'var(--gold-400, #c9a84c)' }}>PINNACLE</span>
            {' '}
            <span style={{ color: '#d4443f' }}>SENTINEL</span>
          </div>
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: GAP }}>
          {NAV_LINKS.map(link => (
            <button
              key={link.path}
              onClick={() => navigate(link.path)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 13,
                fontWeight: (pathname === link.path || link.emphasize) ? 700 : 500,
                color: pathname === link.path
                  ? 'var(--gold-400)'
                  : link.emphasize ? 'var(--gold-300)' : 'var(--text-secondary)',
                padding: '4px 0',
                borderBottom: pathname === link.path ? '2px solid var(--gold-400)' : '2px solid transparent',
                transition: 'color 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {link.label}
            </button>
          ))}

          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                {user.first_name || user.email.split('@')[0]}
              </span>
              <button onClick={handleLogout} style={{
                background: 'none', border: '1px solid var(--border)', borderRadius: 6,
                padding: '4px 12px', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer',
              }}>Log out</button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <button onClick={() => navigate('/login')} style={{
                background: 'none', border: 'none', color: '#ffffff', fontSize: 13, cursor: 'pointer',
              }}>Log in</button>
              <button onClick={() => navigate('/register')} style={{
                background: 'var(--gold-400)', color: '#000', border: 'none',
                borderRadius: 6, padding: '4px 14px', fontWeight: 700, cursor: 'pointer', fontSize: 12,
              }}>Sign Up</button>
            </div>
          )}
        </div>
      </div>

      {subtitle && (
        <div style={{ marginTop: 6, fontSize: 11, color: '#ffffff' }}>{subtitle}</div>
      )}
    </div>
  )
}
