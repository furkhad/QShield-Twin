import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  Fingerprint,
  MapPinned,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Signal,
  Sparkles,
  TerminalSquare,
  TrendingUp,
  Wifi,
} from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'

type SecurityDecision = 'accept' | 'monitor' | 'reject' | 'blacklist' | string

interface AccessControlDevice {
  device_id: string
  name: string
  device_type: string
  zone?: string
  x?: number
  y?: number
  legitimate?: boolean
  malicious?: boolean
  trust_score?: number
  authentication_status?: string
  proximity_status?: string
  connection_status?: string
  security_decision?: SecurityDecision
  threat_status?: string
  attacker_id?: string | null
}

interface AccessControlZone {
  zone_id: string
  name: string
  x: number
  y: number
  width: number
  height: number
}

interface SecurityEvent {
  timestamp: number
  event_type?: string
  device_id?: string
  device_type?: string
  zone?: string
  security_status?: string
  trust_score?: number
  decision?: string
  message?: string
  authentication_status?: string
  proximity_status?: string
}

interface DashboardState {
  overview: {
    total_devices: number
    active_devices: number
    trusted_devices: number
    monitoring_devices: number
    rejected_devices: number
    blacklisted_devices: number
    accepted_devices: number
  }
  zones: AccessControlZone[]
  devices: AccessControlDevice[]
  events: SecurityEvent[]
  analytics: any
  trust: any
  ledger: any
  security: any
}

const EMPTY_STATE: DashboardState = {
  overview: {
    total_devices: 0,
    active_devices: 0,
    trusted_devices: 0,
    monitoring_devices: 0,
    rejected_devices: 0,
    blacklisted_devices: 0,
    accepted_devices: 0,
  },
  zones: [],
  devices: [],
  events: [],
  analytics: {},
  trust: {},
  ledger: {},
  security: {},
}

