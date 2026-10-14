import { createContext, useContext, useEffect, useState } from 'react'
import type { Note, Store, Task } from './types'

const StoreContext = createContext<Store | null>(null)

export const StoreProvider = StoreContext.Provider

export function useStore(): Store {
  const store = useContext(StoreContext)
  if (!store) throw new Error('StoreProvider is missing')
  return store
}

interface Live<T> {
  data: T
  loading: boolean
  error: Error | null
}

function useLive<T>(
  subscribe: (store: Store, onData: (d: T) => void, onError: (e: Error) => void) => () => void,
  initial: T,
  deps: unknown[],
): Live<T> {
  const store = useStore()
  const [state, setState] = useState<Live<T>>({ data: initial, loading: true, error: null })

  useEffect(() => {
    // Старые данные остаются на экране, пока не пришли новые — интерфейс не мигает.
    setState((s) => ({ ...s, loading: true }))
    return subscribe(
      store,
      (data) => setState({ data, loading: false, error: null }),
      (error) => setState((s) => ({ ...s, loading: false, error })),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store, ...deps])

  return state
}

const NO_NOTES: Note[] = []
const NO_TASKS: Task[] = []

export const useNotes = () => useLive((s, ok, err) => s.watchNotes(ok, err), NO_NOTES, [])

export const useTasks = (from: string, to: string) =>
  useLive((s, ok, err) => s.watchTasks(from, to, ok, err), NO_TASKS, [from, to])
