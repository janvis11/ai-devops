'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

export function NavbarClient({ items }) {
  const pathname = usePathname();
  const [online, setOnline] = useState(false);

  useEffect(() => {
    const checkAgent = () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      fetch(`${apiUrl}/health`, { method: 'GET' })
        .then((res) => setOnline(res.ok))
        .catch(() => setOnline(false));
    };

    checkAgent();
    const interval = setInterval(checkAgent, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="nav-controls">
      <div className="nav-items">
        {items.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${isActive ? 'nav-link--active' : ''}`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>

      <div className="nav-right-status">
        <div className="live-pill">
          <span className={`live-dot ${online ? '' : 'live-dot--offline'}`} />
          <span>{online ? 'AGENT ONLINE' : 'AGENT OFFLINE'}</span>
        </div>
      </div>

      <style jsx>{`
        .nav-controls {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex: 1;
        }
        .nav-items {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .nav-link {
          font-family: var(--font-mono);
          font-size: 13px;
          font-weight: 500;
          color: var(--navy-70);
          text-decoration: none;
          padding: 6px 14px;
          border-radius: 6px;
          border: 1.5px solid transparent;
          transition: all 100ms ease;
        }
        .nav-link:hover {
          color: var(--k8s-blue);
          background: var(--ice);
        }
        .nav-link--active {
          color: var(--k8s-blue);
          background: var(--ice);
          border-color: var(--navy);
          box-shadow: 2px 2px 0 var(--navy);
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}
