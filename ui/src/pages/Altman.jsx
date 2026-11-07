import InfoPage, { Section, P, Note, Stat, SimpleTable, RecentFlags, useFlagCounts, Link } from '../components/InfoPage'
import { ALTMAN_THRESHOLD } from '../lib/flagInfo'

const TERMS = [
  ['1.2', 'Working capital / total assets', 'Short-term liquidity'],
  ['1.4', 'Retained earnings / total assets', 'Accumulated profitability'],
  ['3.3', 'Operating income / total assets', 'Earning power of the assets'],
  ['0.6', 'Market value of equity / total liabilities', 'How far equity can fall before debt exceeds assets'],
  ['1.0', 'Sales / total assets', 'How hard the assets are working'],
]

export default function Altman() {
  const { counts } = useFlagCounts()
  const n = counts ? (counts.altman_distress ?? 0) : null
  return (
    <InfoPage subtitle="Altman Z-Score" kicker="FINANCIAL-RATIO FLAG" title="Altman Z-Score"
      lede="A published model that scores how close a company is to financial distress, using five numbers from its statements and its market value.">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 }}>
        <Stat value={n === null ? '—' : n.toLocaleString()} label="Financial distress flags recorded" />
        <Stat value={ALTMAN_THRESHOLD} label="flag threshold: Z-Score below this" />
      </div>

      <Section title="How it works">
        <P>
          Edward Altman (1968) built a score from five ratios that separated companies that later went bankrupt from
          those that did not. Each ratio is multiplied by a fixed weight and the results are added:
        </P>
        <SimpleTable head={['Weight', 'Ratio', 'Captures']} rows={TERMS} />
        <P>
          A lower score means more distress. Sentinel raises a <b>financial distress</b> flag when the Z-Score is below{' '}
          <b>{ALTMAN_THRESHOLD}</b>. The balance sheet and income figures come from each company&#39;s reported XBRL financial facts, and
          the market value of equity uses the same price data as Pinnacle Quant.
        </P>
      </Section>

      <Section title="Latest flags">
        <RecentFlags flagKey="altman_distress" valueLabel="Z-Score" />
        <P><Link to="/flag-analysis" style={{ color: 'var(--red)' }}>All flag types →</Link></P>
      </Section>

      <Note>the Z-Score was developed on manufacturing companies and is a rough guide for other kinds of business. A low score
        does not mean a company will fail, and whether Sentinel&#39;s flags predict later underperformance is not validated yet
        (<Link to="/validation" style={{ color: 'var(--red)' }}>Flag Validation</Link>).</Note>
    </InfoPage>
  )
}
