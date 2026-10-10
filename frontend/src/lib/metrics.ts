// Normalises backend analytics payloads into stable, typed shapes.
//
// The backend `metrics()` response exposes `detection_accuracy` (scores) and
// `confusion_matrix` (counts). Some older UI code referred to a flattened
// `detection_metrics` object; this helper bridges both so pages can read real
// values regardless of which representation is present.

export interface DetectionMetrics {
  precision: number
  recall: number
  f1_score: number
  accuracy: number
  false_positive_rate: number
  false_positives: number
  false_negatives: number
  true_positives: number
  true_negatives: number
}

const EMPTY_DETECTION: DetectionMetrics = {
  precision: 0,
  recall: 0,
  f1_score: 0,
  accuracy: 0,
  false_positive_rate: 0,
  false_positives: 0,
  false_negatives: 0,
  true_positives: 0,
  true_negatives: 0,
}

function num(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : 0
}

export function extractDetectionMetrics(analytics: any): DetectionMetrics {
  if (!analytics) return { ...EMPTY_DETECTION }
  const scores = analytics.detection_accuracy ?? analytics.detection_metrics ?? {}
  const cm = analytics.confusion_matrix ?? {}
  return {
    precision: num(scores.precision),
    recall: num(scores.recall),
    f1_score: num(scores.f1_score),
    accuracy: num(scores.accuracy),
    false_positive_rate: num(scores.false_positive_rate),
    false_positives: num(cm.false_positives ?? scores.false_positives),
    false_negatives: num(cm.false_negatives ?? scores.false_negatives),
    true_positives: num(cm.true_positives ?? scores.true_positives),
    true_negatives: num(cm.true_negatives ?? scores.true_negatives),
  }
}

export interface TrustMetrics {
  total_devices: number
  average: number
  accepted: number
  monitored: number
  rejected: number
  blacklisted: number
}

export function extractTrust(status: any): TrustMetrics {
  // The backend nests the trust block under `security.trust`; tolerate older
  // flat shapes as well.
  const t =
    status?.security?.trust ??
    status?.trust ??
    status?.trust_metrics ??
    {}
  return {
    total_devices: num(t.total_devices),
    average: num(t.average_trust ?? t.average_score),
    accepted: num(t.accepted_count),
    monitored: num(t.monitored_count),
    rejected: num(t.rejected_count),
    blacklisted: num(t.blacklisted_count),
  }
}

export interface SecurityCounters {
  processed_joins: number
  processed_packets: number
  legitimate_devices: number
  ghost_nodes: number
}

/**
 * Security counters live under `security` in the `/security/status` payload;
 * this reads them robustly whether the caller passes the full status object or
 * the already-unwrapped `security` sub-object.
 */
export function extractSecurityCounters(status: any): SecurityCounters {
  const s = status?.security ?? status ?? {}
  return {
    processed_joins: num(s.processed_joins),
    processed_packets: num(s.processed_packets),
    legitimate_devices: num(s.legitimate_devices),
    ghost_nodes: num(s.ghost_nodes),
  }
}

export interface VerificationMetrics {
  total: number
  acceptanceRate: number
  avgPropagationMs: number
  avgConfidence: number
}

export function extractVerification(v: any): VerificationMetrics {
  if (!v) return { total: 0, acceptanceRate: 0, avgPropagationMs: 0, avgConfidence: 0 }
  return {
    total: num(v.total_verifications),
    acceptanceRate: num(v.acceptance_rate),
    // The proximity engine reports average_propagation_delay_ms; older UI code
    // referenced a non-existent `average_time`.
    avgPropagationMs: num(v.average_propagation_delay_ms ?? v.average_time),
    avgConfidence: num(v.average_confidence),
  }
}
