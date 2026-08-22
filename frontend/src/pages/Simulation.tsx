import React, { useEffect, useState } from 'react'
import NetworkView from '../components/NetworkView'

export default function Simulation() {
  const [topology, setTopology] = useState('random')

  useEffect(() => {
    // no-op
  }, [])

  async function applyTopology(t: string) {
    setTopology(t)
    try {
      await fetch('/api/v1/network/topology', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topology: t, params: {} }),
      })
    } catch (err) {
      console.error('failed apply topology', err)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Simulation</h2>
      <p className="text-gray-300">Configure and run digital twin simulations.</p>

      <div className="mt-4 mb-6 flex items-center gap-4">
        <label className="text-sm">Topology:</label>
        <select value={topology} onChange={(e) => applyTopology(e.target.value)} className="bg-slate-700 rounded p-1">
          <option value="random">Random</option>
          <option value="grid">Grid</option>
          <option value="cluster">Cluster</option>
          <option value="mesh">Mesh</option>
          <option value="star">Star</option>
        </select>
      </div>

      <div className="mb-4 flex gap-2">
        <button
          className="px-3 py-1 bg-slate-700 rounded"
          onClick={async () => {
            // bulk spawn 500 as a stress test
            await fetch('/api/v1/devices/bulk', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ count: 500, prefix: 'node' }) })
          }}
        >
          Bulk Spawn 500
        </button>
        <button
          className="px-3 py-1 bg-slate-700 rounded"
          onClick={async () => {
            await fetch('/api/v1/simulation/start', { method: 'POST' })
          }}
        >
          Start Simulation
        </button>
        <button
          className="px-3 py-1 bg-slate-700 rounded"
          onClick={async () => {
            await fetch('/api/v1/simulation/pause', { method: 'POST' })
          }}
        >
          Pause
        </button>
        <button
          className="px-3 py-1 bg-slate-700 rounded"
          onClick={async () => {
            await fetch('/api/v1/simulation/resume', { method: 'POST' })
          }}
        >
          Resume
        </button>
        <button
          className="px-3 py-1 bg-slate-700 rounded"
          onClick={async () => {
            await fetch('/api/v1/simulation/step', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ steps: 1 }) })
          }}
        >
          Step
        </button>
        <button
          className="px-3 py-1 bg-slate-700 rounded"
          onClick={async () => {
            // request server replay of last history
            await fetch('/api/v1/network/replay', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'start', speed: 2.0 }) })
          }}
        >
          Server Replay x2
        </button>
      </div>

      <NetworkView />
    </div>
  )
}
