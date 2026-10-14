import { useMemo, useState } from "react";
import { useNotes, useTasks } from "../data/StoreContext";
import {
  addDays,
  dayHeading,
  fromKey,
  relativeDayTitle,
  todayKey,
  weekStart,
  WEEKDAYS,
} from "../lib/date";
import { Screen } from "../components/Screen";
import { useEditors } from "../components/Editors";
import { Segmented } from "../components/Segmented";
import {
  TaskList,
  TaskProgress,
  type AreaFilter,
} from "../components/TaskList";
import { NoteCard } from "../components/NoteCard";
import { DayDots, groupByDate } from "../components/DayDots";
import { InstallBanner } from "../components/InstallBanner";
import {
  IconChevronLeft,
  IconChevronRight,
  IconPlus,
} from "../components/Icons";

const FILTERS: { value: AreaFilter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "work", label: "Работа" },
  { value: "life", label: "Личное" },
];

interface Props {
  date: string;
  onDateChange: (d: string) => void;
  onOpenNotes: () => void;
}

export function DayScreen({ date, onDateChange, onOpenNotes }: Props) {
  const { editTask, editNote } = useEditors();
  const [filter, setFilter] = useState<AreaFilter>("all");

  const start = weekStart(date);
  const end = addDays(start, 6);
  const week = useTasks(start, end);
  const byDate = useMemo(() => groupByDate(week.data), [week.data]);
  const dayTasks = byDate.get(date) ?? [];

  const notes = useNotes();
  const pinned = notes.data.filter((n) => n.pinned);
  const today = todayKey();

  const { title, subtitle } = dayHeading(date);

  return (
    <Screen
      title={title}
      subtitle={subtitle}
      actions={
        <>
          {date !== today && (
            <button
              type="button"
              className="text-btn pressable"
              style={{ fontSize: 15 }}
              onClick={() => onDateChange(today)}
            >
              Сегодня
            </button>
          )}
          <button
            type="button"
            className="icon-btn pressable"
            aria-label="Новая задача"
            onClick={() =>
              editTask({ date, area: filter === "life" ? "life" : "work" })
            }
          >
            <IconPlus />
          </button>
        </>
      }
    >
      <nav className="week" aria-label="Неделя">
        <button
          type="button"
          className="week-arrow pressable"
          aria-label="Предыдущая неделя"
          onClick={() => onDateChange(addDays(date, -7))}
        >
          <IconChevronLeft />
        </button>
        <div className="week-days" role="tablist">
          {Array.from({ length: 7 }, (_, i) => {
            const d = addDays(start, i);
            return (
              <button
                key={d}
                type="button"
                role="tab"
                aria-selected={d === date}
                aria-label={relativeDayTitle(d)}
                className={d === today ? "week-day today" : "week-day"}
                onClick={() => onDateChange(d)}
              >
                <span className="wd">{WEEKDAYS[i]}</span>
                <span className="num">{fromKey(d).getDate()}</span>
                <DayDots tasks={byDate.get(d) ?? []} />
              </button>
            );
          })}
        </div>
        <button
          type="button"
          className="week-arrow pressable"
          aria-label="Следующая неделя"
          onClick={() => onDateChange(addDays(date, 7))}
        >
          <IconChevronRight />
        </button>
      </nav>

      <InstallBanner />

      <section className="section" aria-labelledby="pinned-h">
        <div className="section-head">
          <h2 id="pinned-h">Заметки</h2>
          <button
            type="button"
            className="text-btn pressable"
            onClick={onOpenNotes}
          >
            Все
          </button>
        </div>
        {/* Ленту рисуем после загрузки: иначе scroll-snap «прилипает» к кнопке добавления в конце */}
        {notes.loading && notes.data.length === 0 ? (
          <div className="notes-strip" aria-hidden>
            <div className="skeleton note" />
            <div className="skeleton note" />
          </div>
        ) : (
          <div className="notes-strip fade-in">
            {pinned.map((n) => (
              <NoteCard key={n.id} note={n} />
            ))}
            <button
              type="button"
              className={pinned.length ? 'note add pressable' : 'note add wide pressable'}
              onClick={() => editNote(null)}
            >
              <span>
                <IconPlus />
                {pinned.length
                  ? "Заметка"
                  : "Закрепите заметку —\nона будет на каждом дне"}
              </span>
            </button>
          </div>
        )}
      </section>

      <section className="section" aria-labelledby="plan-h">
        <div className="section-head">
          <h2 id="plan-h">План</h2>
          {dayTasks.length > 0 && (
            <span className="meta">
              {dayTasks.filter((t) => t.done).length} из {dayTasks.length}
            </span>
          )}
        </div>
        <TaskProgress tasks={dayTasks} />
        <div style={{ marginBottom: 12 }}>
          <Segmented
            ariaLabel="Фильтр"
            value={filter}
            options={FILTERS}
            onChange={setFilter}
          />
        </div>
        <TaskList
          date={date}
          tasks={dayTasks}
          loading={week.loading}
          filter={filter}
        />
      </section>
    </Screen>
  );
}
