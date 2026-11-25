import "./BrandLogo.css"

export default function BrandLogo({ size = 32, iconOnly = false, className = "" }) {
  const classes = ["brand-logo", iconOnly && "brand-logo-icon-only", className].filter(Boolean).join(" ")

  return (
    <span
      className={classes}
      role={iconOnly ? "img" : undefined}
      aria-label={iconOnly ? "CodeDuel AI" : undefined}
    >
      <svg
        className="brand-logo-icon"
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        focusable="false"
      >
        <rect width="100" height="100" rx="22" fill="#0F1218" />
        <path
          d="M50 10L84.6 30V70L50 90L15.4 70V30L50 10Z"
          stroke="#4DA3FF"
          strokeWidth="4.5"
          strokeLinejoin="round"
        />
        <path
          d="M42 32L26 50L42 68"
          stroke="#4DA3FF"
          strokeWidth="6.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M58 32L74 50L58 68"
          stroke="#FF7A45"
          strokeWidth="6.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M52 29L45.5 49.5H54.5L48 71"
          stroke="#FFD43B"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M79 14L82.5 21L90 24L82.5 27L79 34L75.5 27L68 24L75.5 21L79 14Z" fill="#FF7A45" />
      </svg>
      {!iconOnly && (
        <span className="brand-logo-wordmark">
          code<span>duel</span><small>.dev</small>
        </span>
      )}
    </span>
  )
}
