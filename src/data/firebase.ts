import { initializeApp } from 'firebase/app'
import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  indexedDBLocalPersistence,
  initializeAuth,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth'
import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  initializeFirestore,
  onSnapshot,
  persistentLocalCache,
  persistentMultipleTabManager,
  query,
  updateDoc,
  where,
  type Firestore,
} from 'firebase/firestore'
import type { AppUser, Note, Store, Task } from './types'
import { sortNotes, sortTasks } from './sort'
import { toast } from '../components/toast'

const onWriteError = () => toast('Не удалось сохранить изменения')

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export const firebaseEnabled = Boolean(config.apiKey && config.projectId && config.appId)

const app = firebaseEnabled ? initializeApp(config) : null

// Без popup/redirect-резолвера: в standalone-режиме iOS вход по email/паролю самый надёжный.
const auth = app ? initializeAuth(app, { persistence: [indexedDBLocalPersistence, browserLocalPersistence] }) : null

// Офлайн-кэш в IndexedDB: приложение открывается мгновенно и работает без сети.
const db: Firestore | null = app
  ? initializeFirestore(app, { localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }) })
  : null

export const authApi = {
  onChange(cb: (user: AppUser | null) => void) {
    if (!auth) return () => {}
    return onAuthStateChanged(auth, (u) => cb(u ? { uid: u.uid, email: u.email } : null))
  },
  signIn: (email: string, password: string) => signInWithEmailAndPassword(auth!, email, password).then(() => {}),
  signUp: (email: string, password: string) => createUserWithEmailAndPassword(auth!, email, password).then(() => {}),
  resetPassword: (email: string) => sendPasswordResetEmail(auth!, email),
  signOut: () => signOut(auth!),
}

export function createFirestoreStore(uid: string): Store {
  const notesCol = collection(db!, 'users', uid, 'notes')
  const tasksCol = collection(db!, 'users', uid, 'tasks')

  return {
    watchNotes(onData, onError) {
      return onSnapshot(
        notesCol,
        (snap) => onData(sortNotes(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as Note))),
        onError,
      )
    },
    watchTasks(from, to, onData, onError) {
      const q = query(tasksCol, where('date', '>=', from), where('date', '<=', to))
      return onSnapshot(
        q,
        (snap) => onData(sortTasks(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as Task))),
        onError,
      )
    },
    // Записи не ждут ответа сервера: локальный кэш сразу отдаёт изменения в onSnapshot.
    async addNote(input) {
      const now = Date.now()
      addDoc(notesCol, { ...input, createdAt: now, updatedAt: now }).catch(onWriteError)
    },
    async updateNote(id, patch) {
      updateDoc(doc(notesCol, id), { ...patch, updatedAt: Date.now() }).catch(onWriteError)
    },
    async deleteNote(id) {
      deleteDoc(doc(notesCol, id)).catch(onWriteError)
    },
    async addTask(input) {
      addDoc(tasksCol, { ...input, done: false, createdAt: Date.now() }).catch(onWriteError)
    },
    async updateTask(id, patch) {
      updateDoc(doc(tasksCol, id), patch).catch(onWriteError)
    },
    async deleteTask(id) {
      deleteDoc(doc(tasksCol, id)).catch(onWriteError)
    },
  }
}
