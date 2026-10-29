import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { confirmChat, createChat, decideApproval, getChat, getChatPresets, hasToken, sendChatMessage } from '../api/client.js'
import {
  DEFAULT_DISCLOSURE, MODES, busyLine, composerBlock, decisionKind, decisionWord, pendingApproval, pollDelay, ruleLabel,
} from '../lib/chat.js'

// **bold** in a model's reply, as React text (never as HTML).
function Inline({ text }) {
  return text.split('**').map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : <Fragment key={i}>{part}</Fragment>))
}

function Chip({ a }) {
  const kind = decisionKind(a.decision)
  return (
    <details className={`chip chip--${kind}`}>
      <summary>
        <span className="chip-word">{decisionWord(a.decision)}</span>
        <span className="chip-label">{a.label}</span>
        <span className="chip-preview">{a.args_preview}</span>
      </summary>
      <div className="chip-body">
        {a.reason && <p className="chip-reason">{a.reason}</p>}
        {a.rules?.length > 0 && <p className="chip-rules">{a.rules.map(ruleLabel).join(' · ')}</p>}
      </div>
    </details>
  )
}

function Message({ m, working }) {
  if (m.role === 'user') return <div className="msg msg-user"><p><Inline text={m.text} /></p></div>
  const empty = !m.text && working
  return (
    <div className={`msg msg-${m.role}`}>
      {m.text ? <p className="msg-text"><Inline text={m.text} /></p> : empty && <p className="msg-text muted">Working...</p>}
      {m.actions?.length > 0 && <div className="chips">{m.actions.map((a) => <Chip key={a.action_id} a={a} />)}</div>}
    </div>
  )
}

function SlipCard({ slip, busy, onConfirm }) {
  return (
    <div className="s-panel slip-card chat-slip">
      <p className="s-label">The permission slip</p>
      <p className="slip-objective">{slip.objective}</p>
      <dl className="slip-facts">
        <dt>May use</dt><dd>{slip.allowed_tools.map((t) => t.replace(/_/g, ' ')).join(', ')}</dd>
        <dt>May write to</dt><dd>{slip.allowed_destinations.join(', ') || 'nobody'}</dd>
        <dt>Message limit</dt><dd>{slip.max_messages}</dd>
      </dl>
      <p className="muted">Nothing runs until the officer confirms it.</p>
      <div><button type="button" className="s-btn s-btn--primary" onClick={onConfirm} disabled={busy}>Confirm as officer</button></div>
    </div>
  )
}

function ApprovalCard({ a, busy, onDecide }) {
  return (
    <div className="s-panel approval-card" role="alert">
      <p className="chip-word approval-word">NEEDS APPROVAL</p>
      <p className="approval-what">{a.label}</p>
      <code className="approval-args">{a.args_preview}</code>
      <p className="muted">{a.reason}</p>
      <div className="approval-buttons">
        <button type="button" className="s-btn s-btn--primary" onClick={() => onDecide('approve')} disabled={busy}>Approve</button>
        <button type="button" className="s-btn s-btn--ghost" onClick={() => onDecide('deny')} disabled={busy}>Deny</button>
      </div>
    </div>
  )
}

