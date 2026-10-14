import { useNotes } from '../data/StoreContext'
import { Screen } from '../components/Screen'
import { useEditors } from '../components/Editors'
import { NoteCard } from '../components/NoteCard'
import { Spinner } from '../components/Spinner'
import { IconPlus } from '../components/Icons'

export function NotesScreen() {
  const { editNote } = useEditors()
  const notes = useNotes()
  const count = notes.data.length

  return (
    <Screen
      title="Заметки"
      subtitle={count ? `${count} ${plural(count, 'заметка', 'заметки', 'заметок')}` : undefined}
      actions={
        <button type="button" className="icon-btn pressable" aria-label="Новая заметка" onClick={() => editNote(null)}>
          <IconPlus />
        </button>
      }
    >
      {notes.loading && count === 0 ? (
        <div className="spinner-center">
          <Spinner large />
        </div>
      ) : count === 0 ? (
        <div className="card empty fade-in">
          <strong>Пока пусто</strong>
          Заметки не привязаны к датам: идеи, списки, важное — всё под рукой каждый день.
          <div style={{ marginTop: 16 }}>
            <button type="button" className="primary-btn pressable" onClick={() => editNote(null)}>
              Новая заметка
            </button>
          </div>
        </div>
      ) : (
        <div className="notes-grid fade-in">
          {notes.data.map((n) => (
            <NoteCard key={n.id} note={n} />
          ))}
        </div>
      )}
    </Screen>
  )
}

function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few
  return many
}
