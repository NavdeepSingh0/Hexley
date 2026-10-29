// Reads /evidence.json once per page view. If the file cannot be read, the caller says so and shows no number: there is
// never a fallback typed into a page. Entries without their n, interval, source or caveat are dropped (lib/evidence.js).
import { useEffect, useState } from 'react'
import { groupEvidence } from './evidence.js'

export function useEvidence() {
  const [state, setState] = useState({ status: 'loading', groups: [] })
  useEffect(() => {
    let live = true
    fetch('/evidence.json')
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
      .then((items) => { if (live) setState({ status: 'ready', ...groupEvidence(items) }) })
      .catch(() => { if (live) setState({ status: 'error', groups: [] }) })
    return () => { live = false }
  }, [])
  return state
}
