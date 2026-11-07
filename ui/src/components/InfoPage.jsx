// Shared layout and building blocks for Sentinel's explanatory pages.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import NavBar from './NavBar'
import RaqaFooter from './RaqaFooter'
import { apiFetch } from '../api/client'
import { FLAG_LABELS, tierFor } from '../lib/flagInfo'

export const pText = { fontSize: 15, lineHeight: 1.65, color: 'var(--text-secondary)', margin: '0 0 14px' }
const thStyle = { textAlign: 'left', padding: '8px 10px', color: 'var(--text-muted)', fontWeight: 700, fontSize: 11.5, letterSpacing: 0.5, textTransform: 'uppercase' }
const tdStyle = { padding: '8px 10px', color: 'var(--text-secondary)' }

export default function InfoPage({ subtitle, kicker, title, lede, children }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar subtitle={subtitle} />
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '56px 24px 96px' }}>
        {kicker && (
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: 'var(--red)', marginBottom: 10 }}>{kicker}</div>
        )}
        <h1 style={{ fontSize: 30, fontWeight: 800, marginBottom: 10, letterSpacing: -0.3 }}>{title}</h1>
        {lede && <p style={{ ...pText, fontSize: 16, marginBottom: 36 }}>{lede}</p>}
        {children}
      </div>
      <RaqaFooter />
    </div>
  )
}

export function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 40 }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 14 }}>{title}</h2>
      {children}
    </div>
  )
}

export function P({ children }) { return <p style={pText}>{children}</p> }

export function Note({ title = "What we don't claim", children }) {
  return (
    <div style={{
      fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6,
      background: 'rgba(212,68,63,0.06)', border: '1px solid rgba(212,68,63,0.2)',
      borderRadius: 8, padding: '12px 14px', marginTop: 16,
    }}>
      <b style={{ color: 'var(--text-secondary)' }}>{title}:</b> {children}
    </div>
  )
}

export function Badge({ color, children }) {
  return (
    <span style={{
      display: 'inline-block', fontSize: 12, fontWeight: 700, letterSpacing: 0.5,
      color, border: `1px solid ${color}`, borderRadius: 999, padding: '1px 8px', margin: '0 2px',
    }}>{children}</span>
  )
}

export function Stat({ value, label }) {
  return (
    <div style={{ flex: '1 1 160px', background: 'var(--navy-800)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--red)', fontFamily: 'ui-monospace, Consolas, monospace' }}>{value}</div>
      <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.4 }}>{label}</div>
    </div>
  )
}

export function SimpleTable({ head, rows }) {
  return (
    <div style={{ overflowX: 'auto', margin: '12px 0 18px' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-light)' }}>{head.map(h => <th key={h} style={thStyle}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
              {r.map((c, j) => <td key={j} style={tdStyle}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Live count of flags per type, shared by every page that shows counts.
export function useFlagCounts() {
  const [counts, setCounts] = useState(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    apiFetch('/api/flags/summary').then(d => setCounts(d.counts || {})).catch(() => setFailed(true))
  }, [])
  return { counts, failed }
}

// Most recent flags of one type, straight from the API. `valueLabel` shows details.value (the score) when present.
export function RecentFlags({ flagKey, limit = 15, valueLabel }) {
  const [rows, setRows] = useState(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    apiFetch(`/api/filings?flag_type=${encodeURIComponent(flagKey)}&limit=${limit}`)
      .then(d => setRows(Array.isArray(d) ? d : []))
      .catch(() => setFailed(true))
  }, [flagKey, limit])

  if (failed) return <div style={{ color: 'var(--red)', fontSize: 14 }}>The recent flags are not available right now.</div>
  if (rows === null) return <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Loading…</div>
  if (rows.length === 0) return <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No flags of this type have been recorded yet.</div>
  const head = ['Ticker', 'Company', 'Date', ...(valueLabel ? [valueLabel] : []), 'Source']
  const body = rows.map(f => [
    <b key="t" style={{ fontFamily: 'ui-monospace, Consolas, monospace' }}>{f.ticker || '—'}</b>,
    f.company_name || '—',
    f.filing_date || '—',
    ...(valueLabel ? [typeof f.details?.value === 'number' ? f.details.value.toFixed(2) : '—'] : []),
    f.filing_url ? <a key="u" href={f.filing_url} target="_blank" rel="noreferrer" style={{ color: 'var(--red)' }}>{f.form_type || 'filing'}</a> : (f.form_type || '—'),
  ])
  return <SimpleTable head={head} rows={body} />
}

export function TierBadge({ flagKey }) {
  const t = tierFor(flagKey)
  return <Badge color={t === 'ALERT' ? 'var(--red)' : 'var(--amber)'}>{t}</Badge>
}

export { Link, FLAG_LABELS }
