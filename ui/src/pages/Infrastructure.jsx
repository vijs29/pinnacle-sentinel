import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { BASE_URL } from '../api/client'
import NavBar from '../components/NavBar'

const VIJAY_EMAIL = 'vijay.cloudarchitect@gmail.com'

function SectionTitle({ title }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 600, letterSpacing: '0.1em',
      textTransform: 'uppercase', color: 'var(--text-muted)',
      marginBottom: 12, paddingBottom: 8,
      borderBottom: '0.5px solid var(--border-light)',
    }}>{title}</div>
  )
}

function ServiceCard({ icon, name, description, detail, isVijay }) {
  return (
    <div style={{
      background: 'var(--surface-1)', border: '0.5px solid var(--border-light)',
      borderRadius: 8, padding: '14px 16px', marginBottom: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ fontSize: 20, flexShrink: 0 }}>{icon}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>
            {name}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {description}
          </div>
          {isVijay && detail && (
            <div style={{
              marginTop: 8, padding: '6px 10px',
              background: 'rgba(212,175,55,0.08)', border: '0.5px solid rgba(212,175,55,0.2)',
              borderRadius: 5, fontSize: 11, color: 'var(--gold-400)', fontFamily: 'monospace',
              lineHeight: 1.7, whiteSpace: 'pre-line',
            }}>
              {detail}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const colors = {
    live: { bg: 'rgba(16,185,129,0.12)', color: '#10b981' },
    planned: { bg: 'rgba(180,83,9,0.12)', color: '#b45309' },
    'in progress': { bg: 'rgba(2,132,199,0.12)', color: '#0284c7' },
  }
  const cfg = colors[status.toLowerCase()] || colors.planned
  return (
    <span style={{
      display: 'inline-block', padding: '1px 7px', borderRadius: 4,
      fontSize: 10, fontWeight: 600,
      background: cfg.bg, color: cfg.color, marginLeft: 8,
    }}>{status}</span>
  )
}

const SECTIONS = {
  aws: {
    title: '☁ AWS Services',
    content: (isVijay) => (
      <>
        <ServiceCard icon="🖥" name="Amazon EC2"
          description="Virtual server hosting all three Pinnacle Platform products. Single instance running Docker containers for Pinnacle Quant, Pinnacle Veridia, and Pinnacle Sentinel."
          detail={`Instance: t3.medium (2 vCPU, 4GB RAM)\nRegion: us-west-1 (N. California)\nIP: 52.52.131.132\nOS: Ubuntu 24.04 LTS`}
          isVijay={isVijay} />
        <ServiceCard icon="🌐" name="Amazon Route 53"
          description="DNS management for pinnacletranscore.com and all product subdomains (quant, veridia, sentinel)."
          detail={`Domain: pinnacletranscore.com\nSubdomains: quant.*, veridia.*, sentinel.*`}
          isVijay={isVijay} />
        <ServiceCard icon="🔐" name="AWS IAM"
          description="Identity and access management. SSH key-only EC2 access -- no password authentication."
          detail={`SSH key: pinnacle-quant-ed25519-20260702\nAuth: Ed25519 key pair only`}
          isVijay={isVijay} />
      </>
    )
  },
  containers: {
    title: '🐳 Docker & Containers',
    content: (isVijay) => (
      <>
        <ServiceCard icon="📦" name="Docker Compose"
          description="Orchestrates all platform containers on a single host. Each product runs in its own container with shared networking."
          detail={`Network: pinnacle_default (bridge)\nContainers: pinnacle-app-1, pinnacle-veridia-veridia-app-1,\npinnacle-sentinel-app-1, pinnacle-db-1, pinnacle-caddy-1`}
          isVijay={isVijay} />
        <ServiceCard icon="🔀" name="Caddy"
          description="Reverse proxy and automatic HTTPS. Routes traffic from public subdomains to the correct container. Handles SSL certificate renewal automatically via Let's Encrypt."
          detail={`Config: /home/ubuntu/pinnacle/Caddyfile\nCerts: automatic via Let's Encrypt\nPorts: 80/443 → internal 8000/8003/8010`}
          isVijay={isVijay} />
        <ServiceCard icon="🗄" name="PostgreSQL 16"
          description="Primary database for all three products. Cross-product read-only users enable secure data sharing between Pinnacle products."
          detail={`Container: pinnacle-db-1\nDatabases: pinnacle (Quant+Sentinel), pinnacle_sentinel\nRead-only users: veridia_ro, sentinel_ro`}
          isVijay={isVijay} />
      </>
    )
  },
  ansible: {
    title: '📦 Ansible — Deployment Automation',
    content: (isVijay) => (
      <>
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 12,
          background: 'rgba(2,132,199,0.06)', border: '0.5px solid rgba(2,132,199,0.2)',
          fontSize: 12, color: '#0284c7',
        }}>
          🚧 In progress -- replacing manual deployment with fully automated, auditable playbooks
        </div>
        {[
          { icon: '📋', name: 'Ansible Collections', status: 'planned', description: 'community.docker for container management, community.postgresql for database users and grants, community.crypto for SSL/TLS certificates.' },
          { icon: '🔒', name: 'Ansible Vault', status: 'planned', description: 'Encrypted secrets management. Replaces manual .env file editing. All credentials stored encrypted in git.' },
          { icon: '🎭', name: 'Ansible Roles', status: 'planned', description: 'Structured, reusable playbooks per product: pinnacle_quant, pinnacle_veridia, pinnacle_sentinel, postgres_users, caddy, common.' },
          { icon: '📝', name: 'Jinja2 Templates', status: 'planned', description: 'Generate .env files from vault variables. Eliminates manual environment configuration on the server.' },
          { icon: '🏷', name: 'Ansible Tags', status: 'planned', description: 'Deploy only what changed: --tags quant deploys Pinnacle Quant only. --tags db_users updates database permissions only.' },
          { icon: '🧪', name: 'Molecule Testing', status: 'planned', description: 'Test-driven infrastructure. Roles tested in isolation using Docker before being applied to production.' },
        ].map(({ icon, name, description, status }) => (
          <div key={name} style={{
            background: 'var(--surface-1)', border: '0.5px solid var(--border-light)',
            borderRadius: 8, padding: '14px 16px', marginBottom: 10,
            display: 'flex', gap: 12, alignItems: 'flex-start',
          }}>
            <div style={{ fontSize: 18, flexShrink: 0 }}>{icon}</div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>
                {name} <StatusBadge status={status} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{description}</div>
            </div>
          </div>
        ))}
      </>
    )
  },
  terraform: {
    title: '⚡ Terraform — Infrastructure as Code',
    content: (isVijay) => (
      <ServiceCard icon="🏗" name="Terraform via QuantInfra AI"
        description="Infrastructure provisioning as code. QuantInfra AI generates Terraform configurations for multi-cloud deployments. Manages EC2, networking, security groups, and DNS programmatically."
        detail={`QuantInfra AI: quantinfra.pinnacletranscore.com\nProviders: AWS, GCP, Azure\nState: local (S3 backend planned)`}
        isVijay={isVijay} />
    )
  },
  security: {
    title: '🔒 Security',
    content: () => (
      <>
        {[
          { icon: '🔑', name: 'JWT Authentication', description: 'JSON Web Token authentication on all three products. Tokens expire and are refreshed automatically. No session cookies.' },
          { icon: '🛡', name: 'AES-256 Fernet Encryption', description: 'Alpaca API keys stored encrypted in the database using AES-256 Fernet symmetric encryption. Keys never stored in plaintext.' },
          { icon: '👁', name: 'Read-Only Cross-Product DB Users', description: 'Pinnacle Veridia and Pinnacle Sentinel access Pinnacle Quant data via scoped read-only database users (veridia_ro, sentinel_ro). No write access across product boundaries.' },
          { icon: '🚫', name: 'SSH Key-Only Access', description: 'EC2 server accessible only via Ed25519 SSH key pair. Password authentication disabled. No root login.' },
          { icon: '🌐', name: 'HTTPS Everywhere', description: "All traffic encrypted via TLS. Certificates issued and renewed automatically by Let's Encrypt via Caddy. HTTP redirects to HTTPS." },
        ].map(({ icon, name, description }) => (
          <ServiceCard key={name} icon={icon} name={name} description={description} isVijay={false} />
        ))}
      </>
    )
  },
  connectivity: {
    title: '🔗 Cross-Product Connectivity',
    content: (isVijay) => (
      <>
        <ServiceCard icon="📊" name="Pinnacle Veridia → Pinnacle Quant (live)"
          description="Pinnacle Veridia writes a daily per-ticker VaR forecast. Pinnacle Quant reads it at scan time and downgrades BUY signals to WATCH when volatility risk is elevated. Statistically validated: 1.78x lift in miss rate (p=0.0000)."
          detail={`File: /veridia_data/ticker_var_forecast_latest.json\nMount: Docker volume (read-only)\nValidation: D-016`}
          isVijay={isVijay} />
        <ServiceCard icon="🚨" name="Pinnacle Sentinel → Pinnacle Quant (planned)"
          description="Pinnacle Sentinel will write daily red flag summaries per ticker. Pinnacle Quant will read them and adjust composite risk scores. BUY signals on flagged tickers will be downgraded."
          detail={`File: /sentinel_data/flag_summary_latest.json\nStatus: Planned — D-018`}
          isVijay={isVijay} />
        <ServiceCard icon="🔍" name="Pinnacle Veridia cross-product DB access"
          description="Pinnacle Veridia queries Pinnacle Quant's predictions and miss_analysis tables directly via a read-only database user to power the cross-product correlation page."
          detail={`DB user: veridia_ro\nAccess: SELECT on predictions, miss_analysis\nValidation: D-015 (p=0.0008, 1.46x lift)`}
          isVijay={isVijay} />
      </>
    )
  },
}

export default function Infrastructure() {
  const [isVijay, setIsVijay] = useState(false)
  const location = useLocation()
  const params = new URLSearchParams(location.search)
  const activeSection = params.get('section')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    fetch(`${BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.email === VIJAY_EMAIL) setIsVijay(true)
      })
      .catch(() => {})
  }, [])

  const sectionsToShow = activeSection
    ? (SECTIONS[activeSection] ? [activeSection] : Object.keys(SECTIONS))
    : Object.keys(SECTIONS)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <NavBar />
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 20px' }}>

        <div style={{ marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 30, height: 30,
              background: 'linear-gradient(160deg,#1e2d4a,#0f1729)',
              clipPath: 'polygon(50% 0%,100% 20%,100% 70%,50% 100%,0% 70%,0% 20%)',
              border: '1px solid rgba(212,175,55,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{ color: '#d4af37', fontSize: 13, fontWeight: 800 }}>P</span>
            </div>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 5, color: '#d4af37' }}>PINNACLE PLATFORM</div>
              <div style={{ fontSize: 9, letterSpacing: 3, color: 'var(--text-muted)' }}>INFRASTRUCTURE</div>
            </div>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
            {activeSection && SECTIONS[activeSection]
              ? SECTIONS[activeSection].title
              : 'Platform Infrastructure'}
          </h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            {activeSection
              ? 'The services and tools that power the Pinnacle Platform.'
              : 'The services and tools that power Pinnacle Quant, Pinnacle Veridia, and Pinnacle Sentinel. Built on open standards, deployed on AWS, automated with Ansible.'}
          </div>
          {isVijay && (
            <div style={{
              marginTop: 10, padding: '6px 12px', borderRadius: 6,
              background: 'rgba(212,175,55,0.08)', border: '0.5px solid rgba(212,175,55,0.2)',
              fontSize: 11, color: 'var(--gold-400)', display: 'inline-block',
            }}>
              🔑 Admin view -- infrastructure details visible
            </div>
          )}
        </div>

        {sectionsToShow.map(key => {
          const section = SECTIONS[key]
          if (!section) return null
          return (
            <div key={key} style={{ marginBottom: 32 }}>
              <SectionTitle title={section.title} />
              {section.content(isVijay)}
            </div>
          )
        })}

        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.8, marginTop: 8 }}>
          Infrastructure details updated July 2026 · Built by RAQA Consultancy LLC ·
          Powered by open-source tools and AWS
        </div>

      </div>
    </div>
  )
}
