import DrawerShell from '../chrome/DrawerShell.jsx'
import { isParaphraseGap, laneCountLine, laneLabel, laneVerdict } from '../lib/derive.js'
import { Effects, StepCard, restrictedTokens } from './Stage.jsx'

// Everything a lane did, on demand: its verdict, each step in order, and what reached the outside.
// "Why?" on a denied Hexley step goes one level deeper (the verdict drawer), with a way back here.
export default function StepsDrawer({ view, laneId, onWhy, onDismiss }) {
  const lane = view.lanes.find((l) => l.lane_id === laneId)
  if (!lane) return null
  const isSentinel = lane.column === 'sentinel'
  const verdict = laneVerdict(lane, view.scenario.id)
  const label = laneLabel(lane, view.scenario.id)
  return (
    <DrawerShell label={label} onDismiss={onDismiss} ariaLabel={`Steps: ${label}`}>
      <p className="drawer-title">{verdict.word}: {verdict.sentence}</p>
      <p className="drawer-summary">{laneCountLine(lane)}</p>
      {isParaphraseGap(lane, view.scenario.id) ? (
        <p className="gap-note">
          Neither the value matcher nor the evaluation oracle finds a listed value in this wording, yet the sentence still describes
          stock: the declared gap that hardened mode closes by allowing no free text.
        </p>
      ) : null}
      {lane.contract?.egress_template && isSentinel ? (
        <div className="template-box">
          <p className="s-label">The only message this agent can send</p>
          <p className="template-body">{lane.contract.egress_template.body}</p>
        </div>
      ) : null}
      <ol className="steps">
        {(lane.steps || []).map((s, i) => (
          <StepCard key={s.action_id} step={s} index={i} isSentinel={isSentinel} onWhy={(idx) => onWhy(lane.lane_id, idx)} />
        ))}
      </ol>
      <Effects lane={lane} view={view} tokens={restrictedTokens(view)} />
    </DrawerShell>
  )
}
