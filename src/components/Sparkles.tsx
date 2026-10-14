import { useState } from 'react'
import { IconSparkle } from './Icons'

/** Несколько медленно мерцающих звёздочек — украшение заголовка. */
export function TitleSparkles() {
  return (
    <span className="title-sparkles" aria-hidden>
      <IconSparkle className="s1" />
      <IconSparkle className="s2" />
      <IconSparkle className="s3" />
    </span>
  )
}

const RAYS = [0, 60, 120, 180, 240, 300]

/** Короткий салют из искорок; перезапускается сменой key. */
export function SparkleBurst() {
  return (
    <span className="burst" aria-hidden>
      {RAYS.map((deg, i) => (
        <IconSparkle key={deg} style={{ '--a': `${deg}deg`, '--d': `${i % 2 ? 15 : 19}px` } as React.CSSProperties} />
      ))}
    </span>
  )
}

/** Хук: возвращает key для перезапуска салюта и функцию-триггер. */
export function useBurst() {
  const [burst, setBurst] = useState(0)
  return [burst, () => setBurst((b) => b + 1)] as const
}