export default function ProfessionalDashboard() {
  const [state, setState] = useState<DashboardState>(EMPTY_STATE)
  const [loading, setLoading] = useState(true)
  const [isRunningDemo, setIsRunningDemo] = useState(false)
  const [lastDemoMessage, setLastDemoMessage] = useState<string | null>(null)
  const { data: wsData, connected } = useWebSocket()

  const loadState = async () => {
    try {
      const [statusResponse, analyticsResponse] = await Promise.all([
        fetch('/api/v1/security/status'),
        fetch('/api/v1/security/analytics'),
      ])

      const statusJson = await statusResponse.json()
      const analyticsJson = await analyticsResponse.json()
      const statusData = statusJson.data ?? {}
      const securityData = statusData.security ?? {}
      const accessControl = statusData.access_control ?? {}

      setState({
        overview: statusData.overview ?? EMPTY_STATE.overview,
        zones: accessControl.zones ?? [],
        devices: accessControl.devices ?? statusData.devices ?? [],
        events: securityData.recent_events ?? [],
        analytics: analyticsJson.data ?? securityData.analytics ?? {},
        trust: securityData.trust ?? {},
        ledger: securityData.ledger ?? {},
        security: securityData,
      })
    } catch (error) {
      console.error('Failed to load SecureAccess dashboard state:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadState()
    const interval = window.setInterval(loadState, 3000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!wsData) {
      return
    }

    const payload = wsData.payload ?? wsData
    const mappedEvent: SecurityEvent | null = payload?.event_type
      ? {
          timestamp: payload.timestamp ?? Date.now(),
          event_type: payload.event_type,
          device_id: payload.device_id,
          device_type: payload.device_type,
          zone: payload.zone,
          security_status: payload.security_status,
          trust_score: payload.trust_score,
          decision: payload.decision,
          message: payload.message,
          authentication_status: payload.authentication_status,
          proximity_status: payload.proximity_status,
        }
      : null

    if (mappedEvent) {
      setState((current) => ({
        ...current,
        events: [mappedEvent, ...current.events].slice(0, 40),
      }))
    }
  }, [wsData])

  const analytics = state.analytics ?? {}
  const detection = analytics.detection_accuracy ?? {}
  const performance = analytics.performance ?? {}
  const acceptanceRate = state.overview.total_devices > 0
    ? state.overview.accepted_devices / state.overview.total_devices
    : 0

  const averageTrust = state.trust.average_trust ?? performance.average_trust_score ?? 0

  const zoneBuckets = useMemo(() => {
    return state.zones.map((zone) => ({
      ...zone,
      devices: state.devices.filter((device) => device.zone === zone.zone_id),
    }))
  }, [state.devices, state.zones])

  const latestEvents = state.events.slice(0, 10)

  async function runDemo() {
    setIsRunningDemo(true)
    setLastDemoMessage(null)
    try {
      const response = await fetch('/api/v1/security/demo/access-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ legitimate_count: 100, ghost_count: 20 }),
      })
      const json = await response.json()
      if (json.status !== 'ok') {
        throw new Error(json.message || 'Access-control demo failed')
      }
      setLastDemoMessage('Access-control demo completed. Live data refreshed from backend state.')
      await loadState()
    } catch (error) {
      console.error(error)
      setLastDemoMessage('Access-control demo failed. Check backend logs for details.')
    } finally {
      setIsRunningDemo(false)
    }
  }

  if (loading) {
    return <div className="text-slate-400 py-12 text-center">Loading SecureAccess console...</div>
  }

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-cyan-400/20 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_45%),linear-gradient(135deg,_rgba(2,6,23,0.96),_rgba(15,23,42,0.92))] p-8 shadow-2xl shadow-cyan-950/20">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-xs uppercase tracking-[0.3em] text-cyan-200">
              <ShieldCheck size={14} /> QShield SecureAccess
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white md:text-5xl">Quantum-Resilient Cyber-Physical Security</h1>
              <p className="mt-3 max-w-3xl text-slate-300">
                Protecting connected access-control systems by combining identity authentication, software-simulated
                ToF proximity verification, simulated lattice-based PQC, ghost/Sybil detection, multi-factor trust,
                and an 8-shard hash-based audit ledger.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 text-sm text-slate-300">
              <StatusBadge label={connected ? 'WebSocket Connected' : 'WebSocket Reconnecting'} tone={connected ? 'good' : 'warn'} icon={<Wifi size={14} />} />
              <StatusBadge label={`${state.overview.total_devices} Devices`} tone="neutral" icon={<Signal size={14} />} />
              <StatusBadge label={`${state.overview.rejected_devices} Rejected`} tone="bad" icon={<ShieldAlert size={14} />} />
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-2xl border border-slate-700 bg-slate-950/60 p-4 md:min-w-[320px]">
            <div className="flex items-center gap-2 text-slate-300">
              <Sparkles size={16} className="text-cyan-300" /> Live access-control demo
            </div>
            <p className="text-sm text-slate-400">
              Runs 100 legitimate devices and 20 simulated ghost identities through the existing security pipeline.
            </p>
            <button
              onClick={runDemo}
              disabled={isRunningDemo}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <TerminalSquare size={16} />
              {isRunningDemo ? 'Running demo...' : 'Run Ghost/Sybil Simulation'}
            </button>
            {lastDemoMessage ? <p className="text-xs text-cyan-200">{lastDemoMessage}</p> : null}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard icon={<Database size={20} />} label="Total Devices" value={state.overview.total_devices} tone="cyan" />
        <MetricCard icon={<Activity size={20} />} label="Active Devices" value={state.overview.active_devices} tone="emerald" />
        <MetricCard icon={<ShieldCheck size={20} />} label="Trusted Devices" value={state.overview.trusted_devices} tone="emerald" />
        <MetricCard icon={<Shield size={20} />} label="Monitoring" value={state.overview.monitoring_devices} tone="amber" />
        <MetricCard icon={<ShieldAlert size={20} />} label="Rejected" value={state.overview.rejected_devices} tone="orange" />
        <MetricCard icon={<AlertTriangle size={20} />} label="Blacklisted" value={state.overview.blacklisted_devices} tone="rose" />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 rounded-3xl border border-slate-700 bg-slate-950/80 p-6">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-white">Building / Digital Twin View</h2>
              <p className="text-sm text-slate-400">Zones and connected access-control devices from the live simulation.</p>
            </div>
            <div className="text-xs text-slate-400">
              <span className="rounded-full border border-slate-700 px-3 py-1">Legend</span>
              <span className="ml-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">Trusted</span>
              <span className="ml-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-amber-300">Monitoring</span>
              <span className="ml-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-rose-300">Rejected</span>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {zoneBuckets.map((zone) => (
              <motion.div
                key={zone.zone_id}
                whileHover={{ y: -2 }}
                className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-white">{zone.name}</h3>
                    <p className="text-xs text-slate-400">{zone.devices.length} devices</p>
                  </div>
                  <MapPinned size={18} className="text-cyan-300" />
                </div>
                <div className="flex flex-wrap gap-2">
                  {zone.devices.slice(0, 6).map((device) => (
                    <DeviceChip key={device.device_id} device={device} />
                  ))}
                  {zone.devices.length > 6 ? (
                    <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400">
                      +{zone.devices.length - 6} more
                    </span>
                  ) : null}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <section className="rounded-3xl border border-slate-700 bg-slate-950/80 p-6">
            <h2 className="mb-4 text-xl font-semibold text-white">Security / Trust Analytics</h2>
            <div className="space-y-4">
              <AnalyticsBar label="Precision" value={detection.precision ?? 0} tone="cyan" />
              <AnalyticsBar label="Recall" value={detection.recall ?? 0} tone="emerald" />
              <AnalyticsBar label="F1 Score" value={detection.f1_score ?? 0} tone="violet" />
              <AnalyticsBar label="Average Trust" value={averageTrust} tone="amber" />
              <AnalyticsBar label="Acceptance Rate" value={acceptanceRate} tone="sky" />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <MiniMetric label="Ghost detections" value={analytics.attack_defense?.ghosts_detected ?? 0} />
              <MiniMetric label="Rejected devices" value={state.overview.rejected_devices} />
              <MiniMetric label="Blacklisted devices" value={state.overview.blacklisted_devices} />
              <MiniMetric label="Ledger entries" value={state.ledger.total_entries ?? 0} />
            </div>
          </section>

          <section className="rounded-3xl border border-slate-700 bg-slate-950/80 p-6">
            <h2 className="mb-4 text-xl font-semibold text-white">Technical Honesty</h2>
            <div className="space-y-3 text-sm text-slate-300">
              <p>Simulated lattice-based PQC interface, not production Kyber/Dilithium.</p>
              <p>Software-simulated ToF proximity verification, not hardware-grade ranging.</p>
              <p>8-shard hash-based audit ledger, not blockchain consensus.</p>
            </div>
          </section>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-700 bg-slate-950/80 p-6">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Device Security Table</h2>
            <p className="text-sm text-slate-400">Live device security state derived from the backend simulation.</p>
          </div>
          <div className="text-sm text-slate-400">Real-time state from backend API and WebSocket updates</div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-800">
          <table className="min-w-full divide-y divide-slate-800 text-sm">
            <thead className="bg-slate-900 text-slate-300">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Device ID</th>
                <th className="px-4 py-3 text-left font-medium">Device Type</th>
                <th className="px-4 py-3 text-left font-medium">Zone</th>
                <th className="px-4 py-3 text-left font-medium">Authentication</th>
                <th className="px-4 py-3 text-left font-medium">Proximity</th>
                <th className="px-4 py-3 text-left font-medium">Trust Score</th>
                <th className="px-4 py-3 text-left font-medium">Threat Status</th>
                <th className="px-4 py-3 text-left font-medium">Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950/60">
              {state.devices.slice(0, 30).map((device) => (
                <tr key={device.device_id} className="hover:bg-slate-900/60">
                  <td className="px-4 py-3 font-mono text-xs text-cyan-200">{device.device_id}</td>
                  <td className="px-4 py-3 text-slate-200">{formatDeviceType(device.device_type)}</td>
                  <td className="px-4 py-3 text-slate-300">{formatZone(device.zone)}</td>
                  <td className="px-4 py-3">{statusPill(device.authentication_status, device.authentication_status === 'verified' ? 'good' : 'bad')}</td>
                  <td className="px-4 py-3">{statusPill(device.proximity_status, device.proximity_status === 'accept' ? 'good' : device.proximity_status === 'suspicious' ? 'warn' : 'bad')}</td>
                  <td className="px-4 py-3 text-slate-200">{formatScore(device.trust_score)}</td>
                  <td className="px-4 py-3">{statusPill(device.threat_status || inferThreatStatus(device), threatTone(device))}</td>
                  <td className="px-4 py-3">{decisionPill(device.security_decision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-3xl border border-slate-700 bg-slate-950/80 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Sparkles size={18} className="text-cyan-300" />
            <h2 className="text-xl font-semibold text-white">Security Events</h2>
          </div>
          <div className="space-y-3">
            {latestEvents.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400">
                No security events yet. Run the demo or wait for live activity.
              </div>
            ) : (
              latestEvents.map((event, index) => (
                <motion.div
                  key={`${event.timestamp}-${event.device_id}-${index}`}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-white">{event.message || formatEvent(event.event_type)}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {event.device_id || 'system'} {event.zone ? `• ${formatZone(event.zone)}` : ''} {event.device_type ? `• ${formatDeviceType(event.device_type)}` : ''}
                      </p>
                    </div>
                    <div className="text-right text-xs text-slate-400">
                      <div>{formatTimestamp(event.timestamp)}</div>
                      <div className="mt-1">{event.security_status || 'info'}</div>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-700 bg-slate-950/80 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Fingerprint size={18} className="text-emerald-300" />
            <h2 className="text-xl font-semibold text-white">Attack Simulation Metrics</h2>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <MetricTile label="Ghost detections" value={analytics.attack_defense?.ghosts_detected ?? 0} icon={<ShieldAlert size={16} />} />
            <MetricTile label="Precision" value={formatPercent(detection.precision)} icon={<ShieldCheck size={16} />} />
            <MetricTile label="Recall" value={formatPercent(detection.recall)} icon={<TrendingUp size={16} />} />
            <MetricTile label="F1 score" value={formatPercent(detection.f1_score)} icon={<CheckCircle2 size={16} />} />
            <MetricTile label="Legitimate acceptance" value={formatPercent(acceptanceRate)} icon={<Wifi size={16} />} />
            <MetricTile label="False rejection count" value={detection.false_negatives ?? 0} icon={<AlertTriangle size={16} />} />
          </div>

          <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
            <p>
              The values above are simulation results from the configured access-control scenario. They are useful for
              demonstrating the workflow, not for claiming production security accuracy.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

function MetricCard({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: number; tone: 'cyan' | 'emerald' | 'amber' | 'orange' | 'rose' }) {
  const toneClasses: Record<typeof tone, string> = {
    cyan: 'from-cyan-500/10 to-cyan-400/5 border-cyan-400/20 text-cyan-200',
    emerald: 'from-emerald-500/10 to-emerald-400/5 border-emerald-400/20 text-emerald-200',
    amber: 'from-amber-500/10 to-amber-400/5 border-amber-400/20 text-amber-200',
    orange: 'from-orange-500/10 to-orange-400/5 border-orange-400/20 text-orange-200',
    rose: 'from-rose-500/10 to-rose-400/5 border-rose-400/20 text-rose-200',
  }

  return (
    <motion.div whileHover={{ y: -2 }} className={`rounded-2xl border bg-gradient-to-br p-5 ${toneClasses[tone]} bg-slate-950/80`}>
      <div className="flex items-center justify-between">
        <div className="rounded-xl border border-white/10 bg-white/5 p-2 text-white">{icon}</div>
        <span className="text-xs uppercase tracking-[0.3em] text-slate-400">{label}</span>
      </div>
      <div className="mt-5 text-3xl font-bold text-white">{value}</div>
    </motion.div>
  )
}

function DeviceChip({ device }: { device: AccessControlDevice }) {
  const tone = device.security_decision === 'accept' ? 'emerald' : device.security_decision === 'monitor' ? 'amber' : device.security_decision === 'blacklist' || device.security_decision === 'reject' ? 'rose' : 'slate'
  const classes: Record<string, string> = {
    emerald: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
    amber: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
    rose: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
    slate: 'border-slate-700 bg-slate-800 text-slate-200',
  }

  return <span className={`rounded-full border px-3 py-1 text-xs ${classes[tone]}`}>{formatShortDevice(device)}</span>
}

function AnalyticsBar({ label, value, tone }: { label: string; value: number; tone: 'cyan' | 'emerald' | 'amber' | 'violet' | 'sky' }) {
  const colors: Record<typeof tone, string> = {
    cyan: 'from-cyan-500 to-cyan-300',
    emerald: 'from-emerald-500 to-emerald-300',
    amber: 'from-amber-500 to-amber-300',
    violet: 'from-violet-500 to-violet-300',
    sky: 'from-sky-500 to-sky-300',
  }

  const percentage = Math.max(0, Math.min(1, value || 0)) * 100

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
        <span>{label}</span>
        <span className="text-white">{formatPercent(value)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full bg-gradient-to-r ${colors[tone]}`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
      <div className="text-xs uppercase tracking-[0.25em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  )
}

function MetricTile({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        {icon}
        <span>{label}</span>
      </div>
      <div className="mt-2 text-xl font-semibold text-white">{value}</div>
    </div>
  )
}

function StatusBadge({ label, tone, icon }: { label: string; tone: 'good' | 'warn' | 'bad' | 'neutral'; icon: React.ReactNode }) {
  const toneClasses: Record<typeof tone, string> = {
    good: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
    warn: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
    bad: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
    neutral: 'border-slate-700 bg-slate-800 text-slate-200',
  }

  return <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 ${toneClasses[tone]}`}>{icon}{label}</span>
}

function statusPill(label?: string, tone: 'good' | 'warn' | 'bad' | 'neutral' = 'neutral') {
  const toneClasses = {
    good: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
    warn: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
    bad: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
    neutral: 'border-slate-700 bg-slate-800 text-slate-200',
  }
  return <span className={`inline-flex rounded-full border px-3 py-1 text-xs capitalize ${toneClasses[tone]}`}>{label || 'unknown'}</span>
}

function decisionPill(decision?: SecurityDecision) {
  const value = decision || 'monitor'
  const tone = value === 'accept' ? 'good' : value === 'monitor' ? 'warn' : 'bad'
  return statusPill(value, tone)
}

function threatTone(device: AccessControlDevice): 'good' | 'warn' | 'bad' | 'neutral' {
  if (device.security_decision === 'accept') return 'good'
  if (device.security_decision === 'monitor') return 'warn'
  if (device.security_decision === 'reject' || device.security_decision === 'blacklist') return 'bad'
  return 'neutral'
}

function inferThreatStatus(device: AccessControlDevice): string {
  if (device.malicious) return 'suspicious'
  if ((device.trust_score ?? 0) >= 0.7) return 'trusted'
  if ((device.trust_score ?? 0) >= 0.4) return 'monitoring'
  return 'rejected'
}

function formatDeviceType(deviceType?: string): string {
  if (!deviceType) return 'Unknown'
  return deviceType
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatZone(zone?: string): string {
  if (!zone) return 'Unassigned'
  return zone
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatScore(score?: number): string {
  return `${Math.round((score ?? 0) * 100)}/100`
}

function formatPercent(value?: number): string {
  return `${Math.round(((value ?? 0) * 100))}%`
}

function formatTimestamp(value?: number): string {
  if (!value) return 'now'
  const milliseconds = value > 1_000_000_000_000 ? value : value * 1000
  return new Date(milliseconds).toLocaleTimeString()
}

function formatEvent(eventType?: string): string {
  switch (eventType) {
    case 'device_join':
      return 'New access-control device detected'
    case 'packet_verified':
      return 'Physical proximity verified'
    case 'attack_started':
      return 'Ghost/Sybil simulation started'
    case 'attack_stopped':
      return 'Ghost/Sybil simulation stopped'
    default:
      return eventType || 'Security event recorded'
  }
}

function formatShortDevice(device: AccessControlDevice): string {
  const name = device.name || device.device_id
  return name.length > 28 ? `${name.slice(0, 28)}...` : name
}
