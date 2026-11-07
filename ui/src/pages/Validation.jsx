import { useEffect, useState } from 'react'
import InfoPage, { Section, P, Note, Stat, SimpleTable, Link } from '../components/InfoPage'
import { apiFetch } from '../api/client'

// Stages 1, 2, 3, 5 and 6 are recorded in docs/METHODOLOGY.md (Six-Stage Gauntlet, written 2026-08-04).
// Stage 4 is live: it is computed from the database.
const STAGES = [
  ['1', 'Hypothesis registration', 'Falsifiable, written before looking at data', 'Partly done (strategy document)'],
  ['2', 'Walk-forward backtest', '500+ samples, p < 0.05', 'Not started'],
  ['3', 'Factor-model validation', 'Alpha after the Fama-French factors', 'Not started'],
  ['4', 'Forward validation', 'At least 100 live flags graded against outcomes', null],
  ['5', 'Automated daily audit', '20 consecutive clean days', 'Not started'],
  ['6', 'Honest track record published', 'Including the flags that turn out to be noise', 'Not started'],
]

export default function Validation() {
  const [s, setS] = useState(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => { apiFetch('/api/validation/status').then(setS).catch(() => setFailed(true)) }, [])

  const stage4 = !s ? '—' : s.stage4_reached ? 'Reached' : `${s.graded_flags} of ${s.stage4_required} graded`
  const rows = STAGES.map(([n, name, need, status]) => [n, name, need, status === null ? stage4 : status])

  return (
    <InfoPage subtitle="Flag Validation" kicker="METHODOLOGY" title="Flag validation"
      lede="Detecting a flag is not the same as proving it predicts anything. This page shows where Sentinel stands on proving it.">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 }}>
        <Stat value={s ? s.flags_detected.toLocaleString() : '—'} label="flags detected" />
        <Stat value={s ? s.flag_types_seen : '—'} label="flag types seen" />
        <Stat value={s ? s.graded_flags.toLocaleString() : '—'} label="flags graded against outcomes" />
      </div>
      {failed && <div style={{ color: 'var(--red)', fontSize: 14, marginBottom: 16 }}>The live counts are not available right now.</div>}

      <Section title="The six-stage gauntlet">
        <P>A flag only goes live, visible to everyone and wired into Pinnacle Quant, after it passes all six stages.</P>
        <SimpleTable head={['Stage', 'Name', 'Requirement', 'Status']} rows={rows} />
        <P>The counts and the status of stage 4 are read from the database now. The other statuses are as recorded in the
          Sentinel methodology; the full text is on the <Link to="/methodology" style={{ color: 'var(--red)' }}>Methodology</Link> page.</P>
      </Section>

      <Section title="How a flag is graded">
        <P>
          Each flag gets a price recorded on the day it is raised, then is graded 30, 90, 180 and 365 days later against the
          S&amp;P 500. Grading records the excess return, whether the stock fell more than 10% or 20%, and whether it went bankrupt
          or was delisted. The whole record is published, including the flags that turn out to be noise.
        </P>
      </Section>

      <Note>until a flag reaches stage 4 it is a detection, not a prediction. A flag type that does not predict anything is published as a null result,
        never quietly dropped.</Note>
    </InfoPage>
  )
}
