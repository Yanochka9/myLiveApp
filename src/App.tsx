import { useEffect, useMemo, useState } from 'react'
import { authApi, createFirestoreStore, firebaseEnabled } from './data/firebase'
import { localStore } from './data/local'
import { StoreProvider } from './data/StoreContext'
import type { AppUser } from './data/types'
import { todayKey } from './lib/date'
import { EditorsProvider } from './components/Editors'
import { TabBar, type Tab } from './components/TabBar'
import { Spinner } from './components/Spinner'
import { Toaster } from './components/toast'
import { AuthScreen } from './screens/AuthScreen'
import { DayScreen } from './screens/DayScreen'
import { CalendarScreen } from './screens/CalendarScreen'
import { NotesScreen } from './screens/NotesScreen'
import { ProfileScreen } from './screens/ProfileScreen'

const DEMO_USER: AppUser = { uid: 'demo', email: null }

export function App() {
  // undefined — Firebase ещё проверяет сессию
  const [user, setUser] = useState<AppUser | null | undefined>(firebaseEnabled ? undefined : DEMO_USER)

  useEffect(() => (firebaseEnabled ? authApi.onChange(setUser) : undefined), [])

  if (user === undefined)
    return (
      <div className="splash">
        <Spinner large />
      </div>
    )

  return (
    <>
      {user ? <Planner key={user.uid} user={user} /> : <AuthScreen />}
      <Toaster />
    </>
  )
}

function Planner({ user }: { user: AppUser }) {
  const store = useMemo(() => (firebaseEnabled ? createFirestoreStore(user.uid) : localStore), [user.uid])
  const [tab, setTab] = useState<Tab>('day')
  const [date, setDate] = useState(todayKey)

  // Вернулись в приложение на следующий день — показываем новый «сегодня».
  useEffect(() => {
    let last = todayKey()
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      const now = todayKey()
      if (now !== last) {
        setDate((d) => (d === last ? now : d))
        last = now
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [])

  return (
    <StoreProvider value={store}>
      <EditorsProvider>
        {/* Экраны остаются смонтированными: при переключении вкладок не теряется прокрутка и нет мигания */}
        <div className="app" hidden={tab !== 'day'}>
          <DayScreen date={date} onDateChange={setDate} onOpenNotes={() => setTab('notes')} />
        </div>
        <div className="app" hidden={tab !== 'calendar'}>
          <CalendarScreen date={date} onDateChange={setDate} onOpenDay={() => setTab('day')} />
        </div>
        <div className="app" hidden={tab !== 'notes'}>
          <NotesScreen />
        </div>
        <div className="app" hidden={tab !== 'profile'}>
          <ProfileScreen user={user} demo={!firebaseEnabled} onSignOut={authApi.signOut} />
        </div>
        <TabBar tab={tab} onChange={setTab} />
      </EditorsProvider>
    </StoreProvider>
  )
}
