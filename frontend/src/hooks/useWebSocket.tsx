import { useEffect, useRef, useState } from 'react'

type MessageHandler = (data: any) => void

export function useWebSocket(
  url: string = 'ws://localhost:8000/api/v1/ws/stream',
  onMessage?: MessageHandler,
) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<number | null>(null)
  const [data, setData] = useState<any>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let closed = false

    function connect() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        console.info('ws open')
      }

      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data)
          setData(payload)
          onMessage?.(payload)
        } catch (err) {
          console.warn('failed parse ws message', err)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (closed) return
        // try reconnect
        reconnectRef.current = window.setTimeout(() => connect(), 1500)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      closed = true
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current)
      }
      try {
        wsRef.current?.close()
      } catch {}
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])

  return { data, connected }
}

export default useWebSocket
