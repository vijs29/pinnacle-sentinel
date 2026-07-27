export default function RaqaFooter() {
  return (
    <a
      href="https://raqa.pinnacletranscore.com"
      target="_blank"
      rel="noopener noreferrer"
      style={{
        borderTop: '1px solid var(--border)', padding: '20px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        textDecoration: 'none', cursor: 'pointer',
      }}
    >
      <img src="/raqa-logo.svg" alt="RAQA Consultancy" style={{ height: 18, width: 18 }} />
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: 'var(--gold-400)' }}>
        RAQA CONSULTANCY
      </span>
    </a>
  )
}
