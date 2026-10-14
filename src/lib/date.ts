const pad = (n: number) => String(n).padStart(2, '0')

export function toKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function fromKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export const todayKey = () => toKey(new Date())

export function addDays(key: string, days: number): string {
  const d = fromKey(key)
  d.setDate(d.getDate() + days)
  return toKey(d)
}

/** Понедельник недели, в которой лежит дата */
export function weekStart(key: string): string {
  const d = fromKey(key)
  return addDays(key, -((d.getDay() + 6) % 7))
}

/** 6 недель (42 дня) сетки месяца, начиная с понедельника */
export function monthGrid(year: number, month: number): string[] {
  const start = weekStart(toKey(new Date(year, month, 1)))
  return Array.from({ length: 42 }, (_, i) => addDays(start, i))
}

const fmt = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('ru-RU', opts)
const weekdayLong = fmt({ weekday: 'long' })
const dayMonth = fmt({ day: 'numeric', month: 'long' })
const monthYear = fmt({ month: 'long', year: 'numeric' })
const weekdayShort = fmt({ weekday: 'short' })

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

export const formatWeekday = (key: string) => cap(weekdayLong.format(fromKey(key)))
export const formatWeekdayShort = (key: string) => cap(weekdayShort.format(fromKey(key)))
export const formatDayMonth = (key: string) => dayMonth.format(fromKey(key))
export const formatMonthYear = (year: number, month: number) =>
  cap(monthYear.format(new Date(year, month, 1)).replace(/\s?г\.$/, ''))

export const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

/** «Сегодня», «Завтра», «Вчера» или «Пятница, 17 октября» */
export function relativeDayTitle(key: string): string {
  const today = todayKey()
  if (key === today) return 'Сегодня'
  if (key === addDays(today, 1)) return 'Завтра'
  if (key === addDays(today, -1)) return 'Вчера'
  return `${formatWeekday(key)}, ${formatDayMonth(key)}`
}
