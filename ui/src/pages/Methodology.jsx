import NavBar from '../components/NavBar'
import RaqaFooter from '../components/RaqaFooter'

const FLAGS = [
  { name: 'Late filing', detail: 'NT 10-K / NT 10-Q -- the filing itself is the flag.' },
  { name: 'Auditor change', detail: '8-K Item 4.01, and 4.02 when auditor-related.' },
  { name: 'CFO resignation', detail: '8-K Item 5.02, classified on the body text.' },
  { name: 'Material weakness', detail: '8-K Item 4.02 when weakness-related, or 10-K disclosure.' },
  { name: 'Accelerated insider selling', detail: 'Form 4, against a per-insider historical baseline.' },
  { name: 'Financial restatement', detail: '8-K Item 4.02 -- non-reliance on previously issued financial statements.' },
  { name: 'Debt covenant violation', detail: '8-K Item 2.04 -- a triggering event accelerating a financial obligation.' },
  { name: 'Going concern', detail: '10-K audit opinion language -- substantial doubt about continuing operations.' },
  { name: 'SEC subpoena / investigation', detail: 'Full-text search across 10-K/10-Q/8-K for disclosed investigations.' },
  { name: 'Whistleblower complaint', detail: 'Full-text search for disclosed whistleblower complaints.' },
]

const QUANT_FLAGS = [
  { name: 'Beneish M-Score', detail: '8 variables detecting likely earnings manipulation.' },
  { name: 'Altman Z-Score', detail: '5 variables predicting bankruptcy risk within two years.' },
  { name: 'Sloan accruals ratio', detail: 'Flags earnings running well ahead of cash flow.' },
]

const SCORE_BANDS = [
  { range: '1-2',   label: 'Clean',    color: 'var(--green)',  action: 'BUY recorded normally' },
  { range: '3-4',   label: 'Elevated', color: 'var(--amber)',  action: 'BUY \u2192 WATCH' },
  { range: '5-6',   label: 'High',     color: 'var(--red)',    action: 'BUY \u2192 AVOID' },
  { range: '7-9',   label: 'Severe',   color: 'var(--red)',    action: 'BUY \u2192 AVOID, full breakdown shown' },
  { range: '10-12', label: 'Extreme', color: '#8b1a1a',        action: 'BUY \u2192 AVOID, prominent warning' },
]

