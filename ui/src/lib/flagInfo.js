// One registry for every Sentinel flag: label, severity, source and a plain description.
// The Screener, the flag pages and the analysis pages all read from here so they cannot disagree.
// Thresholds mirror app/services/quant_flags.py (a test keeps the two in step).

export const BENEISH_THRESHOLD = -1.78   // flag when the M-Score is ABOVE this
export const ALTMAN_THRESHOLD = 1.81     // flag when the Z-Score is BELOW this
export const SLOAN_THRESHOLD = 0.10      // flag when the accruals ratio is ABOVE this

// slug: has its own page at /flags/<slug>; page: another dedicated page
export const FLAGS = [
  { key: 'late_filing', label: 'Late filing', severe: false, source: 'disclosure', slug: 'late-filing',
    detail: 'NT 10-K / NT 10-Q -- the filing itself is the flag.' },
  { key: 'auditor_change', label: 'Auditor change', severe: false, source: 'disclosure', slug: 'auditor-change',
    detail: '8-K Item 4.01, and 4.02 when auditor-related.' },
  { key: 'cfo_resignation', label: 'CFO resignation', severe: false, source: 'disclosure', slug: 'cfo-resignation',
    detail: '8-K Item 5.02, classified on the body text.' },
  { key: 'material_weakness', label: 'Material weakness', severe: true, source: 'disclosure', slug: 'material-weakness',
    detail: '8-K Item 4.02 when weakness-related, or 10-K disclosure.' },
  { key: 'accelerated_insider_selling', label: 'Insider selling', severe: false, source: 'disclosure',
    detail: 'Form 4 -- multiple distinct insiders selling (not gifts or option exercises) within a 30-day window.' },
  { key: 'beneish_manipulation_risk', label: 'Earnings manipulation risk', severe: true, source: 'quantitative', page: '/beneish',
    detail: 'Beneish M-Score above the threshold: 8 variables detecting likely earnings manipulation.' },
  { key: 'altman_distress', label: 'Financial distress', severe: true, source: 'quantitative', page: '/altman',
    detail: 'Altman Z-Score below the threshold: 5 variables predicting bankruptcy risk within two years.' },
  { key: 'sloan_ratio_high', label: 'Accrual quality', severe: false, source: 'quantitative',
    detail: 'Sloan accruals ratio above the threshold: earnings running well ahead of cash flow.' },
  { key: 'financial_restatement', label: 'Financial restatement', severe: true, source: 'disclosure',
    detail: '8-K Item 4.02 -- non-reliance on previously issued financial statements.' },
  { key: 'debt_covenant_violation', label: 'Debt covenant violation', severe: false, source: 'disclosure',
    detail: '8-K Item 2.04 -- a triggering event accelerating a financial obligation.' },
  { key: 'going_concern', label: 'Going concern', severe: true, source: 'disclosure',
    detail: '10-K audit opinion language -- substantial doubt about continuing operations.' },
  { key: 'sec_subpoena', label: 'SEC subpoena', severe: true, source: 'disclosure',
    detail: 'Full-text search across 10-K/10-Q/8-K for a disclosed SEC subpoena.' },
  { key: 'sec_investigation', label: 'SEC investigation', severe: true, source: 'disclosure',
    detail: 'Full-text search across 10-K/10-Q/8-K for a disclosed SEC investigation.' },
  { key: 'whistleblower_complaint', label: 'Whistleblower complaint', severe: true, source: 'disclosure',
    detail: 'Full-text search for disclosed whistleblower complaints.' },
]

export const FLAG_LABELS = Object.fromEntries(FLAGS.map(f => [f.key, f.label]))
export const SEVERE_FLAG_TYPES = new Set(FLAGS.filter(f => f.severe).map(f => f.key))

export const flagByKey = key => FLAGS.find(f => f.key === key) || null
export const tierFor = key => (SEVERE_FLAG_TYPES.has(key) ? 'ALERT' : 'WATCH')
export const pageFor = f => (f.slug ? `/flags/${f.slug}` : f.page || null)

// Composite risk score bands (shown on the Methodology page and the Scoring page).
export const SCORE_BANDS = [
  { range: '1-2',   label: 'Clean',    color: 'var(--green)',  action: 'BUY recorded normally' },
  { range: '3-4',   label: 'Elevated', color: 'var(--amber)',  action: 'BUY → WATCH' },
  { range: '5-6',   label: 'High',     color: 'var(--red)',    action: 'BUY → AVOID' },
  { range: '7-9',   label: 'Severe',   color: 'var(--red)',    action: 'BUY → AVOID, full breakdown shown' },
  { range: '10-12', label: 'Extreme',  color: '#8b1a1a',       action: 'BUY → AVOID, prominent warning' },
]
