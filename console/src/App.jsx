import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cancelRun, confirmRun, createRun, getRecordings, initAuth, listRuns, tamperAudit, verifyAudit,
} from './api.js'
import { mascotFor, pickDefaultRecording, presenterNext } from './lib/derive.js'
import { useRun } from './hooks/useRun.js'
import { AuditBar, TopBar } from './chrome/Chrome.jsx'
import { SlipScreen, StartScreen } from './screens/Screens.jsx'
import Stage from './stage/Stage.jsx'
import Verdict, { verdictFor } from './verdict/Verdict.jsx'

const auth = initAuth()

// The guided demo. Poisoned uses a real recorded model run when one exists, otherwise the scripted agent.
const PLAYLIST = ['poisoned', 'freeze', 'hardened', 'bank_change']

export default function App() {
  const [runId, setRunId] = useState(auth.run)
  const [plIndex, setPlIndex] = useState(0)
  const [verdictOpen, setVerdictOpen] = useState(auth.verdict) // `#verdict=1` opens it directly (used for screenshots)
  const [receipts, setReceipts] = useState(false)
  const [verify, setVerify] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const { view, lost, refresh } = useRun(runId)

  const guard = useCallback(async (fn) => {
    setBusy(true)
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError(e.message)
      return null
    } finally {
      setBusy(false)
    }
  }, [])

  // Re-attach to the active run after a reload; learn whether the tamper demo is enabled.
  useEffect(() => {
    if (!runId) listRuns().then((j) => j.active && setRunId(j.active)).catch(() => {})
    verifyAudit().then(setVerify).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const create = useCallback((scenario, source, recordingId) => guard(async () => {
    const v = await createRun(scenario, source, recordingId)
    setVerdictOpen(false)
    setReceipts(false)
    setRunId(v.run_id)
  }), [guard])

  const createFromPlaylist = useCallback(() => guard(async () => {
    const scenario = PLAYLIST[plIndex]
    let source = 'scripted'
    let recordingId
    if (scenario === 'poisoned') {
      const rec = pickDefaultRecording(await getRecordings().catch(() => []), 'poisoned')
      if (rec) { source = 'replay'; recordingId = rec.recording_id }
    }
    const v = await createRun(scenario, source, recordingId)
    setPlIndex(plIndex + 1)
    setVerdictOpen(false)
    setReceipts(false)
    setRunId(v.run_id)
  }), [guard, plIndex])

  const confirm = useCallback(() => guard(async () => { await confirmRun(runId); await refresh() }), [guard, runId, refresh])

  const advance = useCallback(async () => {
    setVerdictOpen(false)
    if (plIndex < PLAYLIST.length) await createFromPlaylist()
    else { setRunId(null); setReceipts(true) }
  }, [plIndex, createFromPlaylist])

  const [verifiedFlash, setVerifiedFlash] = useState(false) // the mascot shows "verified" for three seconds
  const doVerify = useCallback(() => guard(async () => {
    const v = await verifyAudit()
    setVerify(v)
    if (v.ok) {
      setVerifiedFlash(true)
      setTimeout(() => setVerifiedFlash(false), 3000)
    }
  }), [guard])
  const doTamper = useCallback(() => guard(async () => { await tamperAudit(); setVerify(await verifyAudit()) }), [guard])

  const screen = !runId ? 'start' : view?.status === 'awaiting_confirmation' ? 'slip' : view ? 'stage' : 'loading'
  const hasVerdict = Boolean(view && verdictFor(view))

  // Presenter keys, via refs so the listener is registered once and always sees current state.
  const live = useRef({})
  live.current = { screen, view, verdictOpen, hasVerdict, plIndex, advance, createFromPlaylist, confirm, doVerify, doTamper, verify, receipts }
  useEffect(() => {
    const onKey = async (e) => {
      if (['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(e.target.tagName) && e.key === 'Enter') return
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return
      const s = live.current
      const k = e.key.toLowerCase()
      if (k === 'v') s.doVerify()
      else if (k === 't' && (s.receipts || s.screen === 'start') && s.verify?.tamper_enabled) s.doTamper()
      else if (k === 'n') {
        if (s.view && s.view.status !== 'finished') await cancelRun(s.view.run_id).catch(() => {})
        s.advance()
      } else if (e.key === 'Enter') {
        const a = presenterNext({
          screen: s.screen, runStatus: s.view?.status, verdictOpen: s.verdictOpen, hasVerdict: s.hasVerdict,
          playlistIndex: s.plIndex, playlistLength: PLAYLIST.length,
        })
        if (a === 'create') s.createFromPlaylist()
        else if (a === 'confirm') s.confirm()
        else if (a === 'open-verdict') setVerdictOpen(true)
        else if (a === 'close-and-next' || a === 'next') s.advance()
        else if (a === 'done') setReceipts(true)
      }
    }
    // A clicked button keeps focus and would swallow the next Enter; let go of it.
    const onClick = (e) => e.target.closest?.('button')?.blur()
    window.addEventListener('keydown', onKey)
    window.addEventListener('click', onClick)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('click', onClick)
    }
  }, [])

  return (
    <div className="app">
      <TopBar view={view} lost={lost}
        mascot={verifiedFlash && verify?.ok ? { state: 'verified', message: 'Audit log intact.' } : mascotFor(view, verify)} />
      <main className="main">
        {screen === 'start' && !receipts ? (
          <StartScreen onCreate={create} error={error} busy={busy} playlist={PLAYLIST} />
        ) : null}
        {screen === 'start' && receipts ? (
          <div className="screen">
            <h1 className="screen-title">The receipts</h1>
            <p className="lede">Every decision above was written to a signed, hash-chained log before anything was forwarded.
              Verify it, change one record, and verify again.</p>
          </div>
        ) : null}
        {screen === 'slip' ? <SlipScreen view={view} onConfirm={confirm} busy={busy} error={error} /> : null}
        {screen === 'stage' ? <Stage view={view} refresh={refresh} /> : null}
        {screen === 'loading' ? <div className="screen"><div className="hint">Loading the run…</div></div> : null}
        {error && screen === 'stage' ? <div className="error-text">{error}</div> : null}
        {verdictOpen && view ? <Verdict view={view} onClose={advance} /> : null}
      </main>
      {screen === 'stage' && view?.status === 'finished' && !verdictOpen ? (
        <div className="nextbar">
          <button className="btn" onClick={() => { setRunId(null); setReceipts(false) }}>Back to scenarios</button>
          {hasVerdict ? <button className="btn btn-primary" onClick={() => setVerdictOpen(true)}>Why was it denied? (Enter)</button> : null}
          <button className="btn" onClick={advance}>{plIndex < PLAYLIST.length ? 'Next in the guided demo (N)' : 'Show the receipts (N)'}</button>
        </div>
      ) : null}
      <AuditBar verify={verify} onVerify={doVerify} onTamper={doTamper} busy={busy} />
    </div>
  )
}
