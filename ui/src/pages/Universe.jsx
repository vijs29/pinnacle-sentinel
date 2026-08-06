/**
 * Universe.jsx — 126 tickers × 3 lenses (Quant + Veridia + Sentinel)
 * Location: ui/src/pages/Universe.jsx (all three products)
 *
 * Reads from /api/universe (Quant backend — has cross-product DB access).
 * Free tier — no auth required.
 *
 * Columns:
 *   Ticker       — symbol, price, change %
 *   Signal       — Quant signal strength + status label
 *   Max 5-Day Loss — Veridia VaR %
 *   Risk         — Veridia wide_band flag
 *   Governance   — Sentinel flag count + types
 */

import { useState, useEffect, useMemo } from 'react'
import NavBar from '../components/NavBar'

const QUANT_BASE = 'https://quant.pinnacletranscore.com'

const SIGNAL_COLORS = {
  green: '#1d9e75',
  gold:  '#c9a84c',
  amber: '#f59e0b',
  red:   '#d4443f',
  muted: '#475569',
}

const FLAG_LABELS = {
  late_filing:              'Late Filing',
  auditor_change:           'Auditor Change',
  cfo_resignation:          'CFO Resignation',
  material_weakness:        'Material Weakness',
  beneish_manipulation_risk:'Earnings Risk',
  altman_distress:          'Financial Distress',
  sloan_ratio_high:         'Accrual Quality',
  financial_restatement:    'Restatement',
  debt_covenant_violation:  'Debt Covenant',
  going_concern:            'Going Concern',
  sec_subpoena:             'SEC Subpoena',
  sec_investigation:        'SEC Investigation',
  whistleblower_complaint:  'Whistleblower',
}

function SignalBadge({ label, color }) {
  const c = SIGNAL_COLORS[color] || SIGNAL_COLORS.muted
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 11, fontWeight: 600, padding: '3px 8px',
      borderRadius: 4, background: `${c}18`, color: c,
      border: `0.5px solid ${c}40`, whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}

function RiskBadge({ elevated }) {
  if (elevated === null || elevated === undefined) return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 4,
      background: elevated ? 'rgba(212,68,63,0.1)' : 'rgba(29,158,117,0.1)',
      color: elevated ? '#d4443f' : '#1d9e75',
      border: `0.5px solid ${elevated ? '#d4443f40' : '#1d9e7540'}`,
      whiteSpace: 'nowrap',
    }}>
      {elevated ? '⚠ High Risk' : '✓ Normal'}
    </span>
  )
}

function FlagCell({ count, types }) {
  const [expanded, setExpanded] = useState(false)
  if (count === 0) return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>✓ None</span>
  const labels = types.map(t => FLAG_LABELS[t] || t)
  return (
    <div>
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          background: 'rgba(212,68,63,0.08)', border: '0.5px solid rgba(212,68,63,0.3)',
          borderRadius: 4, color: '#d4443f', fontSize: 11, fontWeight: 600,
          padding: '3px 8px', cursor: 'pointer', whiteSpace: 'nowrap',
        }}
      >
        🚩 {count} flag{count > 1 ? 's' : ''} {expanded ? '▴' : '▾'}
      </button>
      {expanded && (
        <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {labels.map(l => (
            <span key={l} style={{
              fontSize: 10, padding: '2px 6px', borderRadius: 3,
              background: 'rgba(212,68,63,0.06)', color: '#d4443f',
              border: '0.5px solid rgba(212,68,63,0.2)',
            }}>{l}</span>
          ))}
        </div>
      )}
    </div>
  )
}

const SORT_OPTIONS = [
  { key: 'signal_score', label: 'Signal Strength' },
  { key: 'max_loss_5d_pct', label: 'Max Loss (asc)' },
  { key: 'flag_count', label: 'Governance Flags' },
  { key: 'ticker', label: 'Ticker A–Z' },
]

const FILTER_OPTIONS = [
  { key: 'all', label: 'All 126' },
  { key: 'buy', label: 'Buy signals' },
  { key: 'risk', label: 'High risk' },
  { key: 'flagged', label: 'Has flags' },
  { key: 'clean', label: 'Clean (no flags, normal risk)' },
]

