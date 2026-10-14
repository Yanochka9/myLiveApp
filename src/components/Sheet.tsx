import { useEffect, useRef, useState, type ReactNode, type PointerEvent } from 'react'
import { createPortal } from 'react-dom'

interface Props {
  open: boolean
  onClose: () => void
  title: string
  left?: ReactNode
  right?: ReactNode
  children: ReactNode
}

const CLOSE_MS = 420

/** Нижняя шторка как в iOS: выезжает снизу, закрывается свайпом вниз за шапку. */
export function Sheet({ open, onClose, title, left, right, children }: Props) {
  const [mounted, setMounted] = useState(open)
  const [visible, setVisible] = useState(false)
  const [drag, setDrag] = useState<number | null>(null)
  const startY = useRef(0)

  useEffect(() => {
    if (open) {
      setMounted(true)
      // Два кадра: сначала элемент в DOM в закрытом положении, потом — переход.
      const id = requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
      return () => cancelAnimationFrame(id)
    }
    setVisible(false)
    const t = setTimeout(() => setMounted(false), CLOSE_MS)
    return () => clearTimeout(t)
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!mounted) return null

  const onPointerDown = (e: PointerEvent) => {
    if ((e.target as HTMLElement).closest('button')) return
    startY.current = e.clientY
    setDrag(0)
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: PointerEvent) => {
    if (drag === null) return
    setDrag(Math.max(0, e.clientY - startY.current))
  }
  const onPointerUp = () => {
    if (drag !== null && drag > 90) onClose()
    setDrag(null)
  }

  const dragHandlers = { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp }

  return createPortal(
    <>
      <div className="sheet-backdrop" data-open={visible} onClick={onClose} />
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        data-open={visible}
        data-dragging={drag !== null}
        style={drag ? ({ '--drag': `${drag}px` } as React.CSSProperties) : undefined}
      >
        <div className="sheet-grabber" {...dragHandlers}>
          <i />
        </div>
        <div className="sheet-head" {...dragHandlers}>
          <div>{left}</div>
          <h3>{title}</h3>
          <div>{right}</div>
        </div>
        <div className="sheet-body">{children}</div>
      </div>
    </>,
    document.body,
  )
}
