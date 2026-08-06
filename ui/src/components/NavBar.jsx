/**
 * Pinnacle Sentinel — NavBar wrapper
 * Location: ui/src/components/NavBar.jsx
 *
 * Thin wrapper around the canonical PinnacleNavBar component.
 * D-NAV-001 FINAL (2026-08-06) — design frozen.
 */

import PinnacleNavBar, { STANDARD_INFRA_LINKS } from './PinnacleNavBar'

const SENTINEL_RED = '#d4443f'

const DROPDOWNS = [
  {
    key: 'infrastructure',
    label: 'Infrastructure',
    links: STANDARD_INFRA_LINKS,
  },
  {
    key: 'methodology',
    label: 'Methodology',
    links: [
      { path: '/methodology', label: 'Our Methodology' },
      { path: '/validation',  label: 'Flag Validation' },
      { path: '/scoring',     label: 'Scoring Model' },
    ],
  },
  {
    key: 'analysis',
    label: 'Analysis',
    links: [
      { path: '/flag-analysis',         label: 'Flag Analysis' },
      { path: '/beneish',               label: 'Beneish M-Score' },
      { path: '/altman',                label: 'Altman Z-Score' },
    ],
  },
  {
    key: 'portfolios',
    label: 'Portfolios',
    links: [
      { path: '/universe',    label: 'Universe — 126 tickers' },
      { path: '/portfolios',  label: 'Model Portfolios' },
    ],
  },
  {
    key: 'red-flags',
    label: 'Red Flags',
    links: [
      { path: '/screener',                    label: 'Screener' },
      { path: '/watchlist',                   label: 'Watchlist' },
      { path: '/flags/cfo-resignation',       label: 'CFO Resignations' },
      { path: '/flags/material-weakness',     label: 'Material Weakness' },
      { path: '/flags/auditor-change',        label: 'Auditor Changes' },
      { path: '/flags/late-filing',           label: 'Late Filings' },
    ],
  },
]

const NAV_LINKS = [
  { path: '/screener',  label: 'Screener', emphasize: true },
  { path: '/watchlist', label: 'Watchlist' },
]

const ACCOUNT_LINKS = [
  { path: '/watchlist', label: 'My Watchlist' },
  { path: '/alerts',    label: 'My Alerts' },
]

export default function NavBar({ subtitle, hideBackHome = false }) {
  return (
    <PinnacleNavBar
      product="sentinel"
      wordmark="SENTINEL"
      accentColor={SENTINEL_RED}
      accentVar="var(--sentinel-red)"
      logoSrc="/pinnacle-logo.svg"
      navLinks={NAV_LINKS}
      dropdowns={DROPDOWNS}
      accountLinks={ACCOUNT_LINKS}
      subtitle={subtitle}
      hideBackHome={hideBackHome}
      loginPath="/login"
      registerPath="/register"
    />
  )
}
