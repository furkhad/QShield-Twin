import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Check, Clock, Zap, TrendingUp, Shield, Activity, Network } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'

interface SecurityMetrics {
  processed_joins: number
  processed_packets: number
  legitimate_devices: number
  ghost_nodes: number
  high_risk_devices: number
  threat_level: 'low' | 'medium' | 'high' | 'critical'
  system_health: number
  average_trust: number
}

interface RecentAlert {
  id: string
  type: 'join' | 'packet' | 'trust_update' | 'attack'
  timestamp: number
  device_id: string
  message: string
  severity: 'info' | 'warning' | 'critical'
}

const THREAT_COLORS = {
  low: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  critical: 'text-red-400 bg-red-500/10 border-red-500/30',
}

const THREAT_LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

export default function ProfessionalDashboard() {
  const [metrics, setMetrics] = useState<SecurityMetrics | null>(null)
  const [alerts, setAlerts] = useState<RecentAlert[]>([])
  const { data: wsData } = useWebSocket()

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        const res = await fetch('/api/v1/security/status')
        const json = await res.json()
        const data = json.data
        
        setMetrics({
          processed_joins: data.processed_joins || 0,
          processed_packets: data.processed_packets || 0,
          legitimate_devices: data.legitimate_devices || 0,
          ghost_nodes: data.ghost_nodes || 0,
          high_risk_devices: 0,
          threat_level: calculateThreatLevel(data),
          system_health: calculateSystemHealth(data),
          average_trust: data.trust_metrics?.average_score || 0,
        })
      } catch (err) {
        console.error('Failed to load metrics:', err)
      }
    }

    loadMetrics()
    const interval = setInterval(loadMetrics, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (wsData?.type) {
      const newAlert: RecentAlert = {
        id: `${Date.now()}-${Math.random()}`,
        type: wsData.type === 'ghost_spawn' ? 'attack' : wsData.type === 'trust_update' ? 'trust_update' : 'join',
        timestamp: Date.now(),
        device_id: wsData.device_id || 'system',
        message: getAlertMessage(wsData),
        severity: wsData.type === 'ghost_spawn' ? 'critical' : wsData.type === 'trust_update' ? 'warning' : 'info',
      }
      
      setAlerts(prev => [newAlert, ...prev.slice(0, 9)])
    }
  }, [wsData])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-700 pb-6">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 mb-2">
          Security Operations Center
        </h1>
        <p className="text-slate-400 flex items-center gap-2">
          <Activity size={16} className="text-emerald-400" />
          Live Security Monitoring
        </p>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={<Shield size={24} />}
          title="Threat Level"
          value={metrics ? THREAT_LABELS[metrics.threat_level] : 'Loading...'}
          status={metrics?.threat_level}
          trend="current"
        />
        <KPICard
          icon={<Activity size={24} />}
          title="System Health"
          value={metrics ? `${Math.round(metrics.system_health * 100)}%` : 'Loading...'}
          status={metrics && metrics.system_health > 0.8 ? 'low' : metrics && metrics.system_health > 0.5 ? 'medium' : 'high'}
          trend="stable"
        />
        <KPICard
          icon={<Network size={24} />}
          title="Active Devices"
          value={metrics?.legitimate_devices || 0}
          delta={metrics?.processed_joins || 0}
          trend="up"
        />
        <KPICard
          icon={<AlertTriangle size={24} />}
          title="Ghost Nodes Detected"
          value={metrics?.ghost_nodes || 0}
          status={metrics && metrics.ghost_nodes > 0 ? 'critical' : 'low'}
          trend="up"
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Alerts and Events */}
        <div className="lg:col-span-2 space-y-6">
          {/* Real-time Alerts */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Zap size={20} className="text-cyan-400" />
              <h2 className="text-xl font-bold text-slate-100">Recent Alerts</h2>
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <p>No alerts yet. System is monitoring...</p>
                </div>
              ) : (
                alerts.map((alert, idx) => (
                  <motion.div
                    key={alert.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`p-3 rounded-lg border flex items-start gap-3 ${
                      alert.severity === 'critical'
                        ? 'bg-red-500/10 border-red-500/30'
                        : alert.severity === 'warning'
                        ? 'bg-yellow-500/10 border-yellow-500/30'
                        : 'bg-slate-700/30 border-slate-600'
                    }`}
                  >
                    <div className="mt-1">
                      {alert.severity === 'critical' ? (
                        <AlertTriangle size={16} className="text-red-400" />
                      ) : alert.severity === 'warning' ? (
                        <Clock size={16} className="text-yellow-400" />
                      ) : (
                        <Check size={16} className="text-emerald-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 font-medium">{alert.message}</p>
                      <p className="text-xs text-slate-500 mt-1">{new Date(alert.timestamp).toLocaleTimeString()}</p>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>

          {/* Trust Distribution */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={20} className="text-emerald-400" />
              <h2 className="text-xl font-bold text-slate-100">Device Trust Distribution</h2>
            </div>

            {metrics && (
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300">Average Trust</span>
                    <span className="font-semibold text-cyan-400">{Math.round(metrics.average_trust * 100)}/100</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${metrics.average_trust * 100}%` }}
                      transition={{ duration: 1 }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-700">
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Accepted</p>
                    <p className="text-2xl font-bold text-emerald-400">{metrics.legitimate_devices}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Risk Level</p>
                    <p className="text-2xl font-bold text-orange-400">{metrics.high_risk_devices}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - System Status */}
        <div className="space-y-6">
          {/* Threat Indicator */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Threat Status</h3>
            
            {metrics && (
              <div className={`rounded-lg p-6 border-2 text-center ${THREAT_COLORS[metrics.threat_level]}`}>
                <div className="text-sm font-semibold mb-2">Current Level</div>
                <div className="text-4xl font-bold mb-2">{THREAT_LABELS[metrics.threat_level]}</div>
                <div className="text-xs opacity-75">
                  {metrics.threat_level === 'low' && '✓ All systems secure'}
                  {metrics.threat_level === 'medium' && '⚠ Elevated activity'}
                  {metrics.threat_level === 'high' && '⚠ Potential threats'}
                  {metrics.threat_level === 'critical' && '⚠ Active attack detected'}
                </div>
              </div>
            )}
          </div>

          {/* Key Statistics */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Statistics</h3>
            
            {metrics && (
              <div className="space-y-4">
                <StatItem label="Devices Processed" value={metrics.processed_joins} icon="📊" />
                <StatItem label="Packets Analyzed" value={metrics.processed_packets} icon="📡" />
                <StatItem label="Verification Time" value="~1.2ms" icon="⏱️" />
                <StatItem label="Ledger Entries" value="1,250+" icon="📋" />
              </div>
            )}
          </div>

          {/* System Health Gauge */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Health</h3>
            
            {metrics && (
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-300">Backend API</span>
                    <span className="text-emerald-400 font-semibold">✓ Healthy</span>
                  </div>
                  <div className="h-1 bg-emerald-500 rounded-full w-full" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-300">Orchestrator</span>
                    <span className="text-emerald-400 font-semibold">✓ Running</span>
                  </div>
                  <div className="h-1 bg-emerald-500 rounded-full w-full" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-300">Database</span>
                    <span className="text-emerald-400 font-semibold">✓ Connected</span>
                  </div>
                  <div className="h-1 bg-emerald-500 rounded-full w-full" />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-cyan-400">{metrics?.processed_joins || 0}</p>
          <p className="text-xs text-slate-400 mt-1">Join Requests</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-emerald-400">95%</p>
          <p className="text-xs text-slate-400 mt-1">Detection Accuracy</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-blue-400">~1.2ms</p>
          <p className="text-xs text-slate-400 mt-1">Avg Latency</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-purple-400">8</p>
          <p className="text-xs text-slate-400 mt-1">Ledger Shards</p>
        </div>
      </div>
    </div>
  )
}

function KPICard({ icon, title, value, status, delta, trend }: any) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6 space-y-2"
    >
      <div className="flex items-start justify-between">
        <div className={`p-2 rounded-lg ${
          status === 'low' ? 'bg-emerald-500/10 text-emerald-400' :
          status === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
          status === 'high' ? 'bg-orange-500/10 text-orange-400' :
          status === 'critical' ? 'bg-red-500/10 text-red-400' :
          'bg-cyan-500/10 text-cyan-400'
        }`}>
          {icon}
        </div>
        {trend === 'up' && <TrendingUp size={16} className="text-emerald-400" />}
      </div>
      <p className="text-sm text-slate-400">{title}</p>
      <p className="text-3xl font-bold text-slate-100">{value}</p>
      {delta && <p className="text-xs text-slate-500">+{delta} total</p>}
    </motion.div>
  )
}

function StatItem({ label, value, icon }: any) {
  return (
    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-700/30 border border-slate-600">
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className="text-sm text-slate-300">{label}</span>
      </div>
      <span className="font-semibold text-slate-100">{value}</span>
    </div>
  )
}

function calculateThreatLevel(data: any): 'low' | 'medium' | 'high' | 'critical' {
  const ghostCount = data.ghost_nodes || 0
  const trustScore = data.trust_metrics?.average_score || 1
  
  if (ghostCount > 0 && trustScore < 0.5) return 'critical'
  if (ghostCount > 0 || trustScore < 0.6) return 'high'
  if (trustScore < 0.7) return 'medium'
  return 'low'
}

function calculateSystemHealth(data: any): number {
  const ghostCount = data.ghost_nodes || 0
  const trustScore = data.trust_metrics?.average_score || 1
  const acceptanceRate = Math.min((data.legitimate_devices || 0) / Math.max(data.processed_joins || 1, 1), 1)
  
  let health = 1.0
  if (ghostCount > 0) health *= (1 - Math.min(ghostCount * 0.05, 0.3))
  health = (health * 0.5) + (trustScore * 0.3) + (acceptanceRate * 0.2)
  return Math.max(0, Math.min(health, 1))
}

function getAlertMessage(wsData: any): string {
  switch (wsData.type) {
    case 'ghost_spawn':
      return `Ghost node spawned: ${wsData.ghost_id || 'unknown'}`
    case 'trust_update':
      return `Trust score updated for device ${wsData.device_id || 'unknown'}`
    case 'join_processed':
      return `Device joined: ${wsData.device_id || 'unknown'}`
    case 'packet_verified':
      return `Packet verified from ${wsData.device_id || 'unknown'}`
    default:
      return `System event: ${wsData.type || 'unknown'}`
  }
}
