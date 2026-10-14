import type { ComponentType, SVGProps } from 'react'
import { IconCalendar, IconNote, IconPerson, IconToday } from './Icons'

export type Tab = 'day' | 'calendar' | 'notes' | 'profile'

const TABS: { id: Tab; label: string; Icon: ComponentType<SVGProps<SVGSVGElement>> }[] = [
  { id: 'day', label: 'День', Icon: IconToday },
  { id: 'calendar', label: 'Календарь', Icon: IconCalendar },
  { id: 'notes', label: 'Заметки', Icon: IconNote },
  { id: 'profile', label: 'Профиль', Icon: IconPerson },
]

export function TabBar({ tab, onChange }: { tab: Tab; onChange: (t: Tab) => void }) {
  return (
    <nav className="tabbar" role="tablist" aria-label="Разделы">
      {TABS.map(({ id, label, Icon }) => (
        <button key={id} type="button" role="tab" className="tab" aria-selected={tab === id} onClick={() => onChange(id)}>
          <Icon />
          {label}
        </button>
      ))}
    </nav>
  )
}
