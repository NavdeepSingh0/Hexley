import { useEffect, useRef } from 'react'

// The right-hand drawer's frame: a scrim over the stage, focus moved into the drawer, Escape and the scrim close it.
// Focus goes to the drawer itself (not a button), so the presenter's Enter still reaches the page-level key handler.
export default function DrawerShell({ label, onDismiss, onBack, ariaLabel, children }) {
  const ref = useRef(null)
  useEffect(() => {
    ref.current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onDismiss() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onDismiss])
  return (
    <>
      <div className="scrim" onClick={onDismiss} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={ariaLabel} tabIndex={-1} ref={ref}>
        <div className="drawer-top">
          <p className="s-label">{label}</p>
          <div className="drawer-top-actions">
            {onBack ? <button className="s-btn s-btn--ghost s-btn--small" onClick={onBack}>Back to steps</button> : null}
            <button className="s-btn s-btn--ghost s-btn--small" onClick={onDismiss} aria-label="Close">Close <span className="s-kbd">Esc</span></button>
          </div>
        </div>
        {children}
      </aside>
    </>
  )
}
