/**
 * Observability UI contract — currently aligned 1:1 with CLI snapshot shape.
 * Isolate imports here so pages depend on `Ui*` rather than raw transport types.
 */
import type { ObservabilitySnapshot, ObservabilityTracesResponse } from '../observability'

export type UiObservabilitySnapshot = ObservabilitySnapshot

export type UiObservabilityTracesResult = ObservabilityTracesResponse
