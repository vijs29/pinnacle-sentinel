import NavBar from '../components/NavBar'
import RaqaFooter from '../components/RaqaFooter'

export default function Watchlist() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar subtitle="Watchlist" />

      <div style={{ maxWidth: 480, margin: '96px auto', padding: '0 24px', textAlign: 'center' }}>
        <div style={{
          width: 48, height: 48, borderRadius: 10, margin: '0 auto 20px',
          background: 'var(--navy-800)', border: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22,
        }}>
          ★
        </div>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>Watchlist is coming soon</h1>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Track specific companies and get notified the moment a new flag lands on them.
          This is a per-account feature we're still building -- for now, use the
          Screener to see everything flagged so far.
        </p>
      <RaqaFooter />
      </div>
    </div>
  )
}
