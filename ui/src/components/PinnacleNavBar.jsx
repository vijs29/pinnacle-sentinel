/**
 * PinnacleNavBar — Canonical shared NavBar component
 * Location: pinnacle-infra/shared_content/PinnacleNavBar.jsx
 *
 * Sync to each product's ui/src/components/NavBar.jsx at deploy time.
 * Each product's NavBar.jsx is a thin wrapper that calls this component
 * with product-specific config.
 *
 * Props:
 *   product        {string}  'quant' | 'veridia' | 'sentinel'
 *   wordmark       {string}  e.g. 'QUANT', 'VERIDIA', 'SENTINEL'
 *   accentColor    {string}  CSS color string e.g. '#c9a84c'
 *   accentVar      {string}  CSS variable e.g. 'var(--gold-400)'
 *   logoSrc        {string}  Path to logo image e.g. '/pinnacle-logo.svg'
 *   navLinks       {Array}   Direct nav links [{path, label, emphasize?}]
 *   dropdowns      {Array}   Dropdown menus [{key, label, links: [{path, label}]}]
 *   accountLinks   {Array}   Links in account dropdown [{path, label, icon?}]
 *   subtitle       {string?} Optional subtitle below desktop nav
 *   hideBackHome   {bool}    Hide Back/Home buttons (use on Landing page)
 *   loginPath      {string}  e.g. '/login'
 *   registerPath   {string}  e.g. '/register'
 */

import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// ── Standard Infrastructure dropdown links (identical across all products) ──
export const STANDARD_INFRA_LINKS = [
  { path: '/infrastructure?section=ansible',    label: 'Ansible' },
  { path: '/infrastructure?section=terraform',  label: 'Terraform' },
  { path: '/infrastructure?section=containers', label: 'Docker & Containers' },
  { path: '/infrastructure?section=aws',        label: 'AWS Services' },
  { path: '/infrastructure?section=security',   label: 'Security' },
  { path: '/infrastructure',                    label: 'Platform Overview' },
  { path: '/platform-intelligence',             label: 'Platform Intelligence' },
]

// ── Token helpers ─────────────────────────────────────────────────────────────
function emailFromToken(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.email || payload.sub || null
  } catch { return null }
}

