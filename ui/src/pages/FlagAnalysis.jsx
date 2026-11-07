import InfoPage, { Section, P, Note, Stat, SimpleTable, TierBadge, useFlagCounts, Link } from '../components/InfoPage'
import { FLAGS, pageFor } from '../lib/flagInfo'

export default function FlagAnalysis() {
  const { counts, failed } = useFlagCounts()
  const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : null
  const rows = FLAGS.map(f => {
    const page = pageFor(f)
    return [
      page ? <Link key={f.key} to={page} style={{ color: 'var(--red)' }}>{f.label}</Link> : f.label,
      f.source === 'disclosure' ? 'Disclosure' : 'Financial ratio',
      <TierBadge key={`${f.key}-t`} flagKey={f.key} />,
      counts ? (counts[f.key] ?? 0).toLocaleString() : '—',
    ]
  })
  return (
    <InfoPage subtitle="Flag Analysis" kicker="ANALYSIS" title="Flag analysis"
      lede="Every flag type Sentinel watches for, how severe it is on its own, and how many have been recorded.">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 }}>
        <Stat value={total === null ? '—' : total.toLocaleString()} label="flags recorded across all types" />
        <Stat value={FLAGS.length} label="flag types watched" />
      </div>
      <Section title="By flag type">
        {failed && <div style={{ color: 'var(--red)', fontSize: 14 }}>The flag counts are not available right now.</div>}
        <SimpleTable head={['Flag', 'Source', 'On its own', 'Recorded']} rows={rows} />
        <P>Click a flag with a link for its own page and latest events. <Link to="/screener" style={{ color: 'var(--red)' }}>The Screener</Link> lists every flagged company.</P>
      </Section>
      <Note>these are counts of detections. They say how often a flag fired, not whether a flag predicts anything;
        see <Link to="/validation" style={{ color: 'var(--red)' }}>Flag Validation</Link>.</Note>
    </InfoPage>
  )
}
