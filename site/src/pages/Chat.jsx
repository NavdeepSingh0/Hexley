import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { confirmChat, createChat, decideApproval, getChat, getChatPresets, hasToken, sendChatMessage, uploadChatDocument } from '../api/client.js'
import { Icon } from '../components/Blocks.jsx'
import Composer from '../components/chat/Composer.jsx'
import Details from '../components/chat/Details.jsx'
import Sidebar from '../components/chat/Sidebar.jsx'
import { ApprovalCard, Message, SlipCard, SlipCompact, Suggestions } from '../components/chat/parts.jsx'
import { DEFAULT_DISCLOSURE, GENERAL_PRESET, busyLine, chatTitle, composerBlock, modesFor, pendingApproval, pollDelay, statusChip, suggestions } from '../lib/chat.js'
import { loadChats, removeChat, saveChat } from '../lib/chatHistory.js'

// Hexley Chat, the way a frontier chat works: type and send. A sidebar of this browser's chats, a model picker at the top, one centred conversation.
// Sending approves the general slip, which stays one click away at the top of the conversation; every tool call opens to show its real request
// and real output. Everything it shows comes from the ChatView the gateway builds; the page decides nothing.
export default function Chat() {
  const [params, setParams] = useSearchParams()
  const chatParam = params.get('chat')
  const [presets, setPresets] = useState({ status: 'loading', list: [], error: '' })
  const [mode, setMode] = useState('auto')
  const [useConnector, setUseConnector] = useState(false)
  const [view, setView] = useState(null)
  const [attached, setAttached] = useState([]) // files picked for the next message (plan Q10)
  const [gone, setGone] = useState(false)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState(() => loadChats())
  const [navOpen, setNavOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const convo = useRef(null)
  const stick = useRef(true) // keep the newest message in view unless the reader scrolled up
  const starting = useRef(false) // the chat being opened is the one just started here, so the address must not reload it

  useEffect(() => {
    let live = true
    getChatPresets()
      .then((list) => { if (live) setPresets({ status: 'ready', list, error: '' }) })
      .catch((e) => { if (live) setPresets({ status: 'error', list: [], error: e.message }) })
    return () => { live = false }
  }, [])

  // Open the chat named in the address (a reload, a link, the sidebar); go back to the empty state when it is removed.
  useEffect(() => {
    if (starting.current) { starting.current = false; return undefined }
    setAttached([])
    if (!chatParam) { setView(null); setGone(false); setDraft(''); setDetailsOpen(false); return undefined }
    if (view?.chat_id === chatParam) return undefined
    let live = true
    setGone(false)
    getChat(chatParam)
      .then((v) => { if (live) setView(v) })
      .catch((e) => { if (live) { setView(null); if (e.status === 404) setGone(true); else setError(e.message) } })
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatParam])

  // Ask for the chat again after a pause that depends on what it is doing; each answer schedules the next ask.
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
        if (live) { setError(e.message); setView((old) => ({ ...old })) }
      }
    }, delay)
    return () => { live = false; clearTimeout(t) }
  }, [view])

  // Remember the chat in the sidebar (title, state), per viewer.
  useEffect(() => {
    if (!view) return
    const preset = presets.list.find((p) => p.id === view.preset)
    setHistory(saveChat({ id: view.chat_id, title: chatTitle(preset, view), preset: view.preset, status: view.status, ts: Date.now() }))
  }, [view?.chat_id, view?.status, view?.title, presets.list.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const messageCount = view?.messages?.length ?? 0
  const actionCount = (view?.messages ?? []).reduce((n, m) => n + (m.actions?.length ?? 0), 0)
  useEffect(() => {
    const el = convo.current
    if (el && stick.current) el.scrollTop = el.scrollHeight
  }, [messageCount, actionCount, view?.status, view?.messages?.at(-1)?.text])

  const onScroll = () => {
    const el = convo.current
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 140
  }

  const run = useCallback(async (fn) => {
    setBusy(true)
    setError('')
    try { await fn() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }, [])

  const connector = presets.list.find((p) => p.connector)
  const preset = presets.list.find((p) => p.id === view?.preset)

  // A chat starts when its first message is sent: the slip is drafted and confirmed in one step, and can be read at the top of the conversation.
  const open = async (presetId) => {
    const created = await createChat(presetId, mode)
    const v = await confirmChat(created.chat_id)
    stick.current = true
    starting.current = true
    setView(v)
    setNavOpen(false)
    setParams({ chat: v.chat_id })
    return v
  }
  const send = () => run(async () => {
    const text = draft.trim()
    if (!text) return
    stick.current = true
    const v = view ?? await open(useConnector && connector ? connector.id : GENERAL_PRESET)
    await sendChatMessage(v.chat_id, text, attached.filter((a) => a.status === 'ready').map((a) => a.name))
    setDraft('')
    setAttached([])
    setView(await getChat(v.chat_id))
  })
  const suggest = (id) => run(async () => {
    const task = presets.list.find((p) => p.id === id)
    const v = await open(id)
    await sendChatMessage(v.chat_id, task.prompt, [])
    setView(await getChat(v.chat_id))
  })
  const confirm = () => run(async () => { setView(await confirmChat(view.chat_id)) })
  // A picked PDF is uploaded at once and shown in the box; it goes with the next message.
  const attach = async (file) => {
    const temp = { name: file.name, status: 'uploading' }
    setAttached((list) => [...list.filter((a) => a.name !== file.name), temp])
    try {
      const v = view ?? await open(GENERAL_PRESET)
      const d = await uploadChatDocument(v.chat_id, file)
      setAttached((list) => [...list.filter((a) => a !== temp && a.name !== d.name), { ...d, status: 'ready' }])
    } catch (e) {
      setAttached((list) => list.map((a) => (a === temp ? { ...a, status: 'error', error: e.message } : a)))
    }
  }
  const detach = (name) => setAttached((list) => list.filter((a) => a.name !== name))
  const decide = (decision) => run(async () => {
    await decideApproval(pendingApproval(view).approval_id, decision)
    setView(await getChat(view.chat_id))
  })
  const newChat = () => { setNavOpen(false); setParams({}) }
  const openChat = (id) => { setNavOpen(false); setDetailsOpen(false); setParams({ chat: id }) }
  const forget = (id) => {
    setHistory(removeChat(id))
    if (id === chatParam) setParams({})
  }

  // Escape closes whichever panel is open.
  useEffect(() => {
    const esc = (e) => { if (e.key === 'Escape') { setDetailsOpen(false); setNavOpen(false) } }
    document.addEventListener('keydown', esc)
    return () => document.removeEventListener('keydown', esc)
  }, [])

  const block = view ? composerBlock(view) : ''
  const approval = pendingApproval(view)
  const status = view?.status
  const chip = statusChip(view)
  const working = status === 'thinking' || status === 'model_busy'
  const lastIndex = messageCount - 1
  const unreachable = presets.status === 'error' ? presets.error : ''
  const canAttach = hasToken() || view?.can_upload
  const attachHandler = canAttach && status !== 'awaiting_confirmation' && (view ? view.can_upload : hasToken()) ? attach : null
  const disclosure = view?.disclosure ?? (useConnector && connector ? 'A real GitHub connector, on the repositories this deployment names. Hexley judges every call.' : DEFAULT_DISCLOSURE)
  const empty = !view && !gone
  const box = (
    <Composer draft={draft} setDraft={setDraft} onSend={send} block={block} canType={working} busy={busy} disclosure={disclosure}
      attachments={attached} onDetach={detach} onAttach={attachHandler} />
  )

  return (
    <div className="cx-app">
      <Sidebar chats={history} activeId={chatParam} onNew={newChat} onOpen={openChat} onRemove={forget} open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="cx-main">
        <header className="cx-head">
          <button type="button" className="cx-icon-btn cx-burger" onClick={() => setNavOpen(true)} aria-label="Open the chat list"><Icon name="menu" size={19} /></button>
          {view
            ? <p className="cx-head-title">{chatTitle(preset, view)}</p>
            : (
              <select className="cx-model-pick" value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Model">
                {modesFor(window.location.hostname).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
              </select>
            )}
          <span className="cx-head-space" />
          {view?.mascot?.message && <p className="cx-head-sub" aria-live="polite">{view.mascot.message}</p>}
          <span className="cx-head-mascot"><sentinel-mascot state={view?.mascot?.state ?? 'sleeping'} message="" size="36" /></span>
          {chip && chip.kind === 'quarantined' && <span className={`cx-chip-status cx-chip-status--${chip.kind}`}>{chip.text}</span>}
          {view && <button type="button" className="cx-details-btn" onClick={() => setDetailsOpen((o) => !o)} aria-expanded={detailsOpen}><Icon name="list" size={16} /> Details</button>}
        </header>

        {empty ? (
          <div className="cx-landing">
            <h1 className="cx-landing-title">What can I help with?</h1>
            {box}
            {connector && (
              <label className="cx-connector">
                <input type="checkbox" checked={useConnector} onChange={(e) => setUseConnector(e.target.checked)} />
                <span>Use the real GitHub connector</span>
              </label>
            )}
            <Suggestions presets={suggestions(presets.list)} busy={busy} onPick={suggest} errorText={unreachable} />
            {error && <p className="conn-error" role="alert">{error}</p>}
          </div>
        ) : (
          <>
            <div className="cx-convo" ref={convo} onScroll={onScroll} role="log" aria-live="polite" aria-label="Conversation">
              <div className="cx-col">
                {gone && (
                  <div className="cx-card cx-gone">
                    <p className="cx-gone-title">This chat is no longer on the server</p>
                    <p className="muted">Chats live in memory, so a restart clears them. You can start a new one.</p>
                    <div><button type="button" className="s-btn s-btn--ghost s-btn--small" onClick={() => forget(chatParam)}>Remove it from the list</button></div>
                  </div>
                )}
                {view && status === 'awaiting_confirmation' && <SlipCard slip={view.slip} busy={busy} onConfirm={confirm} />}
                {view && status !== 'awaiting_confirmation' && <SlipCompact slip={view.slip} />}
                {view && status !== 'awaiting_confirmation' && view.messages.map((m, i) => <Message key={m.id} m={m} working={i === lastIndex && working} />)}
                {approval && <ApprovalCard a={approval} busy={busy} onDecide={decide} />}
                {busyLine(view) && <p className="cx-note" role="status">{busyLine(view)}</p>}
                {status === 'quarantined' && (
                  <div className="cx-card cx-quarantined" role="status">
                    <p><strong>QUARANTINED.</strong> This session was frozen and its permission slip revoked. Nothing more can run in it.</p>
                    <button type="button" className="s-btn s-btn--small cx-q-btn" onClick={newChat}>Start a new chat</button>
                  </div>
                )}
                {status === 'ended' && <p className="cx-note" role="status">The permission slip has expired. <button type="button" className="cx-link" onClick={newChat}>Start a new chat</button></p>}
                {error && <p className="conn-error" role="alert">{error}</p>}
              </div>
            </div>
            {box}
          </>
        )}
      </div>
      {detailsOpen && view && <Details view={view} onClose={() => setDetailsOpen(false)} />}
    </div>
  )
}
