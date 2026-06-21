import type { GoalSnapshot } from '../../types/observability'

type GoalStatePanelProps = {
  goal: GoalSnapshot | null
}

import { redactRuntimeDebugText } from '../../lib/runtimeDebugSanitizer'

function formatPercent(value: number | null) {
  if (typeof value !== 'number') {
    return 'n/a'
  }
  return `${Math.round(value * 100)}%`
}

export function GoalStatePanel({ goal }: GoalStatePanelProps) {
  if (!goal) {
    return (
      <section className="panel-card metric-card observability-card">
        <p className="card-eyebrow">Goal state</p>
        <h3>No active goal</h3>
        <p className="muted-copy">The runtime is currently idle or no goal artifact is available yet.</p>
      </section>
    )
  }

  return (
    <section className="panel-card metric-card observability-card">
      <p className="card-eyebrow">Goal state</p>
      <h3>{redactRuntimeDebugText(goal.description)}</h3>
      <div className="metric-stack">
        <div className="metric-row"><span>Status</span><strong>{redactRuntimeDebugText(goal.status)}</strong></div>
        <div className="metric-row"><span>Intent</span><strong>{redactRuntimeDebugText(goal.intent) || 'n/a'}</strong></div>
        <div className="metric-row"><span>Priority</span><strong>{goal.priority}</strong></div>
        <div className="metric-row"><span>Progress</span><strong>{formatPercent(goal.progress_score)}</strong></div>
      </div>

      <div className="observability-list-block">
        <strong>Constraints</strong>
        {goal.active_constraints.length === 0 ? <p className="muted-copy">No active constraints.</p> : (
          <ul className="observability-list">{goal.active_constraints.map((item) => <li key={item}>{redactRuntimeDebugText(item)}</li>)}</ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Success criteria</strong>
        {goal.success_criteria.length === 0 ? <p className="muted-copy">No explicit criteria.</p> : (
          <ul className="observability-list">
            {goal.success_criteria.map((criterion) => (
              <li key={`${criterion.description}-${criterion.status}`}>
                <span>{redactRuntimeDebugText(criterion.description)}</span>
                <em>{redactRuntimeDebugText(criterion.status)}</em>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="observability-list-block">
        <strong>Subgoals</strong>
        {goal.subgoals.length === 0 ? <p className="muted-copy">No subgoals recorded.</p> : (
          <ul className="observability-list">
            {goal.subgoals.map((subgoal) => (
              <li key={subgoal.subgoal_id}>
                <span>{redactRuntimeDebugText(subgoal.description)}</span>
                <em>{redactRuntimeDebugText(subgoal.status)}</em>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
