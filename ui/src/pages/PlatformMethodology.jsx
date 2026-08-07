/**
 * PlatformMethodology.jsx — Platform-wide methodology page (tabbed)
 * Location: ui/src/pages/PlatformMethodology.jsx (all three products)
 *
 * Reads from /api/platform/methodology (public, no auth required).
 * Content assembled nightly at 9:05pm ET by INF-016.
 * Splits assembled content into tabs by product.
 *
 * Route: /platform-methodology
 */

import { useState, useEffect } from 'react'
import NavBar from '../components/NavBar'

const TABS = [
  { key: 'quant',    label: 'Pinnacle Quant',           color: '#c9a84c' },
  { key: 'veridia',  label: 'Pinnacle Veridia',         color: '#1d9e75' },
  { key: 'sentinel', label: 'Pinnacle Sentinel',        color: '#d4443f' },
  { key: 'infra',    label: 'Pinnacle Infrastructure',  color: '#94a3b8' },
]

function splitByProduct(content) {
  if (!content) return {}
  const sections = {}
  // Split on --- separator lines
  const parts = content.split(/\n---\n/)
  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue
    const firstLine = trimmed.split('\n')[0].trim()
    if (firstLine === '> **Pinnacle Quant**') {
      sections.quant = trimmed.replace(/^> \*\*Pinnacle Quant\*\*\s*\n/, '').trim()
    } else if (firstLine === '> **Pinnacle Veridia**') {
      sections.veridia = trimmed.replace(/^> \*\*Pinnacle Veridia\*\*\s*\n/, '').trim()
    } else if (firstLine === '> **Pinnacle Sentinel**') {
      sections.sentinel = trimmed.replace(/^> \*\*Pinnacle Sentinel\*\*\s*\n/, '').trim()
    } else if (firstLine === '> **Pinnacle Infrastructure**') {
      sections.infra = trimmed.replace(/^> \*\*Pinnacle Infrastructure\*\*\s*\n/, '').trim()
    }
  }
  return sections
}

