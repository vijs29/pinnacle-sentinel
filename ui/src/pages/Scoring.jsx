import InfoPage, { Section, P, Note, Badge, SimpleTable, Link } from '../components/InfoPage'
import { SCORE_BANDS } from '../lib/flagInfo'

export default function Scoring() {
  return (
    <InfoPage subtitle="Scoring Model" kicker="METHODOLOGY" title="Scoring model"
      lede="How Sentinel turns individual flags into a company-level signal, and how that feeds the platform's composite risk score.">
      <Section title="Step 1: confluence on one company">
        <P>
          One flag on a company is common and often ordinary, so it is shown as a <Badge color="var(--amber)">WATCH</Badge>.
          Two or more different flags on the same company in the same window are far rarer, and are shown as an{' '}
          <Badge color="var(--red)">ALERT</Badge>. Flags are additive and each flag type counts once, so a repeated flag does
          not raise the level by itself.
        </P>
        <P>On their own, some flags are treated as severe (for example a material weakness, going concern or a restatement) and others as common (for example a late filing).
          The full list with each flag&#39;s level is on the <Link to="/flag-analysis" style={{ color: 'var(--red)' }}>Flag Analysis</Link> page.</P>
      </Section>

      <Section title="Step 2: the platform's composite score, 1 to 12">
        <P>The composite score combines Sentinel, Veridia and Quant into a single number and tells Pinnacle Quant how to treat a bullish signal.</P>
        <SimpleTable head={['Score', 'Label', 'What Pinnacle Quant does']}
          rows={SCORE_BANDS.map(b => [b.range, <span key={b.range} style={{ color: b.color, fontWeight: 700 }}>{b.label}</span>, b.action])} />
        <P>How the 12 points are built, and which weight has been tested, is explained on the <Link to="/methodology" style={{ color: 'var(--red)' }}>Methodology</Link> page.</P>
      </Section>

      <Note>the score is a risk filter, not a prediction. Sentinel&#39;s contribution to it has not yet been validated against outcomes
        (<Link to="/validation" style={{ color: 'var(--red)' }}>Flag Validation</Link>).</Note>
    </InfoPage>
  )
}
