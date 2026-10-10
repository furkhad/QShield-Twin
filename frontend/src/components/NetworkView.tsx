import React, { useEffect, useRef, useState } from 'react'
import useWebSocket from '../hooks/useWebSocket'

type Node = {
  device_id: string
  name?: string
  x: number
  y: number
  battery?: number
  trust_score?: number
  latency_ms?: number
  packets_sent?: number
  packets_received?: number
}

type Link = [string, string]

type PacketAnim = {
  id: string
  src: string
  dst: string
  t0: number
  duration: number
}

export default function NetworkView() {
  const [nodes, setNodes] = useState<Record<string, Node>>({})
  const [links, setLinks] = useState<Link[]>([])
  const [packets, setPackets] = useState<PacketAnim[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  // pan/zoom
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [scale, setScale] = useState(1)
  const dragging = useRef<{ down: boolean; x: number; y: number }>({ down: false, x: 0, y: 0 })

  // playback/history
  const [history, setHistory] = useState<any[]>([])
  const [playing, setPlaying] = useState(true)
  const [playIndex, setPlayIndex] = useState<number | null>(null)

  useWebSocket((msg) => {
    // snapshot message
    if (msg && msg.devices) {
      const next: Record<string, Node> = {}
      for (const d of msg.devices) {
        next[d.device_id] = {
          device_id: d.device_id,
          name: d.name,
          x: d.x || 0,
          y: d.y || 0,
          battery: d.battery,
          trust_score: d.trust_score,
          latency_ms: d.latency_ms,
          packets_sent: d.packets_sent,
          packets_received: d.packets_received,
        }
      }
      setNodes(next)
      if (msg.links) setLinks(msg.links)
      // append to history buffer for playback (keep last 200)
      setHistory((h) => {
        const nh = [...h, msg]
        return nh.slice(-200)
      })
      if (playIndex === null) setPlayIndex(history.length + 0)
    }

    // packet event
    if (msg && msg.type === 'packet') {
      const id = `${msg.src}-${msg.dst}-${Date.now()}`
      const duration = (msg.latency_ms || 100) / 1000
      setPackets((p) => [...p, { id, src: msg.src, dst: msg.dst, t0: performance.now(), duration }])
      // auto-prune after duration
      setTimeout(() => setPackets((p) => p.filter((x) => x.id !== id)), (duration + 0.2) * 1000)
    }
  })

  // animation frame for packet progress
  const [, tick] = useState(0)
  useEffect(() => {
    let raf = 0
    const loop = () => {
      tick((t) => t + 1)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [])

  // draw onto canvas when node count is large for performance
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const draw = () => {
      const allNodes = Object.values(nodes)
      const w = canvas.width
      const h = canvas.height
      ctx.clearRect(0, 0, w, h)
      // draw links
      ctx.strokeStyle = 'rgba(59,130,246,0.4)'
      ctx.lineWidth = 1
      for (const ln of links) {
        const a = nodes[ln[0]]
        const b = nodes[ln[1]]
        if (!a || !b) continue
        const x1 = a.x * scale + offset.x
        const y1 = a.y * scale + offset.y
        const x2 = b.x * scale + offset.x
        const y2 = b.y * scale + offset.y
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
      }

      // draw nodes
      for (const n of allNodes) {
        const x = n.x * scale + offset.x
        const y = n.y * scale + offset.y
        ctx.beginPath()
        ctx.fillStyle = '#22c55e'
        ctx.arc(x, y, Math.max(2, 4 * Math.max(0.6, scale)), 0, Math.PI * 2)
        ctx.fill()
      }

      // draw packets
      for (const p of packets) {
        const a = nodes[p.src]
        const b = nodes[p.dst]
        if (!a || !b) continue
        const elapsed = (performance.now() - p.t0) / 1000
        const t = Math.min(1, elapsed / Math.max(0.001, p.duration))
        const x = (a.x + (b.x - a.x) * t) * scale + offset.x
        const y = (a.y + (b.y - a.y) * t) * scale + offset.y
        ctx.beginPath()
        ctx.fillStyle = '#f97316'
        ctx.arc(x, y, Math.max(2, 3 * Math.max(0.6, scale)), 0, Math.PI * 2)
        ctx.fill()
      }
      requestAnimationFrame(draw)
    }
    requestAnimationFrame(draw)
    return () => {
      // no-op; next render will clear
    }
  }, [nodes, links, packets, scale, offset])

  // dashboard metrics polling
  const [metrics, setMetrics] = useState<any>(null)
  useEffect(() => {
    let id = 0
    async function poll() {
      try {
        const res = await fetch('/api/v1/statistics')
        const json = await res.json()
        setMetrics(json.data)
      } catch (err) {
        // ignore
      }
    }
    poll()
    id = window.setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [])

  // snapshot history metadata
  const [historyMeta, setHistoryMeta] = useState<any[]>([])
  async function fetchHistoryMeta() {
    try {
      const res = await fetch('/api/v1/network/history')
      const json = await res.json()
      setHistoryMeta(json.data.items || [])
    } catch (err) {
      console.error(err)
    }
  }
  useEffect(() => {
    fetchHistoryMeta()
  }, [])

  async function loadHistoryItem(index: number) {
    try {
      const res = await fetch(`/api/v1/network/history/${index}`)
      const json = await res.json()
      const item = json.data.item
      if (!item) return
      if (item.kind === 'snapshot') {
        const s = item.snapshot
        const next: Record<string, Node> = {}
        for (const d of s.devices) {
          next[d.device_id] = {
            device_id: d.device_id,
            name: d.name,
            x: d.x || 0,
            y: d.y || 0,
            battery: d.battery,
            trust_score: d.trust_score,
            latency_ms: d.latency_ms,
            packets_sent: d.packets_sent,
            packets_received: d.packets_received,
          }
        }
        setNodes(next)
        if (s.links) setLinks(s.links)
      } else if (item.kind === 'packet') {
        // trigger a packet animation
        const ev = item.event
        const id = `${ev.src}-${ev.dst}-${Date.now()}`
        const duration = (ev.latency_ms || 100) / 1000
        setPackets((p) => [...p, { id, src: ev.src, dst: ev.dst, t0: performance.now(), duration }])
        setTimeout(() => setPackets((p) => p.filter((x) => x.id !== id)), (duration + 0.2) * 1000)
      }
    } catch (err) {
      console.error(err)
    }
  }

  // playback loop (replay from history when paused)
  useEffect(() => {
    if (!playing) return
    let id = 0
    id = window.setInterval(() => {
      setHistory((h) => {
        if (h.length === 0) return h
        const idx = playIndex === null ? h.length - 1 : Math.min(h.length - 1, (playIndex + 1) % h.length)
        const item = h[idx]
        if (item) {
          // apply snapshot
          const next: Record<string, Node> = {}
          for (const d of item.devices) {
            next[d.device_id] = {
              device_id: d.device_id,
              name: d.name,
              x: d.x || 0,
              y: d.y || 0,
              battery: d.battery,
              trust_score: d.trust_score,
              latency_ms: d.latency_ms,
              packets_sent: d.packets_sent,
              packets_received: d.packets_received,
            }
          }
          setNodes(next)
          if (item.links) setLinks(item.links)
        }
        setPlayIndex(idx)
        return h
      })
    }, 500)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, playIndex])

  const renderLinks = () => {
    return links.map((ln) => {
      const a = nodes[ln[0]]
      const b = nodes[ln[1]]
      if (!a || !b) return null
      const x1 = a.x * scale + offset.x
      const y1 = a.y * scale + offset.y
      const x2 = b.x * scale + offset.x
      const y2 = b.y * scale + offset.y
      return <line key={`${ln[0]}-${ln[1]}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#3b82f6" strokeWidth={1} opacity={0.5} />
    })
  }

  const renderNodes = () => {
    return Object.values(nodes).map((n) => {
      const x = n.x * scale + offset.x
      const y = n.y * scale + offset.y
      return (
        <g key={n.device_id} transform={`translate(${x}, ${y})`}>
          <circle r={8 * Math.max(0.6, scale)} fill={selected === n.device_id ? '#f97316' : '#22c55e'} onClick={() => setSelected(n.device_id)} />
          <text x={12} y={4} fontSize={12} fill="#cbd5e1">
            {n.name || n.device_id.slice(0, 6)}
          </text>
        </g>
      )
    })
  }

  const renderPackets = () => {
    return packets.map((p) => {
      const a = nodes[p.src]
      const b = nodes[p.dst]
      if (!a || !b) return null
      const elapsed = (performance.now() - p.t0) / 1000
      const t = Math.min(1, elapsed / Math.max(0.001, p.duration))
      const x = (a.x + (b.x - a.x) * t) * scale + offset.x
      const y = (a.y + (b.y - a.y) * t) * scale + offset.y
      return <circle key={p.id} cx={x} cy={y} r={4 * Math.max(0.6, scale)} fill="#f97316" opacity={0.9} />
    })
  }

  const selectedNode = selected ? nodes[selected] : null

  // handlers for pan/zoom
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return

    const onWheel = (ev: WheelEvent) => {
      ev.preventDefault()
      const delta = ev.deltaY < 0 ? 1.1 : 0.9
      const rect = svg.getBoundingClientRect()
      const mx = (ev.clientX - rect.left - offset.x) / scale
      const my = (ev.clientY - rect.top - offset.y) / scale
      const newScale = Math.max(0.2, Math.min(5, scale * delta))
      const nx = ev.clientX - rect.left - mx * newScale
      const ny = ev.clientY - rect.top - my * newScale
      setScale(newScale)
      setOffset({ x: nx, y: ny })
    }

    const onMouseDown = (ev: MouseEvent) => {
      dragging.current = { down: true, x: ev.clientX, y: ev.clientY }
    }
    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current.down) return
      const dx = ev.clientX - dragging.current.x
      const dy = ev.clientY - dragging.current.y
      dragging.current.x = ev.clientX
      dragging.current.y = ev.clientY
      setOffset((s) => ({ x: s.x + dx, y: s.y + dy }))
    }
    const onMouseUp = () => {
      dragging.current.down = false
    }

    svg.addEventListener('wheel', onWheel, { passive: false })
    svg.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      svg.removeEventListener('wheel', onWheel as any)
      svg.removeEventListener('mousedown', onMouseDown as any)
      window.removeEventListener('mousemove', onMouseMove as any)
      window.removeEventListener('mouseup', onMouseUp as any)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scale, offset])

  return (
    <div className="flex gap-4">
      <div className="flex-1">
        <div className="mb-2 flex items-center gap-2">
          <button onClick={() => setPlaying((p) => !p)} className="px-2 py-1 bg-slate-700 rounded">
            {playing ? 'Pause' : 'Play'}
          </button>
          <button
            onClick={() => {
              setPlaying(false)
              // step forward one history frame
              setPlayIndex((i) => (i === null ? Math.max(0, history.length - 1) : Math.min(history.length - 1, i + 1)))
            }}
            className="px-2 py-1 bg-slate-700 rounded"
          >
            Step →
          </button>
          <button
            onClick={() => {
              setPlaying(false)
              setPlayIndex((i) => (i === null ? Math.max(0, history.length - 1) : Math.max(0, i - 1)))
            }}
            className="px-2 py-1 bg-slate-700 rounded"
          >
            ← Step
          </button>
          <div className="ml-4 text-sm text-gray-300">Frames: {history.length}</div>
          <button
            className="px-2 py-1 bg-slate-700 rounded ml-2"
            onClick={() => {
              // compute bounding box and fit
              const vals = Object.values(nodes)
              if (vals.length === 0) return
              let minX = Infinity
              let minY = Infinity
              let maxX = -Infinity
              let maxY = -Infinity
              for (const n of vals) {
                minX = Math.min(minX, n.x)
                minY = Math.min(minY, n.y)
                maxX = Math.max(maxX, n.x)
                maxY = Math.max(maxY, n.y)
              }
              const width = maxX - minX || 1
              const height = maxY - minY || 1
              const viewW = 800
              const viewH = 600
              const newScale = Math.min(viewW / (width * 1.2), viewH / (height * 1.2))
              const nx = (viewW - (minX + maxX) * newScale) / 2
              const ny = (viewH - (minY + maxY) * newScale) / 2
              setScale(Math.max(0.1, Math.min(5, newScale)))
              setOffset({ x: nx, y: ny })
            }}
          >
            Zoom to Fit
          </button>
        </div>

        {/* Use canvas when node count is large */}
        {Object.keys(nodes).length > 600 ? (
          <canvas ref={canvasRef} width={800} height={600} className="bg-slate-900 rounded shadow-lg w-full h-[600px]" />
        ) : (
          <svg ref={svgRef} viewBox="0 0 800 600" className="bg-slate-900 rounded shadow-lg w-full h-[600px]">
            <defs></defs>
            {renderLinks()}
            {renderPackets()}
            {renderNodes()}
          </svg>
        )}
      </div>

      <div className="w-64 p-4 bg-slate-800 rounded">
        <h3 className="font-semibold mb-2">Simulation</h3>
        <div className="mb-4">
          <div>Nodes: {Object.keys(nodes).length}</div>
          <div>Links: {links.length}</div>
          {metrics && (
            <>
              <div>Avg latency: {metrics.avg_latency?.toFixed(2)}</div>
              <div>Packets sent: {metrics.packets_sent}</div>
              <div>Packets recv: {metrics.packets_received}</div>
            </>
          )}
        </div>

        <h4 className="font-medium">Selected</h4>
        {selectedNode ? (
          <div className="text-sm mt-2">
            <div>ID: {selectedNode.device_id}</div>
            <div>Name: {selectedNode.name}</div>
            <div>Trust: {selectedNode.trust_score ?? 0}</div>
            <div>Battery: {selectedNode.battery ?? 0}%</div>
            <div>Latency: {selectedNode.latency_ms ?? 0} ms</div>
            <div>Packets Sent: {selectedNode.packets_sent ?? 0}</div>
            <div>Packets Recv: {selectedNode.packets_received ?? 0}</div>
          </div>
        ) : (
          <div className="text-sm text-gray-400 mt-2">Select a node to see details</div>
        )}

        <div className="mt-4">
          <h4 className="font-medium">Snapshot History</h4>
          <div className="max-h-40 overflow-auto text-sm mt-2">
            {historyMeta.map((h) => (
              <div key={h.index} className="flex items-center justify-between py-1">
                <div>{h.index}: {h.kind} @{h.time}</div>
                <div className="flex gap-2">
                  <button onClick={() => loadHistoryItem(h.index)} className="px-2 py-0.5 bg-slate-700 rounded text-xs">Load</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
