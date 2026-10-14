import type { SVGProps } from 'react'

// Иконки в духе SF Symbols: штрих 1.8, скруглённые концы, currentColor.
type P = SVGProps<SVGSVGElement>

const base = (p: P) => ({
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  ...p,
})

export const IconToday = (p: P) => (
  <svg {...base(p)}>
    <rect x="3.5" y="4.5" width="17" height="16" rx="3.5" />
    <path d="M3.5 9.5h17M8 2.8v3.4M16 2.8v3.4" />
    <path d="m9 14.6 2 2 4-4.2" />
  </svg>
)

export const IconCalendar = (p: P) => (
  <svg {...base(p)}>
    <rect x="3.5" y="4.5" width="17" height="16" rx="3.5" />
    <path d="M3.5 9.5h17M8 2.8v3.4M16 2.8v3.4" />
    <circle cx="8.3" cy="13.4" r=".6" fill="currentColor" />
    <circle cx="12" cy="13.4" r=".6" fill="currentColor" />
    <circle cx="15.7" cy="13.4" r=".6" fill="currentColor" />
    <circle cx="8.3" cy="16.8" r=".6" fill="currentColor" />
    <circle cx="12" cy="16.8" r=".6" fill="currentColor" />
  </svg>
)

export const IconNote = (p: P) => (
  <svg {...base(p)}>
    <path d="M6.5 3.5h11a3 3 0 0 1 3 3v8.2L14.7 20.5H6.5a3 3 0 0 1-3-3v-11a3 3 0 0 1 3-3Z" />
    <path d="M20.5 14.5h-3.3a2.5 2.5 0 0 0-2.5 2.5v3.5M7.5 8.5h9M7.5 12.5h5" />
  </svg>
)

export const IconPerson = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="10" r="3.2" />
    <path d="M6.3 18.4c1.3-1.9 3.3-2.9 5.7-2.9s4.4 1 5.7 2.9" />
  </svg>
)

export const IconPlus = (p: P) => (
  <svg {...base({ strokeWidth: 2.2, ...p })}>
    <path d="M12 5v14M5 12h14" />
  </svg>
)

export const IconCheck = (p: P) => (
  <svg {...base({ strokeWidth: 3, ...p })}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </svg>
)

export const IconChevronLeft = (p: P) => (
  <svg {...base({ strokeWidth: 2.4, ...p })}>
    <path d="m15 5-7 7 7 7" />
  </svg>
)

export const IconChevronRight = (p: P) => (
  <svg {...base({ strokeWidth: 2.4, ...p })}>
    <path d="m9 5 7 7-7 7" />
  </svg>
)

export const IconPin = (p: P) => (
  <svg {...base(p)}>
    <path d="M9 3.5h6l-1 5.5 3.5 3.5v1.5h-11V12.5L10 9 9 3.5ZM12 14v6.5" />
  </svg>
)

export const IconClock = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </svg>
)

export const IconBriefcase = (p: P) => (
  <svg {...base(p)}>
    <rect x="3.5" y="7.5" width="17" height="12" rx="2.5" />
    <path d="M9 7.5V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1.5M3.5 12.5h17" />
  </svg>
)

export const IconHeart = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 19.5s-7.5-4.4-7.5-10A4.3 4.3 0 0 1 12 6.6a4.3 4.3 0 0 1 7.5 2.9c0 5.6-7.5 10-7.5 10Z" />
  </svg>
)

export const IconShare = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 3.5v11M8 7.5l4-4 4 4" />
    <path d="M8.5 10.5h-2a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-2" />
  </svg>
)

export const IconClose = (p: P) => (
  <svg {...base({ strokeWidth: 2.4, ...p })}>
    <path d="M6 6l12 12M18 6 6 18" />
  </svg>
)

export const IconCloud = (p: P) => (
  <svg {...base(p)}>
    <path d="M7 18.5a4.5 4.5 0 0 1-.6-9 5.5 5.5 0 0 1 10.6 1.4 3.8 3.8 0 0 1-.5 7.6H7Z" />
  </svg>
)

/** Четырёхлучевая звёздочка-блёстка */
export const IconSparkle = (p: P) => (
  <svg viewBox="0 0 24 24" aria-hidden {...p}>
    <path fill="currentColor" d="M12 1.5c.5 5.6 3.4 8.6 10.5 10.5-7.1 1.9-10 4.9-10.5 10.5-.5-5.6-3.4-8.6-10.5-10.5C8.6 10.1 11.5 7.1 12 1.5Z" />
  </svg>
)
