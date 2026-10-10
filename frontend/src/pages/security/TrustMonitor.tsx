import React, { useState, useEffect } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'

export default function TrustMonitor() {
  const [devices, setDevices] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const { data: wsData } = useWebSocket()

  useEffect(() => {
    async function loadTrust() {
      try {
        const res = await fetch('/api/v1/security/trust')
        const j = await res.json()
        if (j.data?.scores) {
          const devList = Object.entries(j.data.scores).map(([id, score]: any) => ({
            id,
            ...score,
          }))
          setDevices(devList)
        }
      } catch (err) {
        console.error(err)
      }
    }
    loadTrust()
    const iv = setInterval(loadTrust, 2000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    if (wsData?.type === 'security_event' && wsData?.payload?.type === 'trust_update') {
      // Live update from WebSocket
      setDevices((prev) => {
        const idx = prev.findIndex((d) => d.id === wsData.payload.device)
        if (idx >= 0) {
          const updated = [...prev]
          updated[idx].score = wsData.payload.score
          return updated
        }
        return prev
      })
    }
  }, [wsData])

  const getRiskColor = (score: number) => {
    if (score >= 0.7) return 'bg-green-900'
    if (score >= 0.4) return 'bg-yellow-900'
    return 'bg-red-900'
  }

  const acceptedCount = devices.filter((d) => d.decision === 'accept').length
  const monitoredCount = devices.filter((d) => d.decision === 'monitor').length
  const rejectedCount = devices.filter((d) => d.decision === 'reject').length
  const blacklistedCount = devices.filter((d) => d.decision === 'blacklist').length

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-3xl font-bold">Trust Monitor</h2>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-green-900 p-4 rounded">
          <div className="text-sm text-gray-300">Accepted</div>
          <div className="text-2xl font-bold">{acceptedCount}</div>
        </div>
        <div className="bg-yellow-900 p-4 rounded">
          <div className="text-sm text-gray-300">Monitored</div>
          <div className="text-2xl font-bold">{monitoredCount}</div>
        </div>
        <div className="bg-orange-900 p-4 rounded">
          <div className="text-sm text-gray-300">Rejected</div>
          <div className="text-2xl font-bold">{rejectedCount}</div>
        </div>
        <div className="bg-red-900 p-4 rounded">
          <div className="text-sm text-gray-300">Blacklisted</div>
          <div className="text-2xl font-bold">{blacklistedCount}</div>
        </div>
      </div>

      {/* Trust Scores Table */}
      <div className="bg-slate-800 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-2 text-left">Device ID</th>
              <th className="px-4 py-2 text-left">Score</th>
              <th className="px-4 py-2 text-left">Decision</th>
              <th className="px-4 py-2 text-left">Risk Level</th>
              <th className="px-4 py-2 text-left">Updates</th>
            </tr>
          </thead>
          <tbody>
            {devices.slice(0, 20).map((d) => (
              <tr key={d.id} className={`border-t border-slate-700 ${getRiskColor(d.score)}`}>
                <td className="px-4 py-2 font-mono text-xs">{d.id.substring(0, 8)}</td>
                <td className="px-4 py-2 font-bold">{(d.score * 100).toFixed(0)}%</td>
                <td className="px-4 py-2 capitalize">{d.decision}</td>
                <td className="px-4 py-2 capitalize">{d.risk_level}</td>
                <td className="px-4 py-2">{d.update_count || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
