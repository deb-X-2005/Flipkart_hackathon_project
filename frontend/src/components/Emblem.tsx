/**
 * Stylized police-themed emblem used as a watermark on the login screen.
 * Original SVG (lion-pillar inspired silhouette + shield) — no copyrighted assets.
 */
export function Emblem({ size = 220, opacity = 0.18 }: { size?: number; opacity?: number }) {
  return (
    <svg viewBox="0 0 200 200" width={size} height={size}
         style={{ opacity }} aria-hidden="true">
      <defs>
        <linearGradient id="tri" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0"   stopColor="#ff9933" />
          <stop offset=".5"  stopColor="#ffffff" />
          <stop offset="1"   stopColor="#138808" />
        </linearGradient>
      </defs>
      {/* Outer shield */}
      <path d="M100 8 L185 38 V108 C185 152 145 182 100 192 C55 182 15 152 15 108 V38 Z"
            fill="none" stroke="currentColor" strokeWidth="3" />
      {/* Inner shield band - tricolour gradient */}
      <path d="M100 22 L172 47 V108 C172 145 138 170 100 178 C62 170 28 145 28 108 V47 Z"
            fill="url(#tri)" opacity="0.5" />
      {/* Stylised Ashoka chakra (24 spokes -> 8 simplified) */}
      <circle cx="100" cy="105" r="22" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="100" cy="105" r="3"  fill="currentColor" />
      {Array.from({ length: 8 }).map((_, i) => {
        const a = (i * Math.PI) / 4;
        return (
          <line key={i}
                x1={100 + 4 * Math.cos(a)} y1={105 + 4 * Math.sin(a)}
                x2={100 + 21 * Math.cos(a)} y2={105 + 21 * Math.sin(a)}
                stroke="currentColor" strokeWidth="1.5" />
        );
      })}
      {/* Star at top */}
      <polygon points="100,38 104,50 116,50 106,57 110,69 100,62 90,69 94,57 84,50 96,50"
               fill="currentColor" />
      {/* Banner */}
      <rect x="36" y="148" width="128" height="14" fill="currentColor" opacity="0.85" />
      <text x="100" y="159" textAnchor="middle" fontFamily="sans-serif"
            fontWeight="700" fontSize="9" fill="#fff" letterSpacing="2">
        KARNATAKA POLICE
      </text>
    </svg>
  );
}
