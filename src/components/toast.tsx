import { useEffect, useState } from 'react'

const listeners = new Set<(msg: string) => void>()

export function toast(message: string) {
  listeners.forEach((l) => l(message))
}

export function Toaster() {
  const [msg, setMsg] = useState('')
  const [show, setShow] = useState(false)

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    const on = (m: string) => {
      setMsg(m)
      setShow(true)
      clearTimeout(timer)
      timer = setTimeout(() => setShow(false), 2600)
    }
    listeners.add(on)
    return () => {
      listeners.delete(on)
      clearTimeout(timer)
    }
  }, [])

  return (
    <div className="toast" data-show={show} role="status" aria-live="polite">
      {msg}
    </div>
  )
}