// ── Dropdown component ────────────────────────────────────────────────────────
function NavDropdown({ label, links, accentColor, isOpen, onToggle, onClose, pathname }) {
  const ref = useRef(null)

  useEffect(() => {
    function onOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [onClose])

  const isActive = links.some(l => pathname.startsWith(l.path.split('?')[0]))
  const navigate = useNavigate()

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={onToggle}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          fontSize: 13, padding: '4px 8px',
          color: isActive ? accentColor : 'var(--text-muted)',
          fontWeight: isActive ? 700 : 400,
        }}
      >{label} ▾</button>
      {isOpen && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, zIndex: 200,
          background: 'var(--navy-800)', border: '1px solid var(--border-light)',
          borderRadius: 6, padding: '4px 0', minWidth: 210, marginTop: 6,
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        }}>
          {links.map(link => (
            <button
              key={link.path + link.label}
              onClick={() => { navigate(link.path); onClose() }}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                background: pathname === link.path ? 'var(--navy-700)' : 'none',
                border: 'none', cursor: 'pointer', fontSize: 13,
                color: pathname === link.path ? accentColor : 'var(--text-muted)',
                padding: '9px 16px',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--navy-700)'}
              onMouseLeave={e => e.currentTarget.style.background = pathname === link.path ? 'var(--navy-700)' : 'none'}
            >{link.label}</button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function PinnacleNavBar({
  product      = 'quant',
  wordmark     = 'QUANT',
  accentColor  = '#c9a84c',
  accentVar    = 'var(--gold-400)',
  logoSrc      = '/pinnacle-logo.svg',
  navLinks     = [],
  dropdowns    = [],
  accountLinks = [],
  subtitle,
  hideBackHome = false,
  loginPath    = '/login',
  registerPath = '/register',
}) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  // ── Auth state ──────────────────────────────────────────────────────────────
  const storedToken = localStorage.getItem('token')
  const [isLoggedIn] = useState(!!storedToken)
  const [user, setUser]   = useState(null)

  useEffect(() => {
    if (!storedToken) return
    fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${storedToken}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUser(data) })
      .catch(() => {})
  }, [])

  // ── Display name ────────────────────────────────────────────────────────────
  const fallbackEmail = storedToken ? emailFromToken(storedToken) : null
  const displayName = user
    ? (user.first_name && user.last_name
        ? `${user.first_name} ${user.last_name}`
        : user.first_name || user.email?.split('@')[0] || fallbackEmail?.split('@')[0] || 'Account')
    : (fallbackEmail?.split('@')[0] || 'Account')
  const initials = displayName[0]?.toUpperCase() ?? '?'

  // ── Dropdown open state — one per dropdown key ─────────────────────────────
  const [openKey, setOpenKey]         = useState(null)
  const [accountOpen, setAccountOpen] = useState(null)
  const accountRef                    = useRef(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isMobile, setIsMobile]       = useState(
    typeof window !== 'undefined' ? window.innerWidth <= 768 : false
  )

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  // Close mobile menu on route change
  useEffect(() => { setMobileMenuOpen(false) }, [pathname])

  // Outside click for account dropdown
  useEffect(() => {
    function onOutside(e) {
      if (accountRef.current && !accountRef.current.contains(e.target)) setAccountOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [])

  function handleLogout() {
    localStorage.clear()
    setAccountOpen(false)
    navigate(loginPath)
  }

  // ── All links for mobile menu ───────────────────────────────────────────────
  const ALL_MOBILE_LINKS = [
    ...navLinks.map(l => ({ ...l, group: 'Main' })),
    ...dropdowns.flatMap(d => d.links.map(l => ({ ...l, group: d.label }))),
  ]

  const GAP = 18

  return (
    <div style={{
      borderBottom: '1px solid var(--border)',
      background: 'var(--navy-800)',
      position: 'sticky', top: 0, zIndex: 100,
      padding: isMobile ? '10px 12px 8px' : '12px 24px 8px',
    }}>

      {/* ── Mobile header row ─────────────────────────────────────────────── */}
      {isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
               onClick={() => navigate('/')}>
            <img src={logoSrc} alt={`Pinnacle ${wordmark}`} style={{ height: 24 }} />
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 1 }}>
              <span style={{ color: '#c9a84c' }}>PINNACLE </span>
              <span style={{ color: accentColor }}>{wordmark}</span>
            </div>
          </div>
          <button
            onClick={() => setMobileMenuOpen(o => !o)}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-primary)', fontSize: 22, padding: '4px 8px' }}
          >{mobileMenuOpen ? '✕' : '☰'}</button>
        </div>
      )}

      {/* ── Mobile full-screen overlay ────────────────────────────────────── */}
      {isMobile && mobileMenuOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'var(--navy-800)', zIndex: 999,
          overflowY: 'auto', padding: '16px 0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0 20px 16px', borderBottom: '0.5px solid var(--border-light)' }}>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 1 }}>
              <span style={{ color: '#c9a84c' }}>PINNACLE </span>
              <span style={{ color: accentColor }}>{wordmark}</span>
            </div>
            <button onClick={() => setMobileMenuOpen(false)}
              style={{ background: 'none', border: 'none', color: 'var(--text-primary)', fontSize: 22, cursor: 'pointer' }}>✕</button>
          </div>

          {/* Main links */}
          {navLinks.length > 0 && (
            <div style={{ padding: '12px 0', borderBottom: '0.5px solid var(--border-light)' }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase',
                color: 'var(--text-muted)', padding: '0 20px', marginBottom: 4 }}>Main</div>
              {navLinks.map(link => (
                <button key={link.path + link.label}
                  onClick={() => { navigate(link.path); setMobileMenuOpen(false) }}
                  style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none',
                    border: 'none', cursor: 'pointer', fontSize: 14,
                    color: pathname === link.path ? accentColor : 'var(--text-secondary)',
                    padding: '10px 20px' }}>
                  {link.label}
                </button>
              ))}
            </div>
          )}

          {/* Dropdown groups */}
          {dropdowns.map(d => (
            <div key={d.key} style={{ padding: '12px 0', borderBottom: '0.5px solid var(--border-light)' }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase',
                color: 'var(--text-muted)', padding: '0 20px', marginBottom: 4 }}>{d.label}</div>
              {d.links.map(link => (
                <button key={link.path + link.label}
                  onClick={() => { navigate(link.path); setMobileMenuOpen(false) }}
                  style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none',
                    border: 'none', cursor: 'pointer', fontSize: 14,
                    color: pathname === link.path ? accentColor : 'var(--text-secondary)',
                    padding: '10px 20px' }}>
                  {link.label}
                </button>
              ))}
            </div>
          ))}

          {/* Auth */}
          <div style={{ padding: '16px 20px' }}>
            {isLoggedIn ? (
              <button onClick={() => { handleLogout(); setMobileMenuOpen(false) }}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                  fontSize: 14, color: '#e24b4a', padding: 0 }}>
                ⏻ Logout
              </button>
            ) : (
              <button onClick={() => { navigate(registerPath); setMobileMenuOpen(false) }}
                style={{ background: accentColor, color: '#000', border: 'none',
                  borderRadius: 6, padding: '8px 20px', fontWeight: 700,
                  cursor: 'pointer', fontSize: 13 }}>
                Register free →
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Desktop nav row ───────────────────────────────────────────────── */}
      {!isMobile && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: GAP }}>

            {/* Back / Home */}
            {!hideBackHome && (
              <>
                <button onClick={() => navigate(-1)} style={{
                  background: 'none', color: 'var(--text-secondary)', border: 'none',
                  padding: '4px 0', fontSize: 13, fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap',
                }}>‹ Back</button>
                <button onClick={() => navigate('/')} style={{
                  background: 'none', color: 'var(--text-secondary)', border: 'none',
                  padding: '4px 0', fontSize: 13, fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap',
                }}>⌂ Home</button>
              </>
            )}

            {/* Wordmark */}
            <img src={logoSrc} alt={`Pinnacle ${wordmark}`} style={{ height: 28, flexShrink: 0 }} />
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 1, whiteSpace: 'nowrap' }}>
              <span style={{ color: '#c9a84c' }}>PINNACLE </span>
              <span style={{ color: accentColor }}>{wordmark}</span>
            </div>

            <div style={{ flex: 1 }} />

            {/* Dropdowns */}
            {dropdowns.map(d => (
              <NavDropdown
                key={d.key}
                label={d.label}
                links={d.links}
                accentColor={accentColor}
                isOpen={openKey === d.key}
                onToggle={() => setOpenKey(openKey === d.key ? null : d.key)}
                onClose={() => setOpenKey(null)}
                pathname={pathname}
              />
            ))}

            {/* Direct nav links */}
            {navLinks.map(link => (
              <button
                key={link.path}
                onClick={() => navigate(link.path)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
                  fontWeight: (pathname === link.path || link.emphasize) ? 700 : 500,
                  color: pathname === link.path
                    ? accentColor
                    : link.emphasize ? accentColor : 'var(--text-secondary)',
                  padding: '4px 0',
                  borderBottom: pathname === link.path ? `2px solid ${accentColor}` : '2px solid transparent',
                  transition: 'color 0.15s', whiteSpace: 'nowrap',
                }}
              >{link.label}</button>
            ))}
          </div>

          {/* Account row — below nav, flush right */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 6, minHeight: 24 }}>
            {subtitle && (
              <div style={{ flex: 1, fontSize: 11, color: 'var(--text-muted)' }}>{subtitle}</div>
            )}
            {isLoggedIn ? (
              <div ref={accountRef} style={{ position: 'relative' }}>
                <div
                  onClick={() => setAccountOpen(o => !o)}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
                >
                  <div style={{
                    width: 22, height: 22, borderRadius: '50%',
                    background: `linear-gradient(135deg, ${accentColor}, #d4af37)`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 800, color: '#000', flexShrink: 0,
                  }}>{initials}</div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>{displayName}</span>
                  <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>▾</span>
                </div>
                {accountOpen && (
                  <div style={{
                    position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                    background: 'var(--navy-700)', border: '1px solid var(--border)',
                    borderRadius: 8, overflow: 'hidden', minWidth: 160,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 200,
                  }}>
                    {accountLinks.map(link => (
                      <button
                        key={link.path}
                        onClick={() => { navigate(link.path); setAccountOpen(false) }}
                        style={{ display: 'block', width: '100%', padding: '10px 16px',
                          background: 'none', border: 'none', textAlign: 'left',
                          fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--navy-600)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'none'}
                      >{link.icon && `${link.icon} `}{link.label}</button>
                    ))}
                    <div style={{ borderTop: '1px solid var(--border)' }}>
                      <button
                        onClick={handleLogout}
                        style={{ display: 'block', width: '100%', padding: '10px 16px',
                          background: 'none', border: 'none', textAlign: 'left',
                          fontSize: 13, color: '#e24b4a', cursor: 'pointer' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(226,75,74,0.08)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'none'}
                      >⏻ Logout</button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ color: '#ffffff', fontSize: 12 }}>Guest</span>
                <button
                  onClick={() => navigate(registerPath)}
                  style={{
                    background: accentColor, color: '#000', border: 'none',
                    borderRadius: 6, padding: '4px 14px', fontWeight: 700,
                    cursor: 'pointer', fontSize: 12,
                  }}
                >Register free</button>
                <span onClick={() => navigate(loginPath)}
                  style={{ color: '#ffffff', fontSize: 12, cursor: 'pointer' }}>Login</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
