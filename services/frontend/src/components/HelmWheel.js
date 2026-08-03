export function HelmWheel({ size = 280 }) {
  return (
    <div className="helm-container">
      <svg
        width={size}
        height={size}
        viewBox="0 0 240 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="helm-wheel"
      >
        {/* Outer Ring */}
        <circle cx="120" cy="120" r="95" stroke="var(--k8s-blue)" strokeWidth="4" />
        {/* Inner Hub */}
        <circle cx="120" cy="120" r="32" stroke="var(--k8s-blue)" strokeWidth="4" fill="var(--white)" />
        <circle cx="120" cy="120" r="10" fill="var(--k8s-blue)" />

        {/* Spokes & Handles */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
          <g key={deg} transform={`rotate(${deg} 120 120)`}>
            {/* Spoke */}
            <line x1="120" y1="25" x2="120" y2="88" stroke="var(--k8s-blue)" strokeWidth="4" />
            {/* Handle handle knob outside ring */}
            <circle cx="120" cy="12" r="8" fill="var(--k8s-blue)" />
          </g>
        ))}
      </svg>
      <style jsx>{`
        .helm-container {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: var(--space-lg);
        }
      `}</style>
    </div>
  );
}
