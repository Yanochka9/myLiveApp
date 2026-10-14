import type { Area, Task } from '../data/types'

/** Точки под датой: по одной на сферу, бледные — если всё сделано. */
export function DayDots({ tasks }: { tasks: Task[] }) {
  const areas: Area[] = (['work', 'life'] as const).filter((a) => tasks.some((t) => t.area === a))
  return (
    <span className="dots" aria-hidden>
      {areas.map((a) => (
        <i key={a} className={`dot ${a}${tasks.every((t) => t.area !== a || t.done) ? ' done' : ''}`} />
      ))}
    </span>
  )
}

export function groupByDate(tasks: Task[]): Map<string, Task[]> {
  const map = new Map<string, Task[]>()
  for (const t of tasks) {
    const list = map.get(t.date)
    if (list) list.push(t)
    else map.set(t.date, [t])
  }
  return map
}
