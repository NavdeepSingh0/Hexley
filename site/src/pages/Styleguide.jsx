// Dev page: every shared primitive (design/primitives.css) on the shared tokens (design/tokens.css), for review in both themes.
// Not linked from the nav. Phase F0 of docs/plans/BUILD_PLAN.md.
const SWATCHES = [
  ['bg', 'Page'], ['panel', 'Panel'], ['raised', 'Raised'], ['ink', 'Ink'], ['muted', 'Muted'],
  ['brand', 'Brand text'], ['brand-fill', 'Brand fill'], ['allowed', 'Allowed'], ['denied', 'Denied'],
  ['approval', 'Needs approval'], ['harm', 'Harm'], ['quarantined-bg', 'Quarantined'],
]

function Section({ title, children }) {
  return (
    <section className="sg-section">
      <p className="s-label">{title}</p>
      {children}
    </section>
  )
}

export default function Styleguide() {
  return (
    <main className="sg">
      <p className="s-label">Dev page · phase F0</p>
      <h1 className="sg-title">Styleguide</h1>
      <p className="sg-lede">Every shared primitive on the shared tokens. Switch the theme in the top bar and check both.</p>

      <Section title="Colour tokens">
        <div className="sg-swatches">
          {SWATCHES.map(([token, name]) => (
            <div key={token} className="sg-swatch">
              <span className="sg-chip" style={{ background: `var(--${token})` }} />
              <span>{name}</span>
              <code>--{token}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Type: display, body, label">
        <p className="s-verdict" style={{ marginBottom: 'var(--space-3)' }}>Display 40</p>
        <p className="sg-body">Body 18. The AI can only do the job you gave it.</p>
        <p className="s-label">Label 13, tracked capitals</p>
      </Section>

      <Section title="Buttons">
        <div className="sg-row">
          <button className="s-btn s-btn--primary">Primary action</button>
          <button className="s-btn s-btn--ghost">Secondary</button>
          <button className="s-btn s-btn--primary s-btn--small">Small</button>
          <button className="s-btn s-btn--ghost" disabled>Disabled</button>
        </div>
      </Section>

      <Section title="Panels">
        <div className="sg-row">
          <div className="s-panel"><p className="s-label">Panel</p><p className="sg-body">Quiet by default.</p></div>
          <div className="s-panel s-panel--raised"><p className="s-label">Raised</p><p className="sg-body">One step up.</p></div>
          <div className="s-panel is-active"><p className="s-label">Active</p><p className="sg-body">Top highlight and a brand outline.</p></div>
        </div>
      </Section>

      <Section title="Verdict words (glow on the one decisive element only)">
        <div className="sg-row">
          <div className="s-panel"><p className="s-verdict s-verdict--allowed">Allowed</p><p className="sg-body">What was asked was done.</p></div>
          <div className="s-panel is-active"><p className="s-verdict s-verdict--denied s-glow">Denied</p><p className="sg-body">Restricted data stayed in.</p></div>
          <div className="s-panel"><p className="s-verdict s-verdict--approval">Needs approval</p><p className="sg-body">The officer decides.</p></div>
          <div className="s-panel"><p className="s-verdict s-verdict--quarantined">Quarantined</p><p className="sg-body">The session is frozen.</p></div>
          <div className="s-panel"><p className="s-verdict s-verdict--harm">Leaked</p><p className="sg-body">Reached the outside.</p></div>
        </div>
      </Section>

      <Section title="Status badges and keys">
        <div className="sg-row">
          <span className="s-badge s-badge--tested">Tested</span>
          <span className="s-badge">Should work</span>
          <span className="s-badge s-badge--planned">Planned</span>
          <span><span className="s-kbd">Enter</span> <span className="s-kbd">V</span> <span className="s-kbd">T</span> <span className="s-kbd">N</span></span>
        </div>
      </Section>
    </main>
  )
}
