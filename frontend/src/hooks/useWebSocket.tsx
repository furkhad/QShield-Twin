import { useEffect, useRef } from 'react'

type MessageHandler = (data: any) => void

export function useWebSocket(url: string, onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<number | null>(null)

  useEffect(() => {
    let closed = false

    function connect() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.info('ws open')
      }

      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data)
          onMessage(payload)
        } catch (err) {
          console.warn('failed parse ws message', err)
        }
      }

      ws.onclose = () => {
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
}

export default useWebSocket
