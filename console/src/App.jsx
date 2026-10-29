import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cancelRun, confirmRun, createRun, getRecordings, initAuth, listRuns, restoreAudit, tamperAudit, verifyAudit,
} from './api.js'
import { mascotFor, pickDefaultRecording, presenterNext } from './lib/derive.js'
import { useRun } from './hooks/useRun.js'
import { AuditBar, AuditPanel, PresenterHelp, TaskLine, TopBar } from './chrome/Chrome.jsx'
import { SlipScreen, StartScreen } from './screens/Screens.jsx'
import ApprovalModal from './approval/ApprovalModal.jsx'
import Stage from './stage/Stage.jsx'
import StepsDrawer from './stage/StepsDrawer.jsx'
import Drawer, { targetFor, verdictFor } from './verdict/Verdict.jsx'

const auth = initAuth()

// The guided demo. Poisoned uses a real recorded model run when one exists, otherwise the scripted agent.
const PLAYLIST = ['poisoned', 'freeze', 'hardened', 'bank_change']

export default function App() {
  const [runId, setRunId] = useState(auth.run)
  const [plIndex, setPlIndex] = useState(0)
  // The right-hand drawer: { laneId } lists that lane's steps; { laneId, index } explains one denied step ("from: 'steps'" if
  // it was reached from the list, so it can go back there).
  const [drawer, setDrawer] = useState(null)
  const [wantVerdict, setWantVerdict] = useState(auth.verdict) // `#verdict=1` opens the first verdict directly (screenshots)
  const [helpOpen, setHelpOpen] = useState(false)
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
    setDrawer(null)
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
    setDrawer(null)
    setReceipts(false)
    setRunId(v.run_id)
  }), [guard, plIndex])

  const confirm = useCallback(() => guard(async () => { await confirmRun(runId); await refresh() }), [guard, runId, refresh])

  const advance = useCallback(async () => {
    setDrawer(null)
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
  // Put back the record the demo changed, so the log reads INTACT again and the demo can go on (or be rehearsed again).
  const doRestore = useCallback(() => guard(async () => {
    await restoreAudit()
    const v = await verifyAudit()
    setVerify(v)
    if (v.ok) {
      setVerifiedFlash(true)
      setTimeout(() => setVerifiedFlash(false), 3000)
    }
  }), [guard])

  const screen = !runId ? 'start' : view?.status === 'awaiting_confirmation' ? 'slip' : view ? 'stage' : 'loading'
  const first = view ? verdictFor(view) : null
  const hasVerdict = Boolean(first)
  const openVerdict = useCallback(() => {
    const v = view && verdictFor(view)
    if (v) setDrawer({ laneId: v.lane.lane_id, index: v.index })
  }, [view])
  useEffect(() => {
    if (wantVerdict && hasVerdict) {
      openVerdict()
      setWantVerdict(false)
    }
  }, [wantVerdict, hasVerdict, openVerdict])
  const target = view && drawer && drawer.index != null ? targetFor(view, drawer.laneId, drawer.index) : null
  const stepsLane = view && drawer && drawer.index == null ? drawer.laneId : null
  const pending = view ? view.lanes.flatMap((l) => l.approvals || []).find((a) => a.status === 'pending') : null

  // Presenter keys, via refs so the listener is registered once and always sees current state.
  const live = useRef({})
  live.current = {
    screen, view, verdictOpen: Boolean(target), stepsOpen: Boolean(stepsLane), hasVerdict, plIndex, advance, createFromPlaylist, confirm, doVerify, doTamper, doRestore, verify, receipts,
    openVerdict,
  }
  useEffect(() => {
    const onKey = async (e) => {
      if (['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(e.target.tagName) && e.key === 'Enter') return
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const s = live.current
      const k = e.key.toLowerCase()
      if (e.key === '?') setHelpOpen((o) => !o)
      else if (k === 'v') s.doVerify()
      else if (k === 't' && (s.receipts || s.screen === 'start') && s.verify?.tamper_enabled && !s.verify?.restorable) s.doTamper()
      else if (k === 'r' && s.verify?.restorable) s.doRestore()
      else if (k === 'n') {
        if (s.view && s.view.status !== 'finished') await cancelRun(s.view.run_id).catch(() => {})
        s.advance()
      } else if (e.key === 'Enter') {
        if (s.stepsOpen) { setDrawer(null); return } // a lane's step list is a look, not a step of the demo: Enter just closes it
        const a = presenterNext({
          screen: s.screen, runStatus: s.view?.status, verdictOpen: s.verdictOpen, hasVerdict: s.hasVerdict,
          playlistIndex: s.plIndex, playlistLength: PLAYLIST.length,
        })
        if (a === 'create') s.createFromPlaylist()
        else if (a === 'confirm') s.confirm()
        else if (a === 'open-verdict') s.openVerdict()
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

  const finished = screen === 'stage' && view?.status === 'finished' && !drawer
  return (
    <div className="app">
      <TopBar view={view} lost={lost} helpOpen={helpOpen} onHelp={() => setHelpOpen((o) => !o)}
        mascot={verifiedFlash && verify?.ok ? { state: 'verified', message: 'Audit log intact.' } : mascotFor(view, verify)} />
      {helpOpen ? <PresenterHelp onClose={() => setHelpOpen(false)} tamperEnabled={Boolean(verify?.tamper_enabled)} /> : null}
      <main className="main">
        {screen === 'start' && !receipts ? (
          <StartScreen onCreate={create} onGuided={createFromPlaylist} error={error} busy={busy} playlist={PLAYLIST} />
        ) : null}
        {screen === 'start' && receipts ? (
          <div className="screen">
            <p className="s-label">The guided demo is over</p>
            <h1 className="screen-title">The receipts</h1>
            <p className="screen-sub">Every decision was written to a signed, hash-chained log before anything was forwarded.
              Verify it, change one record, and verify again.</p>
            <AuditPanel verify={verify} onVerify={doVerify} onTamper={doTamper} onRestore={doRestore} busy={busy} />
          </div>
        ) : null}
        {screen === 'slip' ? <SlipScreen view={view} onConfirm={confirm} busy={busy} error={error} /> : null}
        {screen === 'stage' ? (
          <>
            <TaskLine view={view} />
            <Stage view={view} onSteps={(laneId) => setDrawer({ laneId })} />
          </>
        ) : null}
        {screen === 'loading' ? <div className="screen"><p className="screen-sub">Loading the run…</p></div> : null}
        {error && screen === 'stage' ? <p className="error-text">{error}</p> : null}
      </main>
      {finished ? (
        <div className="nextbar">
          <button className="s-btn s-btn--ghost" onClick={() => { setRunId(null); setReceipts(false) }}>Back to situations</button>
          {hasVerdict ? <button className="s-btn s-btn--ghost" onClick={advance}>{plIndex < PLAYLIST.length ? 'Skip ahead' : 'Show the receipts'} <span className="s-kbd">N</span></button> : null}
          {hasVerdict ? (
            <button className="s-btn s-btn--primary" onClick={openVerdict}>Why was it denied? <span className="s-kbd">Enter</span></button>
          ) : (
            <button className="s-btn s-btn--primary" onClick={advance}>{plIndex < PLAYLIST.length ? 'Next situation' : 'Show the receipts'} <span className="s-kbd">Enter</span></button>
          )}
        </div>
      ) : null}
      {stepsLane ? (
        <StepsDrawer view={view} laneId={stepsLane} onDismiss={() => setDrawer(null)}
          onWhy={(laneId, index) => setDrawer({ laneId, index, from: 'steps' })} />
      ) : null}
      {target ? (
        <Drawer target={target} onContinue={advance} onDismiss={() => setDrawer(null)}
          onBack={drawer.from === 'steps' ? () => setDrawer({ laneId: drawer.laneId }) : undefined} />
      ) : null}
      {pending ? <ApprovalModal approval={pending} onDecided={refresh} /> : null}
      <AuditBar verify={verify} onVerify={doVerify} onTamper={doTamper} onRestore={doRestore} busy={busy} />
    </div>
  )
}
