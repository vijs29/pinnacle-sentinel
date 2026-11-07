// One page per disclosure flag (/flags/<slug>): what it is, how it is detected, and the latest real events.
import { Navigate } from 'react-router-dom'
import InfoPage, { Section, P, Note, Stat, RecentFlags, TierBadge, useFlagCounts, Link } from '../components/InfoPage'
import { flagByKey } from '../lib/flagInfo'

export default function FlagPage({ flagKey }) {
  const flag = flagByKey(flagKey)
  const { counts } = useFlagCounts()
  if (!flag) return <Navigate to="/screener" replace />
  const n = counts ? (counts[flag.key] ?? 0) : null

  return (
    <InfoPage subtitle={flag.label} kicker="RED FLAG" title={flag.label} lede={flag.detail}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 }}>
        <Stat value={n === null ? '—' : n.toLocaleString()} label={`${flag.label} flags recorded`} />
        <div style={{ flex: '1 1 160px', display: 'flex', alignItems: 'center' }}><TierBadge flagKey={flag.key} /></div>
      </div>

      <Section title="How it is detected">
        <P>
          {flag.source === 'disclosure'
            ? 'This flag comes from the company’s own SEC disclosures, read from EDGAR. '
            : 'This flag is computed from the company’s reported financial statements. '}
          {flag.detail}
        </P>
        <P>
          On its own this flag is a <b>{flag.severe ? 'severe' : 'common'}</b> signal and is shown as <TierBadge flagKey={flag.key} />.
          Two or more different flags on the same company in the same window are shown as an ALERT, however minor each is alone.
        </P>
      </Section>

      <Section title="Latest recorded">
        <RecentFlags flagKey={flag.key} />
        <P><Link to="/screener" style={{ color: 'var(--red)' }}>See every flag in the Screener →</Link></P>
      </Section>

      <Note>
        a flag is a detection, not a prediction. Whether this flag is followed by underperformance has not been
        validated yet; the status is on the <Link to="/validation" style={{ color: 'var(--red)' }}>Flag Validation</Link> page.
      </Note>
    </InfoPage>
  )
}
