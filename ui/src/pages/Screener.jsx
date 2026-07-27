import { useState, useEffect } from 'react'
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

const SEVERE_FLAG_TYPES = new Set([
  'beneish_manipulation_risk', 'altman_distress', 'material_weakness',
  'going_concern', 'sec_subpoena', 'sec_investigation', 'whistleblower_complaint',
  'financial_restatement',
])

function tierBadge(flagType) {
  const isSevere = SEVERE_FLAG_TYPES.has(flagType)
  return {
    label: isSevere ? 'ALERT' : 'WATCH',
    color: isSevere ? 'var(--red)' : 'var(--amber)',
  }
}

export default function Screener() {
  const [flags, setFlags] = useState([])
  const [summary, setSummary] = useState(null)
  const [flagTypeFilter, setFlagTypeFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/flags/summary').then(setSummary).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError('')
    const query = flagTypeFilter ? `?flag_type=${encodeURIComponent(flagTypeFilter)}&limit=100` : '?limit=100'
    apiFetch(`/api/filings${query}`)
      .then(data => setFlags(Array.isArray(data) ? data : []))
      .catch(() => setError('Could not load flags. Try again in a moment.'))
      .finally(() => setLoading(false))
  }, [flagTypeFilter])

  const flagTypes = Object.keys(summary?.counts || FLAG_LABELS)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar subtitle="Screener" />

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px 80px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Flagged companies</h1>

          <select
            value={flagTypeFilter}
            onChange={e => setFlagTypeFilter(e.target.value)}
            style={{
              background: 'var(--navy-700)', color: 'var(--text-primary)',
              border: '1px solid var(--border)', borderRadius: 6,
              padding: '8px 12px', fontSize: 13,
            }}
          >
            <option value="">All flag types</option>
            {flagTypes.map(t => (
              <option key={t} value={t}>{FLAG_LABELS[t] || t}</option>
            ))}
          </select>
        </div>

        {error && (
          <div style={{ color: 'var(--red)', fontSize: 14, marginBottom: 16 }}>{error}</div>
        )}

        {loading ? (
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, padding: '40px 0', textAlign: 'center' }}>
            Loading flags…
          </div>
        ) : flags.length === 0 ? (
          <div style={{ color: 'var(--text-secondary)', fontSize: 14, padding: '40px 0', textAlign: 'center' }}>
            No flags match this filter yet.
          </div>
        ) : (
          <div style={{ border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--navy-800)', textAlign: 'left' }}>
                  <Th>Ticker</Th>
                  <Th>Company</Th>
                  <Th>Flag</Th>
                  <Th>Tier</Th>
                  <Th>Filing date</Th>
                  <Th>Form</Th>
                </tr>
              </thead>
              <tbody>
                {flags.map(f => {
                  const badge = tierBadge(f.flag_type)
                  return (
                    <tr key={f.id} style={{ borderTop: '1px solid var(--border)' }}>
                      <Td mono>{f.ticker || '—'}</Td>
                      <Td>{f.company_name}</Td>
                      <Td>{FLAG_LABELS[f.flag_type] || f.flag_type}</Td>
                      <Td>
                        <span style={{
                          fontSize: 11, fontWeight: 700, letterSpacing: 0.5,
                          color: badge.color, border: `1px solid ${badge.color}`,
                          borderRadius: 999, padding: '2px 8px',
                        }}>
                          {badge.label}
                        </span>
                      </Td>
                      <Td mono>{f.filing_date}</Td>
                      <Td>{f.form_type || '—'}</Td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <RaqaFooter />
    </div>
  )
}

function Th({ children }) {
  return (
    <th style={{ padding: '10px 16px', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, color: 'var(--text-secondary)' }}>
      {children}
    </th>
  )
}

function Td({ children, mono }) {
  return (
    <td style={{
      padding: '10px 16px',
      fontFamily: mono ? 'ui-monospace, Consolas, monospace' : 'inherit',
      fontWeight: mono ? 700 : 400,
    }}>
      {children}
    </td>
  )
}
