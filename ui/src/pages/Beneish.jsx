import InfoPage, { Section, P, Note, Stat, SimpleTable, RecentFlags, useFlagCounts, Link } from '../components/InfoPage'
import { BENEISH_THRESHOLD } from '../lib/flagInfo'

const VARIABLES = [
  ['DSRI', 'Days sales in receivables index', 'Receivables growing faster than sales'],
  ['GMI', 'Gross margin index', 'Margins deteriorating'],
  ['AQI', 'Asset quality index', 'More assets in soft, non-productive categories'],
  ['SGI', 'Sales growth index', 'Fast growth that creates pressure to keep it up'],
  ['DEPI', 'Depreciation index', 'Slowing depreciation, which lifts reported profit'],
  ['SGAI', 'SG&A expense index', 'Overhead rising against sales'],
  ['LVGI', 'Leverage index', 'More debt relative to assets'],
  ['TATA', 'Total accruals to total assets', 'Profit not backed by cash flow'],
]

export default function Beneish() {
  const { counts } = useFlagCounts()
  const n = counts ? (counts.beneish_manipulation_risk ?? 0) : null
  return (
    <InfoPage subtitle="Beneish M-Score" kicker="FINANCIAL-RATIO FLAG" title="Beneish M-Score"
      lede="A published model that scores how much a company’s financial statements look like those of known earnings manipulators.">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 }}>
        <Stat value={n === null ? '—' : n.toLocaleString()} label="Earnings manipulation risk flags recorded" />
        <Stat value={BENEISH_THRESHOLD} label="flag threshold: M-Score above this" />
      </div>

      <Section title="How it works">
        <P>
          Messod Beneish (1999) compared the financial statements of companies later found to have manipulated earnings
          with those of companies that had not, and found eight year-over-year ratios that separate them. Sentinel
          computes all eight from each company’s reported XBRL financial facts and combines them into one M-Score.
          A higher score means the statements look more like a manipulator’s.
        </P>
        <SimpleTable head={['Variable', 'Measures', 'A warning sign is']} rows={VARIABLES} />
        <P>
          Sentinel raises an <b>earnings manipulation risk</b> flag when the M-Score is above <b>{BENEISH_THRESHOLD}</b>.
          A score is not flagged when one of its inputs is numerically unstable (for example a ratio of ratios that blows up
          on a very small base), because a distorted input would produce a false alarm.
        </P>
      </Section>

      <Section title="Latest flags">
        <RecentFlags flagKey="beneish_manipulation_risk" valueLabel="M-Score" />
        <P><Link to="/flag-analysis" style={{ color: 'var(--red)' }}>All flag types →</Link></P>
      </Section>

      <Note>the M-Score estimates resemblance to past manipulators; it does not establish that any company manipulated its
        earnings, and it has known false positives. Whether Sentinel&#39;s flags predict later underperformance is not validated yet
        (<Link to="/validation" style={{ color: 'var(--red)' }}>Flag Validation</Link>).</Note>
    </InfoPage>
  )
}
