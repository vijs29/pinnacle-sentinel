import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import NavBar from '../components/NavBar'
import RaqaFooter from '../components/RaqaFooter'
import { apiFetch } from '../api/client'

const FLAG_LABELS = {
  late_filing: 'Late filing',
  auditor_change: 'Auditor change',
  cfo_resignation: 'CFO resignation',
  material_weakness: 'Material weakness',
  accelerated_insider_selling: 'Insider selling',
  beneish_manipulation_risk: 'Earnings manipulation risk',
  altman_distress: 'Financial distress',
  sloan_ratio_high: 'Accrual quality',
  financial_restatement: 'Financial restatement',
  debt_covenant_violation: 'Debt covenant violation',
  going_concern: 'Going concern',
  sec_subpoena: 'SEC subpoena',
  sec_investigation: 'SEC investigation',
  whistleblower_complaint: 'Whistleblower complaint',
}

function flagColor(flagType) {
  if (flagType === 'beneish_manipulation_risk' || flagType === 'altman_distress') return 'var(--red)'
  if (flagType === 'sloan_ratio_high' || flagType === 'material_weakness') return 'var(--amber)'
  return 'var(--blue)'
}

function FlagTape({ flags }) {
  const prefersReducedMotion = typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (!flags.length) return null

  const items = prefersReducedMotion ? flags : [...flags, ...flags]

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      borderBottom: '1px solid var(--border)',
      background: 'var(--navy-800)',
      overflow: 'hidden',
      whiteSpace: 'nowrap',
      padding: '10px 0',
    }}>
      <div style={{
        display: 'inline-flex',
        gap: 32,
        animation: prefersReducedMotion ? 'none' : 'sentinel-tape-scroll 40s linear infinite',
        paddingLeft: prefersReducedMotion ? 24 : 0,
      }}>
        {items.map((f, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: flagColor(f.flag_type), flexShrink: 0,
            }} />
            <span style={{ fontFamily: 'ui-monospace, Consolas, monospace', fontWeight: 700, color: 'var(--text-primary)' }}>
              {f.ticker || f.cik}
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {FLAG_LABELS[f.flag_type] || f.flag_type}
            </span>
          </span>
        ))}
      </div>
      <style>{`
        @keyframes sentinel-tape-scroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [recentFlags, setRecentFlags] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // The tape favors a MIX of recent disclosure and quantitative flags.
    // A single date-sorted query would be dominated by disclosure flags,
    // since those post continuously (daily EDGAR filings) while
    // quantitative flags only update once per company per fiscal year --
    // not a bug, just a mismatch in how often each type refreshes.
    Promise.all([
      apiFetch('/api/flags/summary').catch(() => null),
      apiFetch('/api/filings?limit=10&flag_type=late_filing').catch(() => []),
      apiFetch('/api/filings?limit=10&flag_type=altman_distress').catch(() => []),
    ]).then(([summaryData, disclosureFlags, quantFlags]) => {
      setSummary(summaryData)
      const merged = []
      const d = Array.isArray(disclosureFlags) ? disclosureFlags : []
      const q = Array.isArray(quantFlags) ? quantFlags : []
      const maxLen = Math.max(d.length, q.length)
      for (let i = 0; i < maxLen; i++) {
        if (d[i]) merged.push(d[i])
        if (q[i]) merged.push(q[i])
      }
      setRecentFlags(merged)
      setLoading(false)
    })
  }, [])

  const disclosureTypes = ['late_filing', 'auditor_change', 'cfo_resignation', 'material_weakness', 'accelerated_insider_selling']
  const quantTypes = ['beneish_manipulation_risk', 'altman_distress', 'sloan_ratio_high']

  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar hideBackHome />

      <FlagTape flags={recentFlags} />

      <div style={{ maxWidth: 860, margin: '0 auto', padding: '72px 24px 48px', textAlign: 'center' }}>
        <div style={{
          display: 'inline-block', fontSize: 12, fontWeight: 700, letterSpacing: 1.5,
          color: 'var(--red)', border: '1px solid rgba(212, 68, 63, 0.35)',
          borderRadius: 999, padding: '4px 14px', marginBottom: 24,
        }}>
          SEC FILINGS SURVEILLANCE
        </div>
        <h1 style={{ fontSize: 42, fontWeight: 800, lineHeight: 1.15, margin: '0 0 20px', letterSpacing: -0.5 }}>
          Every filing gets read.<br />Most of them are hiding something.
        </h1>
        <p style={{ fontSize: 17, color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: 560, margin: '0 auto 32px' }}>
          Sentinel watches the S&P 500's SEC filings for the disclosure patterns and
          financial-statement red flags that short sellers look for by hand —
          before the market catches up.
        </p>
        <button onClick={() => navigate('/screener')} style={{
          background: 'var(--red)', color: '#fff', border: 'none', borderRadius: 8,
          padding: '14px 32px', fontWeight: 700, fontSize: 15, cursor: 'pointer',
        }}>
          Open the Screener →
        </button>
      </div>

      {!loading && summary && (
        <div style={{
          maxWidth: 860, margin: '0 auto 64px', padding: '0 24px',
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16,
        }}>
          <StatCard label="Companies monitored" value="503" sub="S&P 500 universe" />
          <StatCard label="Flags detected" value={summary.total?.toLocaleString() ?? '—'} sub="disclosure + quantitative" />
          <StatCard label="Red-flag types" value={Object.keys(summary.counts || {}).length || '—'} sub="text + financial-ratio" />
        </div>
      )}

      <div style={{ maxWidth: 860, margin: '0 auto', padding: '0 24px 80px' }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>What Sentinel detects</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: 'var(--blue)', marginBottom: 12 }}>
              DISCLOSURE-BASED
            </div>
            {disclosureTypes.map(t => (
              <FlagRow key={t} label={FLAG_LABELS[t]} count={summary?.counts?.[t]} color="var(--blue)" />
            ))}
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: 'var(--red)', marginBottom: 12 }}>
              FINANCIAL-RATIO
            </div>
            {quantTypes.map(t => (
              <FlagRow key={t} label={FLAG_LABELS[t]} count={summary?.counts?.[t]} color="var(--red)" />
            ))}
          </div>
        </div>
      </div>

      <RaqaFooter />
    </div>
  )
}

function StatCard({ label, value, sub }) {
  return (
    <div style={{
      background: 'var(--navy-800)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '20px 16px', textAlign: 'center',
    }}>
      <div style={{ fontSize: 28, fontWeight: 800, fontFamily: 'ui-monospace, Consolas, monospace' }}>{value}</div>
      <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{label}</div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{sub}</div>
    </div>
  )
}

function FlagRow({ label, count, color }) {
  if (!label) return null
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px 0', borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 14 }}>{label}</span>
      <span style={{
        fontFamily: 'ui-monospace, Consolas, monospace', fontWeight: 700,
        fontSize: 13, color,
      }}>
        {count != null ? count.toLocaleString() : '—'}
      </span>
    </div>
  )
}