function MarkdownSection({ content }) {
  if (!content) return null
  const lines = content.split('\n')
  const elements = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (line.startsWith('# ')) {
      elements.push(<h1 key={i} style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', margin: '28px 0 10px', paddingBottom: 8, borderBottom: '0.5px solid var(--border)' }}>{line.slice(2)}</h1>)
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={i} style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', margin: '22px 0 6px' }}>{line.slice(3)}</h2>)
    } else if (line.startsWith('### ')) {
      elements.push(<h3 key={i} style={{ fontSize: 11, fontWeight: 600, color: '#c9a84c', margin: '14px 0 4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{line.slice(4)}</h3>)
    } else if (line.startsWith('---')) {
      elements.push(<hr key={i} style={{ border: 'none', borderTop: '0.5px solid var(--border)', margin: '20px 0' }} />)
    } else if (line.startsWith('> ')) {
      elements.push(<blockquote key={i} style={{ borderLeft: '3px solid #c9a84c', margin: '10px 0', padding: '6px 14px', background: 'rgba(201,168,76,0.05)', borderRadius: '0 6px 6px 0', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{line.slice(2)}</blockquote>)
    } else if (line.startsWith('```')) {
      const codeLines = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) { codeLines.push(lines[i]); i++ }
      elements.push(<pre key={i} style={{ background: 'var(--navy-800)', border: '0.5px solid var(--border)', borderRadius: 6, padding: '10px 14px', overflow: 'auto', fontSize: 11, lineHeight: 1.6, color: '#94a3b8', fontFamily: 'ui-monospace, Consolas, monospace', margin: '10px 0' }}>{codeLines.join('\n')}</pre>)
    } else if (line.startsWith('| ')) {
      const tableLines = []
      while (i < lines.length && lines[i].startsWith('|')) { tableLines.push(lines[i]); i++ }
      const headers = tableLines[0].split('|').filter(c => c.trim()).map(c => c.trim())
      const rows = tableLines.slice(2).map(r => r.split('|').filter(c => c.trim()).map(c => c.trim()))
      elements.push(
        <div key={`table-${i}`} style={{ overflowX: 'auto', margin: '10px 0' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead><tr>{headers.map((h, j) => <th key={j} style={{ padding: '7px 10px', textAlign: 'left', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', borderBottom: '0.5px solid var(--border)', background: 'var(--navy-800)' }}>{h}</th>)}</tr></thead>
            <tbody>{rows.map((row, j) => <tr key={j} style={{ borderBottom: '0.5px solid rgba(255,255,255,0.04)' }}>{row.map((cell, k) => <td key={k} style={{ padding: '7px 10px', color: 'var(--text-secondary)', fontSize: 12 }}>{cell}</td>)}</tr>)}</tbody>
          </table>
        </div>
      )
      continue
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <div key={i} style={{ display: 'flex', gap: 8, margin: '3px 0', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <span style={{ color: '#c9a84c', flexShrink: 0, marginTop: 2 }}>·</span>
          <span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary)">$1</strong>').replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:3px;font-family:ui-monospace,monospace;font-size:11px">$1</code>') }} />
        </div>
      )
    } else if (line.trim() === '') {
      elements.push(<div key={i} style={{ height: 5 }} />)
    } else {
      elements.push(<p key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: '3px 0' }} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary)">$1</strong>').replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:3px;font-family:ui-monospace,monospace;font-size:11px">$1</code>') }} />)
    }
    i++
  }
  return <>{elements}</>
}

export default function PlatformMethodology() {
  const [data, setData]           = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [activeTab, setActiveTab] = useState('quant')

  useEffect(() => {
    fetch('/api/platform/methodology')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(`Failed to load (${e})`); setLoading(false) })
  }, [])

  const sections    = data?.content ? splitByProduct(data.content) : {}
  const activeColor = TABS.find(t => t.key === activeTab)?.color || '#c9a84c'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar hideBackHome={false} />
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px 80px' }}>

        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#c9a84c', marginBottom: 6 }}>Platform Methodology</div>
          <h1 style={{ fontSize: 22, fontWeight: 500, margin: '0 0 6px' }}>How every product is built and validated</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
            The technical and epistemic standards across all Pinnacle products — assembled nightly from each product's canonical methodology document.
          </p>
          {data?.assembled_at && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              Last assembled: {new Date(data.assembled_at).toLocaleString()} · {data.line_count?.toLocaleString()} lines
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 2, marginBottom: 24, borderBottom: '0.5px solid var(--border)' }}>
          {TABS.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: activeTab === tab.key ? 600 : 400,
              color: activeTab === tab.key ? tab.color : 'var(--text-muted)',
              padding: '8px 16px',
              borderBottom: activeTab === tab.key ? `2px solid ${tab.color}` : '2px solid transparent',
              marginBottom: -1, transition: 'color 0.15s',
            }}>{tab.label}</button>
          ))}
        </div>

        {loading && <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)', fontSize: 14 }}>Loading methodology...</div>}
        {error   && <div style={{ textAlign: 'center', padding: '48px', color: '#d4443f', fontSize: 14 }}>{error}</div>}
        {!loading && !error && (
          sections[activeTab]
            ? <MarkdownSection content={sections[activeTab]} />
            : <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)', fontSize: 13 }}>No methodology content for this product yet.</div>
        )}

        <div style={{ marginTop: 40, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6, borderTop: '0.5px solid var(--border)', paddingTop: 16 }}>
          Auto-assembled nightly from each product's <code style={{ background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: 3, fontFamily: 'ui-monospace, monospace', fontSize: 10 }}>docs/METHODOLOGY.md</code>. Edit the source file in the product's repository — changes appear here by 9:05pm ET.
        </div>
      </div>
    </div>
  )
}
