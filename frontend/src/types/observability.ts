export type GoalCriterionSnapshot = {
  description: string
  criterion_type: string
  required: boolean
  weight: number
  status: string
}

export type SubGoalSnapshot = {
  subgoal_id: string
  description: string
  status: string
  order: number
  depends_on_subgoal_ids: string[]
}

export type GoalSnapshot = {
  goal_id: string
  description: string
  intent: string
  status: string
  priority: number
  progress_score: number | null
  active_constraints: string[]
  success_criteria: GoalCriterionSnapshot[]
  subgoals: SubGoalSnapshot[]
  created_at: string
  resolved_at?: string | null
  metadata: Record<string, unknown>
}

export type TimelineEvent = {
  event_id: string
  event_type: string
  description: string
  outcome: string
  progress_score: number
  timestamp: string
  evidence_ids: string[]
  metadata: Record<string, unknown>
}

export type SpecialistDecisionSnapshot = {
  decision_id: string
  specialist_type: string
  status: string
  reasoning: string
  confidence: number
  simulation_id?: string | null
  decided_at: string
  metadata: Record<string, unknown>
}

export type GovernanceVerdictSnapshot = {
  decision_id: string
  verdict: string
  risk_level: string
  blocked_reasons: string[]
  violations: string[]
  reasoning: string
  confidence: number
  decided_at: string
}

export type TraceSnapshot = {
  trace_id: string
  goal_id?: string | null
  session_id?: string | null
  final_outcome: string
  started_at: string
  completed_at?: string | null
  decisions: SpecialistDecisionSnapshot[]
  governance_verdicts: GovernanceVerdictSnapshot[]
  metadata: Record<string, unknown>
}

export type RouteSnapshot = {
  route: string
  estimated_success_rate: number
  estimated_cost: number
  constraint_risk: number
  goal_alignment: number
  confidence: number
  score: number
  reasoning: string
  supporting_episodes: string[]
  metadata: Record<string, unknown>
}

export type SimulationSnapshot = {
  simulation_id: string
  goal_id?: string | null
  recommended_route: string
  simulated_at: string
  routes: RouteSnapshot[]
  basis: Record<string, unknown>
  metadata: Record<string, unknown>
}

export type EpisodeSnapshot = {
  episode_id: string
  goal_id: string
  subgoal_id?: string | null
  session_id: string
  description: string
  event_type: string
  outcome: string
  progress_at_start: number
  progress_at_end: number
  duration_seconds: number
  created_at: string
  evidence_ids: string[]
  constraints_active: string[]
  metadata: Record<string, unknown>
}

export type SemanticFactSnapshot = {
  fact_id: string
  subject: string
  predicate: string
  object: string
  confidence: number
  source_episode_ids: string[]
  goal_types: string[]
  created_at: string
  last_reinforced_at: string
  metadata: Record<string, unknown>
}

export type ProceduralPatternSnapshot = {
  pattern_id: string
  name: string
  description: string
  applicable_goal_types: string[]
  applicable_constraint_types: string[]
  recommended_route: string
  success_rate: number
  sample_size: number
  last_updated: string
  metadata: Record<string, unknown>
}

export type ObservabilitySnapshot = {
  generated_at: string
  goal: GoalSnapshot | null
  goal_history: GoalSnapshot[]
  timeline: TimelineEvent[]
  latest_trace: TraceSnapshot | null
  recent_traces: TraceSnapshot[]
  latest_simulation: SimulationSnapshot | null
  recent_simulations: SimulationSnapshot[]
  recent_episodes: EpisodeSnapshot[]
  semantic_facts: SemanticFactSnapshot[]
  active_procedural_pattern: ProceduralPatternSnapshot | null
  recent_procedural_updates: ProceduralPatternSnapshot[]
  recent_learning_signals: Array<Record<string, unknown>>
  pending_evolution_proposal_count: number
  recent_evolution_proposals: Array<Record<string, unknown>>
  warnings: string[]
}

export type ObservabilityApiResponse = {
  status: string
  snapshot: ObservabilitySnapshot | null
  error?: string
}

export type ObservabilityTracesResponse = {
  status: string
  traces: TraceSnapshot[]
  error?: string
}

export type ObservabilityConnectionState = 'idle' | 'live' | 'reconnecting' | 'error'
