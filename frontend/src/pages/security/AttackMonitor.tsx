import React, { useState, useEffect } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'

// Real-time attack monitor for launching and tracking Sybil (ghost node) attacks
export default function AttackMonitor() {
  const [attacks, setAttacks] = useState<any[]>([])
  const [ghosts, setGhosts] = useState<any[]>([])
  const [formData, setFormData] = useState({ attacker: 'attacker-1', count: 20, intensity: 1.0 })
  const { data: wsData } = useWebSocket()

  useEffect(() => {
    loadAttacks()
  }, [])

  useEffect(() => {
    // Refreshes attack/ghost lists when new security events arrive via WebSocket
    if (wsData?.type === 'security_event' && wsData?.payload?.type === 'attack_started') {
      loadAttacks()
    }
    if (wsData?.type === 'security_event' && wsData?.payload?.type === 'ghost_spawn') {
      loadGhosts()
    }
  }, [wsData])

  async function loadAttacks() {
    // Fetches the list of currently active attacks from the API
    try {
      const res = await fetch('/api/v1/security/attacks')
      const j = await res.json()
      if (j.data) {
        setAttacks(Object.entries(j.data).map(([id, data]: any) => ({ id, ...data })))
      }
    } catch (err) {
      console.error(err)
    }
  }

  async function loadGhosts() {
    // Fetches the list of detected ghost nodes from the API
    try {
      const res = await fetch('/api/v1/security/ghosts')
      const j = await res.json()
      if (j.data?.ghosts) {
        setGhosts(Object.values(j.data.ghosts))
      }
    } catch (err) {
      console.error(err)
    }
  }

  async function startAttack() {
    // Sends a request to the API to launch a new Sybil attack
    try {
      await fetch('/api/v1/security/attack/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      loadAttacks()
    } catch (err) {
      console.error(err)
    }
  }

  async function stopAttack(attacker: string) {
    // Requests the API to halt an ongoing attack from a given attacker
    try {
      await fetch('/api/v1/security/attack/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attacker }),
      })
      loadAttacks()
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-3xl font-bold">Attack Monitor (Ghost Node Detection)</h2>

      {/* Start Attack Form */}
      <div className="bg-slate-800 p-6 rounded space-y-4">
        <h3 className="text-xl font-semibold">Launch Sybil Attack</h3>
        <div className="grid grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Attacker ID"
            value={formData.attacker}
            onChange={(e) => setFormData({ ...formData, attacker: e.target.value })}
            className="bg-slate-700 px-3 py-2 rounded text-white"
          />
          <input
            type="number"
            placeholder="Ghost Count (10-250)"
            value={formData.count}
            onChange={(e) => setFormData({ ...formData, count: parseInt(e.target.value) })}
            className="bg-slate-700 px-3 py-2 rounded text-white"
          />
          <input
            type="number"
            step="0.1"
            placeholder="Intensity"
            value={formData.intensity}
            onChange={(e) => setFormData({ ...formData, intensity: parseFloat(e.target.value) })}
            className="bg-slate-700 px-3 py-2 rounded text-white"
          />
        </div>
        <button
          onClick={startAttack}
          className="bg-red-700 hover:bg-red-600 px-4 py-2 rounded font-semibold"
        >
          Start Attack
        </button>
      </div>

      {/* Active Attacks */}
      <div className="bg-slate-800 rounded">
        <h3 className="text-xl font-semibold px-6 py-4 border-b border-slate-700">Active Attacks</h3>
        <div className="space-y-3 p-6">
          {attacks.map((a) => (
            <div key={a.id} className="bg-slate-700 p-4 rounded flex justify-between items-center">
              <div>
                <div className="font-semibold">{a.id}</div>
                <div className="text-sm text-gray-400">
                  Ghosts: {a.ghost_count} | Intensity: {a.intensity} | Detected: {a.detected_count} (
                  {(a.detection_rate * 100).toFixed(1)}%)
                </div>
                <div className="text-sm text-gray-400">
                  Success Rate: {(a.success_rate * 100).toFixed(1)}%
                </div>
              </div>
              <button
                onClick={() => stopAttack(a.id)}
                className="bg-orange-700 hover:bg-orange-600 px-3 py-1 rounded text-sm"
              >
                Stop
              </button>
            </div>
          ))}
          {attacks.length === 0 && <p className="text-gray-400">No active attacks</p>}
        </div>
      </div>

      {/* Ghost Nodes Summary */}
      <div className="bg-slate-800 rounded">
        <h3 className="text-xl font-semibold px-6 py-4 border-b border-slate-700">
          Ghost Nodes ({ghosts.length})
        </h3>
        <div className="grid grid-cols-auto gap-2 p-6">
          {ghosts.slice(0, 20).map((g: any, i) => (
            <div key={i} className="bg-slate-700 px-3 py-1 rounded text-xs text-gray-300">
              {g.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
