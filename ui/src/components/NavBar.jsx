import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BASE_URL, authedFetch } from '../api/client'

const NAV_LINKS = [
  { path: '/screener', label: 'Screener', emphasize: true },
  { path: '/methodology', label: 'Methodology' },
  { path: '/watchlist', label: 'Watchlist' },
]

const INFRA_LINKS = [
  { path: '/infrastructure?section=aws', label: 'AWS Services' },
  { path: '/infrastructure?section=containers', label: 'Docker & Containers' },
  { path: '/infrastructure?section=ansible', label: 'Ansible' },
  { path: '/infrastructure?section=terraform', label: 'Terraform' },
  { path: '/infrastructure?section=security', label: 'Security' },
  { path: '/infrastructure', label: 'Platform Overview' },
]

const SENTINEL_RED = '#d4443f'

export default function NavBar({ subtitle, hideBackHome = false }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const storedToken = localStorage.getItem('token')
  const [user, setUser] = useState(null)

  const [infraOpen, setInfraOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth <= 768 : false
  )
  const infraRef = useRef(null)

  useEffect(() => {
    if (!storedToken) return
    authedFetch('/api/auth/me')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUser(data) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    function onResize() { setIsMobile(window.innerWidth <= 768) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    function onOutside(e) {
      if (infraRef.current && !infraRef.current.contains(e.target)) setInfraOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
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
      padding: isMobile ? '10px 12px 8px' : '12px 24px 8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: GAP }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: GAP }}>
          {!hideBackHome && !isMobile && (
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
            <span style={{ color: SENTINEL_RED }}>SENTINEL</span>
          </div>
        </div>

        <div style={{ flex: 1 }} />

        {!isMobile && (
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

            <div ref={infraRef} style={{ position: 'relative' }}>
              <button onClick={() => setInfraOpen(o => !o)} style={{
                background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
                fontWeight: 500, color: 'var(--text-secondary)', padding: '4px 0',
                whiteSpace: 'nowrap',
              }}>Infrastructure ▾</button>
              {infraOpen && (
                <div style={{
                  position: 'absolute', top: '100%', right: 0, zIndex: 200,
                  background: 'var(--navy-800)', border: '1px solid var(--border-light)',
                  borderRadius: 6, padding: '4px 0', minWidth: 200, marginTop: 6,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
                }}>
                  {INFRA_LINKS.map(link => (
                    <button
                      key={link.path}
                      onClick={() => { navigate(link.path); setInfraOpen(false) }}
                      style={{
                        display: 'block', width: '100%', textAlign: 'left',
                        background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
                        color: 'var(--text-muted)', padding: '9px 16px',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--navy-700)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'none'}
                    >{link.label}</button>
                  ))}
                </div>
              )}
            </div>

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
        )}

        {isMobile && (
          <button
            onClick={() => setMobileOpen(o => !o)}
            aria-label="Menu"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-primary)', fontSize: 22, padding: '2px 6px', lineHeight: 1,
            }}
          >
            {mobileOpen ? '✕' : '☰'}
          </button>
        )}
      </div>

      {isMobile && mobileOpen && (
        <div style={{
          marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', gap: 2,
        }}>
          {!hideBackHome && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
              <button onClick={() => { navigate(-1); setMobileOpen(false) }} style={mobileLinkStyle}>‹ Back</button>
              <button onClick={() => { navigate('/'); setMobileOpen(false) }} style={mobileLinkStyle}>⌂ Home</button>
            </div>
          )}
          {NAV_LINKS.map(link => (
            <button
              key={link.path}
              onClick={() => { navigate(link.path); setMobileOpen(false) }}
              style={{
                ...mobileLinkStyle,
                color: pathname === link.path ? 'var(--gold-400)' : 'var(--text-secondary)',
                fontWeight: (pathname === link.path || link.emphasize) ? 700 : 500,
              }}
            >{link.label}</button>
          ))}

          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.5, color: 'var(--text-muted)', margin: '10px 0 4px', textTransform: 'uppercase' }}>
            Infrastructure
          </div>
          {INFRA_LINKS.map(link => (
            <button
              key={link.path}
              onClick={() => { navigate(link.path); setMobileOpen(false) }}
              style={{ ...mobileLinkStyle, color: 'var(--text-muted)' }}
            >{link.label}</button>
          ))}

          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {user.first_name || user.email.split('@')[0]}
                </span>
                <button onClick={() => { handleLogout(); setMobileOpen(false) }} style={{
                  background: 'none', border: '1px solid var(--border)', borderRadius: 6,
                  padding: '4px 12px', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer',
                }}>Log out</button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button onClick={() => { navigate('/login'); setMobileOpen(false) }} style={{
                  background: 'none', border: 'none', color: '#ffffff', fontSize: 13, cursor: 'pointer',
                }}>Log in</button>
                <button onClick={() => { navigate('/register'); setMobileOpen(false) }} style={{
                  background: 'var(--gold-400)', color: '#000', border: 'none',
                  borderRadius: 6, padding: '4px 14px', fontWeight: 700, cursor: 'pointer', fontSize: 12,
                }}>Sign Up</button>
              </div>
            )}
          </div>
        </div>
      )}

      {subtitle && !isMobile && (
        <div style={{ marginTop: 6, fontSize: 11, color: '#ffffff' }}>{subtitle}</div>
      )}
    </div>
  )
}

const mobileLinkStyle = {
  background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left',
  fontSize: 14, padding: '8px 0', whiteSpace: 'nowrap',
}