export default function Universe({ accentColor = '#c9a84c' }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [sort, setSort]       = useState('signal_score')
  const [filter, setFilter]   = useState('all')
  const [search, setSearch]   = useState('')

  useEffect(() => {
    fetch(`${QUANT_BASE}/api/universe`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(`Failed to load universe data (${e})`); setLoading(false) })
  }, [])

  const tickers = useMemo(() => {
    if (!data?.tickers) return []
    let rows = [...data.tickers]

    // Filter
    if (filter === 'buy')     rows = rows.filter(r => ['STRONG_SIGNAL','SIGNAL'].includes(r.signal_routing))
    if (filter === 'risk')    rows = rows.filter(r => r.elevated_risk)
    if (filter === 'flagged') rows = rows.filter(r => r.flag_count > 0)
    if (filter === 'clean')   rows = rows.filter(r => !r.elevated_risk && r.flag_count === 0)

    // Search
    if (search.trim()) {
      const q = search.trim().toUpperCase()
      rows = rows.filter(r => r.ticker.includes(q))
    }

    // Sort
    rows.sort((a, b) => {
      if (sort === 'ticker')           return a.ticker.localeCompare(b.ticker)
      if (sort === 'signal_score')     return (b.signal_score ?? -1) - (a.signal_score ?? -1)
      if (sort === 'max_loss_5d_pct')  return (a.max_loss_5d_pct ?? 0) - (b.max_loss_5d_pct ?? 0)
      if (sort === 'flag_count')       return b.flag_count - a.flag_count
      return 0
    })

    return rows
  }, [data, sort, filter, search])

  const TH = ({ children, width, title }) => (
    <th title={title} style={{
      padding: '10px 12px', textAlign: 'left', fontSize: 10,
      fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase',
      color: 'var(--text-muted)', borderBottom: '0.5px solid var(--border)',
      whiteSpace: 'nowrap', width, cursor: title ? 'help' : 'default',
      textDecoration: title ? 'underline dotted' : 'none',
    }}>{children}</th>
  )

  const TD = ({ children, style = {} }) => (
    <td style={{
      padding: '10px 12px', borderBottom: '0.5px solid rgba(255,255,255,0.04)',
      verticalAlign: 'top', ...style,
    }}>{children}</td>
  )

  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar hideBackHome={false} />

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>

        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em',
            textTransform: 'uppercase', color: accentColor, marginBottom: 6 }}>
            Universe View
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 500, margin: '0 0 6px', color: 'var(--text-primary)' }}>
            126 tickers — three lenses
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
            Every ticker in our 126-stock universe, viewed through three independent lenses:
            signal confluence from <strong style={{ color: '#c9a84c' }}>Pinnacle Quant</strong>,
            portfolio risk from <strong style={{ color: '#1d9e75' }}>Pinnacle Veridia</strong>,
            and SEC filing red flags from <strong style={{ color: '#d4443f' }}>Pinnacle Sentinel</strong>.
            A ticker worth acting on should show a strong buy signal, normal risk, and no governance flags.
            A ticker with all three warning signs — weak signal, high risk, active flags — warrants caution.
            See each product's <a href="/methodology" style={{ color: 'var(--text-muted)', textDecoration: 'underline' }}>Methodology</a> for
            how each lens is validated.
          </p>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16, alignItems: 'center' }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search ticker..."
            style={{
              background: 'var(--navy-800)', border: '0.5px solid var(--border)',
              borderRadius: 6, padding: '6px 12px', fontSize: 12,
              color: 'var(--text-primary)', width: 140,
            }}
          />
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{
              background: 'var(--navy-800)', border: '0.5px solid var(--border)',
              borderRadius: 6, padding: '6px 12px', fontSize: 12,
              color: 'var(--text-secondary)', cursor: 'pointer',
            }}
          >
            {FILTER_OPTIONS.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
          </select>
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            style={{
              background: 'var(--navy-800)', border: '0.5px solid var(--border)',
              borderRadius: 6, padding: '6px 12px', fontSize: 12,
              color: 'var(--text-secondary)', cursor: 'pointer',
            }}
          >
            {SORT_OPTIONS.map(s => <option key={s.key} value={s.key}>Sort: {s.label}</option>)}
          </select>
          {data && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 4 }}>
              {tickers.length} of {data.count} tickers
            </span>
          )}
        </div>

        {/* Legend */}
        <div style={{
          display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 16,
          padding: '8px 12px', background: 'var(--navy-800)',
          border: '0.5px solid var(--border)', borderRadius: 6,
          fontSize: 11, color: 'var(--text-muted)',
        }}>
          <span>Signal: <span style={{ color: SIGNAL_COLORS.green }}>●</span> Strong Buy &nbsp;
            <span style={{ color: SIGNAL_COLORS.gold }}>●</span> Buy &nbsp;
            <span style={{ color: SIGNAL_COLORS.amber }}>●</span> Watch &nbsp;
            <span style={{ color: SIGNAL_COLORS.red }}>●</span> Avoid &nbsp;
            <span style={{ color: SIGNAL_COLORS.muted }}>●</span> Neutral
          </span>
          <span>Max Loss: worst expected loss in 5 trading days (95% confidence)</span>
          <span>Risk: ⚠ High Risk = top 25% of universe by volatility</span>
        </div>

        {/* Table */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)', fontSize: 14 }}>
            Loading universe data...
          </div>
        )}
        {error && (
          <div style={{ textAlign: 'center', padding: '48px', color: '#d4443f', fontSize: 14 }}>
            {error}
          </div>
        )}
        {!loading && !error && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--navy-800)' }}>
                  <TH width="90">Ticker</TH>
                  <TH width="80">Price</TH>
                  <TH width="120" title="STRONG SIGNAL → Strong Buy, SIGNAL → Buy, WATCH → Watch, AVOID → Avoid">Signal Status</TH>
                  <TH width="80" title="How strongly our signals indicate a buying opportunity (0–100%)">Signal Strength</TH>
                  <TH width="110" title="Worst expected loss in 5 trading days with 95% confidence — e.g. -16% means we are 95% confident you will not lose more than 16%">Max 5-Day Loss</TH>
                  <TH width="100" title="Yes/No — this ticker's risk is in the top 25% of our universe by volatility">Elevated Risk</TH>
                  <TH title="Number of SEC filing red flags detected in the last 12 months — click a flag count to see what was flagged">Governance Flags</TH>
                </tr>
              </thead>
              <tbody>
                {tickers.map(r => (
                  <tr
                    key={r.ticker}
                    style={{ transition: 'background 0.1s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    <TD>
                      <div style={{ fontWeight: 700, fontFamily: 'ui-monospace, monospace', fontSize: 13 }}>
                        {r.ticker}
                      </div>
                      {r.change_pct !== null && (
                        <div style={{
                          fontSize: 10, marginTop: 2,
                          color: r.change_pct >= 0 ? '#1d9e75' : '#d4443f',
                        }}>
                          {r.change_pct >= 0 ? '+' : ''}{r.change_pct?.toFixed(1)}%
                        </div>
                      )}
                    </TD>
                    <TD>
                      <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: 13 }}>
                        {r.price ? `$${r.price.toFixed(2)}` : '—'}
                      </span>
                    </TD>
                    <TD>
                      <SignalBadge label={r.signal_label} color={r.signal_color} />
                    </TD>
                    <TD>
                      {r.signal_score !== null ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{
                            width: 48, height: 4, background: 'var(--navy-700)',
                            borderRadius: 2, overflow: 'hidden',
                          }}>
                            <div style={{
                              width: `${r.signal_score}%`, height: '100%',
                              background: SIGNAL_COLORS[r.signal_color],
                              borderRadius: 2,
                            }} />
                          </div>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {r.signal_score}%
                          </span>
                        </div>
                      ) : '—'}
                    </TD>
                    <TD>
                      {r.max_loss_5d_pct !== null ? (
                        <span style={{
                          fontFamily: 'ui-monospace, monospace', fontSize: 13,
                          color: Math.abs(r.max_loss_5d_pct) > 10 ? '#d4443f' : 'var(--text-secondary)',
                        }}>
                          {r.max_loss_5d_pct.toFixed(1)}%
                        </span>
                      ) : '—'}
                    </TD>
                    <TD>
                      <RiskBadge elevated={r.elevated_risk} />
                    </TD>
                    <TD>
                      <FlagCell count={r.flag_count} types={r.flag_types} />
                    </TD>
                  </tr>
                ))}
              </tbody>
            </table>

            {tickers.length === 0 && (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: 13 }}>
                No tickers match your filter.
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: 24, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Signal data updated daily at 1pm ET. VaR forecasts updated daily at 5:30pm ET.
          Governance flags updated as SEC filings are processed. Nothing here is investment advice.
        </div>
      </div>
    </div>
  )
}