export default function Chat() {
  const [params, setParams] = useSearchParams()
  const [presets, setPresets] = useState({ status: 'loading', list: [], error: '' })
  const [mode, setMode] = useState('auto')
  const [selected, setSelected] = useState(null)
  const [view, setView] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const dockRef = useRef(null)
  const endRef = useRef(null)

  useEffect(() => {
    let live = true
    getChatPresets()
      .then((list) => { if (live) setPresets({ status: 'ready', list, error: '' }) })
      .catch((e) => { if (live) setPresets({ status: 'error', list: [], error: e.message }) })
    return () => { live = false }
  }, [])

  // Ask for the chat's view again after a pause that depends on what it is doing. Each answer schedules the next ask.
  useEffect(() => {
    if (!view) return undefined
    const delay = pollDelay(view.status)
    if (delay == null) return undefined
    let live = true
    const t = setTimeout(async () => {
      try {
        const v = await getChat(view.chat_id)
        if (live) { setError(''); setView(v) }
      } catch (e) {
        if (live) { setError(e.message); setView((old) => ({ ...old })) } // try again later
      }
    }, delay)
    return () => { live = false; clearTimeout(t) }
  }, [view])

  const messageCount = view?.messages?.length ?? 0
  const actionCount = (view?.messages ?? []).reduce((n, m) => n + (m.actions?.length ?? 0), 0)
  // The composer is pinned to the bottom of the screen, so "scroll to the end" must stop above it: the end marker keeps a
  // margin as tall as the composer, and everything the officer needs to act on (an approval card, a note) stays clear of it.
  useEffect(() => {
    const end = endRef.current
    if (!end || !view) return
    end.style.scrollMarginBottom = `${(dockRef.current?.offsetHeight ?? 0) + 16}px`
    end.scrollIntoView({ block: 'nearest' })
  }, [messageCount, actionCount, view?.status])

  const run = useCallback(async (fn) => {
    setBusy(true)
    setError('')
    try { await fn() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }, [])

  // ?chat=<id> keeps a conversation across a reload and lets a link open it.
  const chatParam = params.get('chat')
  useEffect(() => {
    if (!chatParam) return
    getChat(chatParam)
      .then((v) => { setView(v); setSelected(v.preset) })
      .catch((e) => { setError(e.message); setParams({}, { replace: true }) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const start = (id) => run(async () => {
    const v = await createChat(id, mode)
    setView(v)
    setSelected(id)
    setDraft('')
    setParams({ chat: v.chat_id }, { replace: true })
  })
  const preset = presets.list.find((p) => p.id === selected)
  const confirm = () => run(async () => {
    setView(await confirmChat(view.chat_id))
    if (preset) setDraft(preset.prompt) // the suggested task is ready in the composer; the officer can edit it
  })
  const send = () => run(async () => {
    const text = draft.trim()
    if (!text) return
    await sendChatMessage(view.chat_id, text)
    setDraft('')
    setView(await getChat(view.chat_id))
  })
  const decide = (decision) => run(async () => {
    await decideApproval(pendingApproval(view).approval_id, decision)
    setView(await getChat(view.chat_id))
  })
  const newChat = () => { setView(null); setSelected(null); setDraft(''); setError(''); setParams({}, { replace: true }) }

  const block = composerBlock(view)
  const approval = pendingApproval(view)
  const status = view?.status
  const lastIndex = (view?.messages?.length ?? 0) - 1

  return (
    <main className="chat">
      <aside className="chat-side" aria-label="Tasks">
        <p className="s-label">Pick a task</p>
        {presets.status === 'loading' && <p className="muted" role="status">Loading...</p>}
        {presets.status === 'error' && (
          <p className="muted" role="status">{hasToken() ? presets.error : 'Chat is an officer action. Open this page from the link that `python -m sentinel up` prints; it carries the officer token.'}</p>
        )}
        <ul className="preset-list">
          {presets.list.map((p) => (
            <li key={p.id}>
              <button type="button" className={`preset${selected === p.id ? ' is-on' : ''}`} onClick={() => start(p.id)} disabled={busy} aria-pressed={selected === p.id}>
                <span className="preset-title">{p.title}</span>
                <span className="preset-desc">{p.description}</span>
              </button>
            </li>
          ))}
        </ul>
        <label className="mode">
          <span className="s-label">Model</span>
          <select value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Where the model's replies come from">
            {MODES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
        </label>
      </aside>

      <section className="chat-main" aria-label="Chat">
        <header className="chat-head">
          <h1 className="chat-title">Sentinel Chat</h1>
          {view && <button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={newChat}>New chat</button>}
        </header>

        {!view && (
          <div className="chat-empty">
            <p className="chat-empty-title">Pick a task, then watch every step get checked.</p>
            <p className="muted">A model works for you. Every tool it calls goes through Sentinel first, and you see each decision as it is made.</p>
          </div>
        )}

        {view && status === 'awaiting_confirmation' && <SlipCard slip={view.slip} busy={busy} onConfirm={confirm} />}

        {view && status !== 'awaiting_confirmation' && (
          <div className="thread" role="log" aria-live="polite" aria-label="Conversation">
            {view.messages.map((m, i) => <Message key={m.id} m={m} working={i === lastIndex && (status === 'thinking' || status === 'model_busy')} />)}
          </div>
        )}

        {approval && <ApprovalCard a={approval} busy={busy} onDecide={decide} />}
        {busyLine(view) && <p className="chat-note" role="status">{busyLine(view)}</p>}
        {status === 'quarantined' && (
          <p className="chat-note chat-note--quarantined" role="status">
            <strong>QUARANTINED.</strong> This session was frozen and its permission slip revoked. <button type="button" className="linklike" onClick={newChat}>Start a new chat</button>
          </p>
        )}
        {status === 'ended' && <p className="chat-note" role="status">The permission slip has expired. <button type="button" className="linklike" onClick={newChat}>Start a new chat</button></p>}
        {error && <p className="conn-error" role="alert">{error}</p>}
        

        <div ref={endRef} aria-hidden="true" />

        <div className="composer-dock" ref={dockRef}>
          <div className="composer">
            <sentinel-mascot state={view?.mascot?.state ?? 'sleeping'} message="" size="64" />
            <div className="composer-body">
              <p className="mascot-line" aria-live="polite">{view?.mascot?.message || (view ? '' : 'Asleep until a task is confirmed.')}</p>
              <div className="composer-row">
                <textarea
                  className="composer-input" rows={2} value={draft} onChange={(e) => setDraft(e.target.value)}
                  disabled={Boolean(block)} aria-label="Message" aria-describedby="composer-why"
                  placeholder={block ? '' : 'Type a message, or send the suggested task'}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !block && draft.trim()) { e.preventDefault(); send() } }}
                />
                <button type="button" className={block ? 's-btn s-btn--ghost' : 's-btn s-btn--primary'} onClick={send} disabled={Boolean(block) || busy || !draft.trim()}>Send</button>
              </div>
              <p id="composer-why" className="composer-why">{status === 'thinking' || status === 'model_busy' ? '' : block}</p>
            </div>
          </div>
          <p className="disclosure">{view?.disclosure ?? DEFAULT_DISCLOSURE}</p>
        </div>
      </section>
    </main>
  )
}
