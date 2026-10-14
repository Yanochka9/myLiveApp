import { useState, type ReactNode } from 'react'
import { TitleSparkles } from './Sparkles'

interface Props {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}

/** Экран с крупным заголовком; при прокрутке заголовок переезжает в стеклянный навбар. */
export function Screen({ title, subtitle, actions, children }: Props) {
  const [scrolled, setScrolled] = useState(false)
  return (
    <main className="screen" onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 36)}>
      <header className="navbar" data-scrolled={scrolled}>
        <div className="navbar-row">
          <span />
          <span className="navbar-title" aria-hidden>
            {title}
          </span>
          <div className="navbar-actions">{actions}</div>
        </div>
      </header>
      <div className="large-title">
        <h1>
          {title}
          <TitleSparkles />
        </h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      <div className="screen-body">{children}</div>
    </main>
  )
}
