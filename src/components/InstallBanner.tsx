import { useState } from 'react'
import { isIOS, isStandalone } from '../lib/viewport'
import { IconClose, IconPlus, IconShare } from './Icons'

const KEY = 'den.installBanner.hidden'

function initiallyVisible() {
  try {
    return isIOS() && !isStandalone() && localStorage.getItem(KEY) !== '1'
  } catch {
    return false
  }
}

export function InstallBanner() {
  const [visible, setVisible] = useState(initiallyVisible)
  if (!visible) return null
  const hide = () => {
    setVisible(false)
    try {
      localStorage.setItem(KEY, '1')
    } catch {
      /* не критично */
    }
  }
  return (
    <div className="card banner fade-in">
      <span className="icon">
        <IconPlus />
      </span>
      <div>
        Установите на экран «Домой»
        <p>
          Нажмите <IconShare className="inline-icon" /> «Поделиться» → «На экран „Домой“» — откроется как приложение.
        </p>
      </div>
      <button type="button" className="close" aria-label="Скрыть" onClick={hide}>
        <IconClose />
      </button>
    </div>
  )
}
