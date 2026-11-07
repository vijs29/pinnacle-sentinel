import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BASE_URL } from '../api/client'
import { shouldRedirectToLogin, authHeaders } from '../lib/authGate'
import NavBar from '../components/NavBar'

const STATUS_CONFIG = {
  ok:   { color: '#10b981', bg: 'rgba(16,185,129,0.1)',  label: 'OK',   icon: '✓' },
  warn: { color: '#d4af37', bg: 'rgba(212,175,55,0.1)',  label: 'WARN', icon: '⚠' },
  fail: { color: '#dc2626', bg: 'rgba(220,38,38,0.1)',   label: 'FAIL', icon: '✗' },
}

const PRODUCT_CONFIG = {
  quant:    { label: 'Pinnacle Quant',    color: '#c9a84c' },
  veridia:  { label: 'Pinnacle Veridia',  color: '#1d9e75' },
  sentinel: { label: 'Pinnacle Sentinel', color: '#d4443f' },
  platform: { label: 'Platform',         color: '#6366f1' },
  unknown:  { label: 'Other',            color: '#64748b' },
}

const CHECK_LABELS = {
  quant_predictions_gap:        'Predictions Gap',
  quant_outcomes_grading_lag:   'Outcomes Grading Lag',
  quant_scan_frequency:         'Scan Frequency',
  quant_scan_ticker_count:      'Scan Ticker Count',
  quant_miss_analysis_backlog:  'Miss Analysis Backlog',
  quant_duplicate_predictions:  'Duplicate Predictions',
  quant_var_forecast_freshness: 'VaR Forecast Freshness',
  quant_paper_trades_orphaned:  'Orphaned Paper Trades',
  quant_prediction_horizons:    'Prediction Horizons',
  veridia_var_forecast_freshness: 'VaR Forecast Freshness',
  veridia_var_forecast_coverage:  'VaR Forecast Coverage',
  veridia_wide_band_count:        'Wide Band Count',
  veridia_breach_log:             'Breach Log',
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.warn
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700,
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

function CheckCard({ check }) {
  const cfg = STATUS_CONFIG[check.status] || STATUS_CONFIG.warn
  const label = CHECK_LABELS[check.check_name] || check.check_name.replace(/_/g, ' ')
  const time = new Date(check.checked_at).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
  })
  return (
    <div style={{
      background: 'var(--navy-800)', border: `0.5px solid ${cfg.color}33`,
      borderLeft: `3px solid ${cfg.color}`,
      borderRadius: 8, padding: '12px 16px',
      display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12,
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{check.detail}</div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>Checked at {time}</div>
      </div>
      <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
        <StatusBadge status={check.status} />
        {check.value !== null && check.value !== undefined && (
          <span style={{ fontSize: 18, fontWeight: 700, color: cfg.color }}>
            {typeof check.value === 'number' ? check.value.toLocaleString() : check.value}
          </span>
        )}
      </div>
    </div>
  )
}

function SummaryBar({ checks }) {
  const ok   = checks.filter(c => c.status === 'ok').length
  const warn = checks.filter(c => c.status === 'warn').length
  const fail = checks.filter(c => c.status === 'fail').length
  const total = checks.length
  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
      {[
        { label: 'Passing',  count: ok,   color: '#10b981', bg: 'rgba(16,185,129,0.08)' },
        { label: 'Warnings', count: warn, color: '#d4af37', bg: 'rgba(212,175,55,0.08)' },
        { label: 'Failures', count: fail, color: '#dc2626', bg: 'rgba(220,38,38,0.08)' },
      ].map(({ label, count, color, bg }) => (
        <div key={label} style={{
          background: bg, border: `0.5px solid ${color}33`,
          borderRadius: 8, padding: '10px 16px', minWidth: 100, textAlign: 'center',
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color }}>{count}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
        </div>
      ))}
      <div style={{
        background: 'var(--navy-800)', border: '0.5px solid var(--border)',
        borderRadius: 8, padding: '10px 16px', minWidth: 100, textAlign: 'center',
      }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>{total}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Total Checks</div>
      </div>
    </div>
  )
}

// ── Data Inventory Components ──────────────────────────────────────────────────
function InventorySummaryBar({ totalRows, totalTables }) {
  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
      {[
        { label: 'Total Rows',   value: totalRows.toLocaleString(),   color: '#e24b4a', bg: 'rgba(226,75,74,0.08)' },
        { label: 'Total Tables', value: totalTables,                  color: '#1d9e75', bg: 'rgba(29,158,117,0.08)' },
      ].map(({ label, value, color, bg }) => (
        <div key={label} style={{
          background: bg, border: `0.5px solid ${color}33`,
          borderRadius: 8, padding: '10px 20px', minWidth: 140, textAlign: 'center',
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
        </div>
      ))}
    </div>
  )
}

function TableRow({ table }) {
  const cfg = PRODUCT_CONFIG[table.product] || PRODUCT_CONFIG.unknown
  return (
    <div style={{
      background: 'var(--navy-800)', border: '0.5px solid var(--border)',
      borderLeft: `3px solid ${cfg.color}`,
      borderRadius: 8, padding: '12px 16px',
      display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'start',
    }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3, fontFamily: 'monospace' }}>
          {table.table_name}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>{table.purpose}</div>
        <div style={{ fontSize: 11, color: cfg.color }}>→ {table.usage}</div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
          {table.row_count.toLocaleString()}
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>rows</div>
      </div>
    </div>
  )
}

function DataInventoryTab({ inventory }) {
  if (!inventory) return <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading inventory...</div>

  const PRODUCT_ORDER = ['sentinel', 'quant', 'veridia', 'platform', 'unknown']

  return (
    <div>
      <InventorySummaryBar totalRows={inventory.total_rows} totalTables={inventory.total_tables} />
      {PRODUCT_ORDER.map(product => {
        const tables = inventory.by_product[product]
        if (!tables || tables.length === 0) return null
        const cfg = PRODUCT_CONFIG[product] || PRODUCT_CONFIG.unknown
        const productRows = tables.reduce((sum, t) => sum + t.row_count, 0)
        return (
          <div key={product} style={{ marginBottom: 28 }}>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
              textTransform: 'uppercase', color: cfg.color,
              marginBottom: 12, paddingBottom: 8,
              borderBottom: `0.5px solid ${cfg.color}33`,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.color, display: 'inline-block' }} />
              {cfg.label}
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                · {tables.length} tables · {productRows.toLocaleString()} rows
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {tables.map(table => <TableRow key={table.table_name} table={table} />)}
            </div>
          </div>
        )
      })}
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 16 }}>
        Row counts from pg_stat_user_tables · Updated live from pinnacle_platform DB
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function PlatformIntelligence() {
  const [checks, setChecks] = useState([])
  const [inventory, setInventory] = useState(null)
  const [activeTab, setActiveTab] = useState('quality')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastRun, setLastRun] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (shouldRedirectToLogin(token, false)) { navigate('/login', { state: { from: '/platform-intelligence' } }); return }

    // Load quality checks
    fetch(`${BASE_URL}/api/platform/quality-checks`, {
      headers: authHeaders(token)
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        setChecks(data.checks || [])
        setLastRun(data.last_run)
        setLoading(false)
      })
      .catch(e => { setError(`Failed to load quality checks (${e})`); setLoading(false) })

    // Load data inventory
    fetch(`${BASE_URL}/api/platform/data-inventory`, {
      headers: authHeaders(token)
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => setInventory(data))
      .catch(() => {}) // non-fatal
  }, [])

  const byProduct = checks.reduce((acc, c) => {
    const product = c.product || 'platform'
    if (!acc[product]) acc[product] = []
    acc[product].push(c)
    return acc
  }, {})

  const lastRunStr = lastRun
    ? new Date(lastRun).toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: 'numeric',
        minute: '2-digit', timeZoneName: 'short'
      })
    : 'Never'

  const TABS = [
    { key: 'quality',   label: 'Quality Checks' },
    { key: 'inventory', label: 'Data Inventory' },
  ]

  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)' }}>
      <NavBar />
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 20px 60px' }}>

        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{
              width: 22, height: 22,
              background: 'linear-gradient(160deg,#1e2d4a,#0f1729)',
              clipPath: 'polygon(50% 0%,100% 20%,100% 70%,50% 100%,0% 70%,0% 20%)',
              border: '1px solid rgba(212,175,55,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{ color: '#d4af37', fontSize: 9, fontWeight: 800 }}>P</span>
            </div>
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 4, color: '#d4af37' }}>PINNACLE PLATFORM</span>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            Platform Intelligence
          </h1>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            {activeTab === 'quality'
              ? `Data quality checks across all products · Last run: ${lastRunStr}`
              : `${inventory ? inventory.total_rows.toLocaleString() : '...' } rows across ${inventory ? inventory.total_tables : '...' } tables in pinnacle_platform`
            }
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--border)' }}>
          {TABS.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '8px 16px', fontSize: 13, fontWeight: 600,
              color: activeTab === tab.key ? '#e24b4a' : 'var(--text-muted)',
              borderBottom: activeTab === tab.key ? '2px solid #e24b4a' : '2px solid transparent',
              marginBottom: -1, transition: 'color 0.15s',
            }}>
              {tab.label}
            </button>
          ))}
        </div>

        {loading && activeTab === 'quality' && (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading quality checks...</div>
        )}
        {error && (
          <div style={{ background: '#2a0f0f', border: '1px solid #dc2626',
            borderRadius: 8, padding: '12px 16px', color: '#ef4444', fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Quality Checks Tab */}
        {activeTab === 'quality' && !loading && !error && (
          <>
            {checks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
                <div style={{ fontSize: 15, marginBottom: 8 }}>No quality checks yet</div>
                <div style={{ fontSize: 13 }}>Checks run daily at 8pm ET weekdays via EC2 cron.</div>
              </div>
            ) : (
              <>
                <SummaryBar checks={checks} />
                {Object.entries(byProduct).map(([product, productChecks]) => {
                  const cfg = PRODUCT_CONFIG[product] || { label: product, color: '#6366f1' }
                  return (
                    <div key={product} style={{ marginBottom: 28 }}>
                      <div style={{
                        fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
                        textTransform: 'uppercase', color: cfg.color,
                        marginBottom: 12, paddingBottom: 8,
                        borderBottom: `0.5px solid ${cfg.color}33`,
                        display: 'flex', alignItems: 'center', gap: 8,
                      }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.color, display: 'inline-block' }} />
                        {cfg.label}
                        <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                          · {productChecks.filter(c => c.status === 'ok').length}/{productChecks.length} passing
                        </span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {productChecks.map(check => <CheckCard key={check.check_name} check={check} />)}
                      </div>
                    </div>
                  )
                })}
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 16 }}>
                  Checks run daily at 8pm ET on EC2 · Results stored in platform_quality_checks table
                </div>
              </>
            )}
          </>
        )}

        {/* Data Inventory Tab */}
        {activeTab === 'inventory' && <DataInventoryTab inventory={inventory} />}

      </div>
    </div>
  )
}
