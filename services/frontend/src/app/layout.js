import '@/styles/globals.css';
import Link from 'next/link';
import { NavbarClient } from '@/components/NavbarClient';

export const metadata = {
  title: 'devops.ai — AI-Driven Kubernetes Remediation',
  description: 'Autonomous incident detection, diagnosis, and self-healing for Kubernetes clusters. Powered by LangGraph and Claude.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Navigation />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}

function Navigation() {
  const navItems = [
    { href: '/', label: 'overview.mdx' },
    { href: '/pipeline', label: 'pipeline.yaml' },
    { href: '/feed', label: 'feed.log' },
    { href: '/chaos', label: 'chaos.sh' },
    { href: '/audit', label: 'audit.sql' },
  ];

  return (
    <header className="nav-wrapper">
      <div className="nav-inner container">
        <Link href="/" className="nav-brand">
          <div className="nav-brand-badge">
            <HelmIcon size={20} />
          </div>
          <span className="nav-brand-title">devops.ai</span>
          <span className="nav-brand-tag">k8s</span>
        </Link>
        <NavbarClient items={navItems} />
      </div>
    </header>
  );
}

function HelmIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <circle cx="12" cy="12" r="3" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <line x1="12" y1="2" x2="12" y2="9" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <line x1="12" y1="15" x2="12" y2="22" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <line x1="2" y1="12" x2="9" y2="12" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <line x1="15" y1="12" x2="22" y2="12" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <line x1="4.93" y1="4.93" x2="9.88" y2="9.88" stroke="var(--k8s-blue)" strokeWidth="2.2" />
      <line x1="14.12" y1="14.12" x2="19.07" y2="19.07" stroke="var(--k8s-blue)" strokeWidth="2.2" />
    </svg>
  );
}

function Footer() {
  const stackChips = [
    'k3s', 'ArgoCD', 'Prometheus', 'Grafana', 'Loki', 'Kafka',
    'LangGraph', 'Claude 3.5', 'Vault', 'OPA Gatekeeper', 'Jaeger', 'Fluentd',
  ];

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-chips">
          {stackChips.map((chip) => (
            <span key={chip} className="footer-chip">{chip}</span>
          ))}
        </div>
        <p className="footer-copy">© devops.ai · AI-driven remediation for Kubernetes</p>
      </div>
    </footer>
  );
}
