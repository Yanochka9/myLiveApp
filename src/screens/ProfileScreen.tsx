import { useState } from 'react'
import type { AppUser } from '../data/types'
import { Screen } from '../components/Screen'
import { Spinner } from '../components/Spinner'
import { IconCloud, IconPerson, IconShare } from '../components/Icons'
import { isStandalone } from '../lib/viewport'

interface Props {
  user: AppUser
  demo: boolean
  onSignOut: () => Promise<void>
}

export function ProfileScreen({ user, demo, onSignOut }: Props) {
  const [busy, setBusy] = useState(false)
  const installed = isStandalone()

  return (
    <Screen title="Профиль">
      <div className="form-group card">
        <div className="form-row" style={{ minHeight: 64 }}>
          <span className="icon" style={{ background: 'var(--label-3)', width: 40, height: 40, borderRadius: '50%' }}>
            <IconPerson />
          </span>
          <div className="label">
            <div style={{ fontWeight: 600 }}>{demo ? 'Демо-режим' : user.email}</div>
            <div style={{ fontSize: 13, color: 'var(--label-2)' }}>
              {demo ? 'Данные хранятся только на этом устройстве' : 'Синхронизация через Firebase'}
            </div>
          </div>
        </div>
        <div className="form-row">
          <span className="icon" style={{ background: demo ? 'var(--life)' : 'var(--accent)' }}>
            <IconCloud />
          </span>
          <span className="label">Облако</span>
          <span style={{ color: 'var(--label-2)' }}>{demo ? 'Не подключено' : 'Подключено'}</span>
        </div>
      </div>
      {demo && (
        <p className="form-caption">
          Чтобы данные синхронизировались между устройствами, задайте переменные VITE_FIREBASE_* в настройках Netlify (см. README).
        </p>
      )}

      {!installed && (
        <div className="form-group card">
          <div className="form-row" style={{ padding: '12px 16px', alignItems: 'flex-start' }}>
            <span className="icon" style={{ background: 'var(--accent)' }}>
              <IconShare />
            </span>
            <div className="label" style={{ fontSize: 15 }}>
              Как установить на iPhone
              <div style={{ fontSize: 13, color: 'var(--label-2)', marginTop: 4, lineHeight: '18px' }}>
                Откройте сайт в Safari → «Поделиться» → «На экран „Домой“» → «Добавить». Приложение откроется на весь экран, без адресной строки.
              </div>
            </div>
          </div>
        </div>
      )}

      {!demo && (
        <button
          type="button"
          className="danger-btn pressable card"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await onSignOut()
            } finally {
              setBusy(false)
            }
          }}
        >
          {busy ? <Spinner /> : 'Выйти'}
        </button>
      )}
    </Screen>
  )
}
