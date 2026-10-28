const icons = {
  logo: (
    <>
      <path d="M12 3v3M12 18v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M3 12h3M18 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
      <circle cx="12" cy="12" r="3.2" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3-1.2 3.4L7.4 7.6l3.4 1.2L12 12l1.2-3.2 3.4-1.2-3.4-1.2L12 3Z" />
      <path d="m5 14-.8 2.2L2 17l2.2.8L5 20l.8-2.2L8 17l-2.2-.8L5 14Z" />
      <path d="m18.5 13-.7 1.8-1.8.7 1.8.7.7 1.8.7-1.8 1.8-.7-1.8-.7-.7-1.8Z" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  x: <path d="m6 6 12 12M18 6 6 18" />,
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  paperclip: (
    <path d="m20.5 11.5-8.1 8.1a6 6 0 0 1-8.5-8.5l8.8-8.8a4 4 0 1 1 5.7 5.7l-8.8 8.8a2 2 0 1 1-2.8-2.8l8.1-8.1" />
  ),
  send: (
    <>
      <path d="m21 3-7.2 18-3.4-7.4L3 10.2 21 3Z" />
      <path d="M10.4 13.6 21 3" />
    </>
  ),
  arrowUp: <path d="M12 19V5M6 11l6-6 6 6" />,
  brain: (
    <>
      <path d="M9.5 4.5A3 3 0 0 0 4 6.2a3 3 0 0 0-1 5.6A3 3 0 0 0 5 17a3 3 0 0 0 4.5 2.5V4.5Z" />
      <path d="M14.5 4.5A3 3 0 0 1 20 6.2a3 3 0 0 1 1 5.6A3 3 0 0 1 19 17a3 3 0 0 1-4.5 2.5V4.5Z" />
      <path d="M9.5 9H7.8M9.5 14H7M14.5 9h1.7M14.5 14H17" />
    </>
  ),
  database: (
    <>
      <ellipse cx="12" cy="5.5" rx="7.5" ry="3" />
      <path d="M4.5 5.5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6" />
      <path d="M4.5 11.5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 11a8 8 0 1 0-2.3 6.4" />
      <path d="M20 4v7h-7" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14" />
      <path d="M10 11v6M14 11v6" />
    </>
  ),
  pencil: (
    <>
      <path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20Z" />
      <path d="m13.5 6.5 3 3" />
    </>
  ),
  check: <path d="m5 12.5 4.2 4.2L19 6.5" />,
  copy: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3 2.8 19h18.4L12 3Z" />
      <path d="M12 9v4M12 16.5v.1" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8v.1" />
    </>
  ),
  file: (
    <>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z" />
      <path d="M14 3v6h6" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="1.5" />
      <path d="m21 15-5-5L5 20" />
    </>
  ),
  download: (
    <>
      <path d="M12 3v12M7 10l5 5 5-5" />
      <path d="M5 21h14" />
    </>
  ),
  message: (
    <>
      <path d="M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8Z" />
      <path d="M8 11h.1M12 11h.1M16 11h.1" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 21a6.5 6.5 0 0 1 13 0" />
      <path d="M16 5.2a3.5 3.5 0 0 1 0 6.6M18 14.6a6.5 6.5 0 0 1 3.5 5.8" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 4.5 6v5.5c0 4.4 3.1 7.7 7.5 9.5 4.4-1.8 7.5-5.1 7.5-9.5V6L12 3Z" />
      <path d="m8.5 12 2.3 2.3 4.7-4.6" />
    </>
  ),
  wifi: (
    <>
      <path d="M3 9a15 15 0 0 1 18 0M6 12.5a10 10 0 0 1 12 0M9 16a5 5 0 0 1 6 0" />
      <circle cx="12" cy="19" r=".6" fill="currentColor" stroke="none" />
    </>
  ),
  cloudOff: (
    <>
      <path d="M5.5 18.5h11a4 4 0 0 0 1.2-7.8A6 6 0 0 0 7 9.5a4.5 4.5 0 0 0-1.5 9Z" />
      <path d="m3 3 18 18" />
    </>
  ),
  memory: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="3" />
      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3" />
      <path d="M9 9h6v6H9z" />
    </>
  ),
  activity: <path d="M3 12h4l2.5-7 5 14 2.5-7h4" />,
  external: (
    <>
      <path d="M14 3h7v7M21 3l-9 9" />
      <path d="M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" />
    </>
  ),
};

export default function Icon({
  name,
  size = 18,
  strokeWidth = 1.8,
  className = "",
  ...props
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {icons[name] || icons.sparkles}
    </svg>
  );
}
