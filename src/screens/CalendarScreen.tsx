import { useMemo, useState } from 'react'
import { useTasks } from '../data/StoreContext'
import { dayHeading, formatDayMonth, formatMonthYear, fromKey, monthGrid, todayKey, WEEKDAYS } from '../lib/date'
import { Screen } from '../components/Screen'
import { useEditors } from '../components/Editors'
import { TaskList } from '../components/TaskList'
import { DayDots, groupByDate } from '../components/DayDots'
import { IconChevronLeft, IconChevronRight, IconPlus } from '../components/Icons'

interface Props {
  date: string
  onDateChange: (d: string) => void
  onOpenDay: () => void
}

export function CalendarScreen({ date, onDateChange, onOpenDay }: Props) {
  const { editTask } = useEditors()
  const selected = fromKey(date)
  const [month, setMonth] = useState({ y: selected.getFullYear(), m: selected.getMonth() })

  const grid = useMemo(() => monthGrid(month.y, month.m), [month])
  const range = useTasks(grid[0], grid[grid.length - 1])
  const byDate = useMemo(() => groupByDate(range.data), [range.data])
  const today = todayKey()

  const shift = (delta: number) =>
    setMonth(({ y, m }) => {
      const d = new Date(y, m + delta, 1)
      return { y: d.getFullYear(), m: d.getMonth() }
    })

  const goToday = () => {
    const now = new Date()
    setMonth({ y: now.getFullYear(), m: now.getMonth() })
    onDateChange(today)
  }

  const dayTasks = byDate.get(date) ?? []
  const heading = dayHeading(date)

  return (
    <Screen
      title="Календарь"
      actions={
        <button type="button" className="text-btn pressable" style={{ fontSize: 15 }} onClick={goToday}>
          Сегодня
        </button>
      }
    >
      <div className="card cal">
        <div className="cal-head">
          <h2 aria-live="polite">{formatMonthYear(month.y, month.m)}</h2>
          <div className="arrows">
            <button type="button" className="pressable" aria-label="Предыдущий месяц" onClick={() => shift(-1)}>
              <IconChevronLeft />
            </button>
            <button type="button" className="pressable" aria-label="Следующий месяц" onClick={() => shift(1)}>
              <IconChevronRight />
            </button>
          </div>
        </div>
        <div className="cal-grid" role="grid">
          {WEEKDAYS.map((w) => (
            <div key={w} className="cal-wd" role="columnheader">
              {w}
            </div>
          ))}
          {grid.map((d) => {
            const dt = fromKey(d)
            const cls = ['cal-day', dt.getMonth() !== month.m && 'out', d === today && 'today'].filter(Boolean).join(' ')
            return (
              <button
                key={d}
                type="button"
                role="gridcell"
                className={cls}
                aria-selected={d === date}
                aria-label={formatDayMonth(d)}
                onClick={() => onDateChange(d)}
              >
                <span className="num">{dt.getDate()}</span>
                <DayDots tasks={byDate.get(d) ?? []} />
              </button>
            )
          })}
        </div>
      </div>

      <section className="section" aria-labelledby="cal-day-h">
        <div className="day-head">
          <button type="button" className="pressable" style={{ textAlign: 'left' }} onClick={onOpenDay}>
            <h2 id="cal-day-h">
              {heading.title} <IconChevronRight style={{ width: 14, height: 14, color: 'var(--label-3)' }} />
            </h2>
            <p>{heading.subtitle}</p>
          </button>
          <button type="button" className="icon-btn pressable" aria-label="Новая задача на этот день" onClick={() => editTask({ date, area: 'work' })}>
            <IconPlus />
          </button>
        </div>
        <TaskList date={date} tasks={dayTasks} loading={range.loading} filter="all" />
      </section>
    </Screen>
  )
}
