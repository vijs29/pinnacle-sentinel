import NavBar from '../components/NavBar'
import RaqaFooter from '../components/RaqaFooter'

const FLAGS = [
  { name: 'Late filing', detail: 'NT 10-K / NT 10-Q -- the filing itself is the flag.' },
  { name: 'Auditor change', detail: '8-K Item 4.01, and 4.02 when auditor-related.' },
  { name: 'CFO resignation', detail: '8-K Item 5.02, classified on the body text.' },
  { name: 'Material weakness', detail: '8-K Item 4.02 when weakness-related, or 10-K disclosure.' },
  { name: 'Accelerated insider selling', detail: 'Form 4, against a per-insider historical baseline.' },
]

const QUANT_FLAGS = [
  { name: 'Beneish M-Score', detail: '8 variables detecting likely earnings manipulation.' },
  { name: 'Altman Z-Score', detail: '5 variables predicting bankruptcy risk within two years.' },
  { name: 'Sloan accruals ratio', detail: 'Flags earnings running well ahead of cash flow.' },
]

export default function Methodology() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--navy-900)', color: 'var(--text-primary)' }}>
      <NavBar subtitle="Methodology" />

      <div style={{ maxWidth: 760, margin: '0 auto', padding: '56px 24px 96px' }}>
        <h1 style={{ fontSize: 30, fontWeight: 800, marginBottom: 8 }}>How Sentinel works</h1>
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
            Sentinel watches SEC filings across a stock universe for exactly these red flags,
            scores them by confluence, and validates -- honestly, against real price
            outcomes -- whether flagged companies actually underperform afterward.
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
