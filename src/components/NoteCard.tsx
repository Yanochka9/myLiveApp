import type { Note } from '../data/types'
import { useEditors } from './Editors'
import { IconPin } from './Icons'

const updated = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })

export function NoteCard({ note }: { note: Note }) {
  const { editNote } = useEditors()
  const [first, ...rest] = note.text.split('\n')
  return (
    <button type="button" className="note pressable" data-tint={note.tint} onClick={() => editNote(note)}>
      <div className="note-text">
        <span className="first">{first}</span>
        {rest.length > 0 && '\n' + rest.join('\n')}
      </div>
      <div className="note-meta">
        {note.pinned && <IconPin />}
        {updated.format(note.updatedAt)}
      </div>
    </button>
  )
}