export default function Methodology() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar subtitle="Methodology" />

      <div style={{ maxWidth: 760, margin: '0 auto', padding: '56px 24px 96px' }}>

        {/* ============================================================ */}
        {/* PLATFORM INTEGRATION -- shared across all three products     */}
        {/* ============================================================ */}
        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: 'var(--gold-400)', marginBottom: 10 }}>
          PINNACLE PLATFORM
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 10, letterSpacing: -0.3 }}>
          How the three products work together
        </h1>
        <p style={pText}>
          Pinnacle Sentinel, Pinnacle Veridia, and Pinnacle Quant are independently useful
          products that also share a common risk layer. Each one answers a different
          question about the same underlying risk -- together, they form a composite
          filter no single product can provide alone.
        </p>

        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12,
          margin: '20px 0 36px',
        }}>
          <ProductCard
            name="Pinnacle Sentinel" accent="var(--red)"
            question="What's wrong with this company?"
            desc="SEC filing red flags -- disclosure-based and financial-ratio-based."
          />
          <ProductCard
            name="Pinnacle Veridia" accent="var(--green)"
            question="How much risk is in this position?"
            desc="Per-ticker Value-at-Risk forecasts, calibrated and graded against outcomes."
          />
          <ProductCard
            name="Pinnacle Quant" accent="var(--gold-400)"
            question="When should I act on this signal?"
            desc="Price-based signals, downweighted when risk context says caution."
          />
        </div>

        <Section title="Composite Risk Score -- 1 to 12">
          <p style={pText}>
            The composite risk score combines signals from all three products into a
            single number from 1 to 12. It is a <b>risk filter, not a prediction</b> --
            a high score means the environment is unfavorable for a bullish signal to
            succeed, not that the stock will definitely fall.
          </p>

          <div style={{ overflowX: 'auto', margin: '18px 0' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                  <th style={thStyle}>Score</th>
                  <th style={thStyle}>Label</th>
                  <th style={thStyle}>What Pinnacle Quant does</th>
                </tr>
              </thead>
              <tbody>
                {SCORE_BANDS.map(b => (
                  <tr key={b.range} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={tdStyle}>{b.range}</td>
                    <td style={{ ...tdStyle, color: b.color, fontWeight: 700 }}>{b.label}</td>
                    <td style={tdStyle}>{b.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p style={pText}>
            <b>How the 12 points are built:</b> Pinnacle Sentinel's 9 disclosure-based
            flags are grouped and capped at <b>+6</b> total, however many fire at once --
            so one flag and five flags don't both trivially hit the ceiling. Pinnacle
            Sentinel's 3 quantitative flags contribute up to <b>+3</b>. Pinnacle Veridia's
            VaR wide-band flag contributes a flat <b>+2</b>. Pinnacle Quant's own signal
            direction contributes up to <b>+1</b>. Maximum possible: 6 + 3 + 2 + 1 = 12,
            requiring every factor across all three products to fire at the same time --
            deliberately rare.
          </p>

          <p style={pText}>
            <b>Why Pinnacle Veridia's +2 is the only statistically validated weight:</b>{' '}
            across 78 walkforward observations (only ever using data that would have been
            available at the time -- no lookahead), Pinnacle Quant's bullish signals missed
            53.2% of the time normally, versus <b>94.9%</b> of the time when Pinnacle
            Veridia's VaR wide-band flag was active -- a <b>1.78x</b> increase in miss
            rate. The result is essentially impossible to be random chance (p&nbsp;=&nbsp;0.0000).
            Every other weight in the table above is a reasoned starting point, not yet
            tested the same way.
          </p>

          <div style={{
            fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6,
            background: 'rgba(212,68,63,0.06)', border: '1px solid rgba(212,68,63,0.2)',
            borderRadius: 8, padding: '12px 14px', marginTop: 16,
          }}>
            <b style={{ color: 'var(--text-secondary)' }}>What we don't claim:</b> a score of
            8 does not mean the stock will fall. It means multiple independent systems are
            simultaneously flagging elevated risk. The Pinnacle Sentinel-derived points in
            this score are not yet validated the way Pinnacle Veridia's is -- they're a
            defensible prior based on known fraud-detection literature and causal logic,
            pending its own before/after backtest once Pinnacle Sentinel has enough live
            flagging history. The score is an input to your decision, not a verdict.
          </div>
        </Section>

        {/* ============================================================ */}
        {/* PINNACLE SENTINEL divider                                    */}
        {/* ============================================================ */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '32px 0 16px' }}>
          <div style={{
            width: 22, height: 22,
            background: 'linear-gradient(160deg,#1e2d4a,#0f1729)',
            clipPath: 'polygon(50% 0%,100% 20%,100% 70%,50% 100%,0% 70%,0% 20%)',
            border: '1px solid rgba(212,175,55,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <span style={{ color: '#d4af37', fontSize: 10, fontWeight: 800 }}>P</span>
          </div>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 5, color: '#dc2626' }}>
              PINNACLE SENTINEL
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
              SEC filing red flag methodology -- what we detect, and how we'll prove it works
            </div>
          </div>
        </div>

        <h1 style={{ fontSize: 30, fontWeight: 800, marginBottom: 8 }}>How Pinnacle Sentinel works</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 15, marginBottom: 48 }}>
          The thesis, the flags, and how we'll prove -- or disprove -- that any of this predicts anything.
        </p>

        <Section title="The thesis">
          <p style={pText}>
            Public companies leave a trail of structured, legally-mandated disclosures long
            before their problems become obvious in the stock price or the news. An auditor
            resigning, a CFO leaving abruptly, a late filing, a disclosed material weakness,
            an executive accelerating their own stock sales -- none of these alone proves
            fraud or failure, but together, and early, they're a real and underused signal.
          </p>
          <p style={pText}>
            Pinnacle Sentinel watches SEC filings across a stock universe for exactly these
            red flags, scores them by confluence, and validates -- honestly, against real
            price outcomes -- whether flagged companies actually underperform afterward.
          </p>
        </Section>

        <Section title="What we detect">
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: 'var(--blue)', marginBottom: 10, marginTop: 4 }}>
            DISCLOSURE-BASED
          </div>
          {FLAGS.map(f => <FlagLine key={f.name} {...f} />)}

          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: 'var(--red)', marginBottom: 10, marginTop: 24 }}>
            FINANCIAL-RATIO
          </div>
          {QUANT_FLAGS.map(f => <FlagLine key={f.name} {...f} />)}
        </Section>

        <Section title="Confluence scoring">
          <p style={pText}>
            One flag alone is common and often meaningless -- a late filing by itself happens
            for all kinds of ordinary reasons. One flag is a <Badge color="var(--amber)">WATCH</Badge>.
            Two or more flags on the same company in the same window is a much rarer,
            more significant pattern -- an <Badge color="var(--red)">ALERT</Badge>.
          </p>
        </Section>

        <Section title="How we'll prove it, not just assert it">
          <p style={pText}>
            Every flag gets a price recorded at the filing date (T=0), then graded at
            T+30/90/180/365 against the S&P 500 -- tracking excess return, whether the
            stock declined more than 10% or 20%, and the extreme case of bankruptcy or
            delisting within a year.
          </p>
          <p style={pText}>
            The full track record gets published, including flags that turn out to be
            noise. A flag type that doesn't predict anything becomes a disclosed null
            result -- not a hidden failure.
          </p>
        </Section>

        <Section title="What would change our mind">
          <p style={pText}>
            If, once validated, none of these flags -- individually or in confluence --
            show a meaningful relationship with subsequent underperformance, that's a
            publishable honest finding, not a failure to hide. We'd rather tell you a
            signal doesn't work than quietly stop mentioning it.
          </p>
        </Section>
      <RaqaFooter />
      </div>
    </div>
  )
}

const pText = { fontSize: 15, lineHeight: 1.65, color: 'var(--text-secondary)', margin: '0 0 14px' }
const thStyle = { textAlign: 'left', padding: '8px 10px', color: 'var(--text-muted)', fontWeight: 700, fontSize: 11.5, letterSpacing: 0.5, textTransform: 'uppercase' }
const tdStyle = { padding: '8px 10px', color: 'var(--text-secondary)' }

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 40 }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 14 }}>{title}</h2>
      {children}
    </div>
  )
}

function FlagLine({ name, detail }) {
  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: 14, fontWeight: 600 }}>{name}</div>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{detail}</div>
    </div>
  )
}

function Badge({ color, children }) {
  return (
    <span style={{
      display: 'inline-block', fontSize: 12, fontWeight: 700, letterSpacing: 0.5,
      color, border: `1px solid ${color}`, borderRadius: 999, padding: '1px 8px', margin: '0 2px',
    }}>
      {children}
    </span>
  )
}

function ProductCard({ name, accent, question, desc }) {
  return (
    <div style={{
      background: 'var(--navy-800)', border: '1px solid var(--border)', borderRadius: 10,
      padding: '16px 16px', borderLeft: `3px solid ${accent}`,
    }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: accent, marginBottom: 6 }}>{name}</div>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, lineHeight: 1.4 }}>{question}</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{desc}</div>
    </div>
  )
}
