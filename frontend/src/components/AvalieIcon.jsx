import { useId } from 'react';

export default function AvalieIcon({ size = 48, rounded = true, className = '' }) {
  const gid = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 1024 1024"
      className={className} role="img" aria-label="AvalieImob">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#DCC06A" />
          <stop offset="0.55" stopColor="#CBA847" />
          <stop offset="1" stopColor="#B0882B" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="1024" height="1024" rx={rounded ? 200 : 0} fill={`url(#${gid})`} />
      <path fill="#0C3320" fillRule="evenodd"
        d="M512 208 L820 808 L628 808 L512 506 L396 808 L204 808 Z
           M512 366 L450 478 L574 478 Z" />
    </svg>
  );
}
