import { useCallback, useEffect, useRef, useState } from 'react'
import { getRun } from '../api.js'

// Polls GET /runs/{id} while the run is live or an approval is pending. Keeps the last good view when a poll fails.
export function useRun(runId) {
  const [view, setView] = useState(null)
  const [lost, setLost] = useState(false)
  const timer = useRef(null)
  const current = useRef(runId)
  current.current = runId

  const refresh = useCallback(async () => {
    const id = current.current
    if (!id) return null
    try {
      const v = await getRun(id)
      if (current.current !== id) return null
      setView(v)
      setLost(false)
      return v
    } catch {
      setLost(true)
      return null
    }
  }, [])

  useEffect(() => {
    setView(null)
    setLost(false)
    if (!runId) return undefined
    let stopped = false
    const tick = async () => {
      const v = await refresh()
      if (stopped) return
      const done = v && (v.status === 'finished' || v.status === 'cancelled')
      timer.current = setTimeout(tick, done ? 2500 : 700) // a slow heartbeat after the end keeps late approvals honest
    }
    tick()
    return () => {
      stopped = true
      clearTimeout(timer.current)
    }
  }, [runId, refresh])

  return { view, lost, refresh }
}
