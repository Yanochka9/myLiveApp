import { useState } from 'react'
import { useStore } from '../data/StoreContext'
import type { Note, NoteTint } from '../data/types'
import { Sheet } from './Sheet'
import { Switch } from './Switch'
import { IconPin } from './Icons'

const TINTS: { value: NoteTint; label: string }[] = [
  { value: 'plain', label: 'Без цвета' },
  { value: 'yellow', label: 'Жёлтый' },
  { value: 'green', label: 'Зелёный' },
  { value: 'blue', label: 'Голубой' },
  { value: 'pink', label: 'Розовый' },
]

export function NoteEditor({ open, note, onClose }: { open: boolean; note: Note | null; onClose: () => void }) {
  const store = useStore()
  const [text, setText] = useState(note?.text ?? '')
  const [tint, setTint] = useState<NoteTint>(note?.tint ?? 'plain')
  const [pinned, setPinned] = useState(note?.pinned ?? true)

  const canSave = text.trim().length > 0

  const save = () => {
    if (!canSave) return
    const data = { text: text.trim(), tint, pinned }
    if (note) void store.updateNote(note.id, data)
    else void store.addNote(data)
    onClose()
  }

  const remove = () => {
    if (note) void store.deleteNote(note.id)
    onClose()
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={note ? 'Заметка' : 'Новая заметка'}
      left={
        <button type="button" className="text-btn" onClick={onClose}>
          Отмена
        </button>
      }
      right={
        <button type="button" className="text-btn bold" disabled={!canSave} onClick={save}>
          Готово
        </button>
      }
    >
      <div className="form-group" style={{ background: `var(--tint-${tint})` }}>
        <textarea
          className="field field-note"
          placeholder="Первая строка станет заголовком"
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus={!note}
        />
      </div>

      <div className="form-group">
        <div className="tints" role="group" aria-label="Цвет заметки">
          {TINTS.map((t) => (
            <button
              key={t.value}
              type="button"
              className="tint"
              data-tint={t.value}
              aria-pressed={tint === t.value}
              aria-label={t.label}
              onClick={() => setTint(t.value)}
            />
          ))}
        </div>
        <div className="form-row">
          <span className="icon" style={{ background: 'var(--accent)' }}>
            <IconPin />
          </span>
          <span className="label">Показывать на каждом дне</span>
          <Switch checked={pinned} onChange={setPinned} label="Закрепить заметку" />
        </div>
      </div>
      <p className="form-caption">Закреплённые заметки всегда видны на экране «День» — для любой даты.</p>

      {note && (
        <button type="button" className="danger-btn pressable" onClick={remove}>
          Удалить заметку
        </button>
      )}
    </Sheet>
  )
}
