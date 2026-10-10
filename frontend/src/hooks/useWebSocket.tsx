import { useCallback, useEffect, useRef, useState } from 'react'
import { wsUrl } from '../lib/config'

export type WebSocketMessage = Record<string, any>
type MessageHandler = (data: WebSocketMessage) => void

export interface UseWebSocketOptions {
  /** Full WebSocket URL. Defaults to the configured stream endpoint. */
  url?: string
  /** Maximum reconnect attempts before giving up. Defaults to 10. */
  maxRetries?: number
  /** Base delay for exponential backoff in ms. Defaults to 500. */
  baseDelayMs?: number
}

export interface UseWebSocketResult {
  data: WebSocketMessage | null
  connected: boolean
  /** Attempts made since the last successful connection. */
  retries: number
  /** Manually re-open the connection (resets the retry counter). */
  reconnect: () => void
}

/**
 * WebSocket hook with controlled exponential backoff + jitter reconnection.
 *
 * - The message handler is stored in a ref so callers can pass an inline
 *   function without causing reconnects (no stale-closure / no reopen storms).
 * - All timers and sockets are cleaned up on unmount, so there are no handler
 *   or timer leaks.
 */
export function useWebSocket(
  onMessage?: MessageHandler,
  options: UseWebSocketOptions = {},
): UseWebSocketResult {
  const { url = wsUrl(), maxRetries = 10, baseDelayMs = 500 } = options

  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<number | null>(null)
  const handlerRef = useRef<MessageHandler | undefined>(onMessage)
  const closedByUserRef = useRef(false)
  const retriesRef = useRef(0)

  const [data, setData] = useState<WebSocketMessage | null>(null)
  const [connected, setConnected] = useState(false)
  const [retries, setRetries] = useState(0)

  // Keep the latest handler without triggering a reconnect.
  useEffect(() => {
    handlerRef.current = onMessage
  }, [onMessage])

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    clearTimer()
    closedByUserRef.current = false

    let ws: WebSocket
    try {
      ws = new WebSocket(url)
    } catch (err) {
      console.warn('Failed to create WebSocket', err)
      return
    }
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setRetries(0)
      setConnected(true)
    }

    ws.onmessage = (ev: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(ev.data) as WebSocketMessage
        setData(payload)
        handlerRef.current?.(payload)
      } catch (err) {
        console.warn('Failed to parse WebSocket message', err)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      if (closedByUserRef.current) return
      if (retriesRef.current >= maxRetries) {
        console.warn(`WebSocket giving up after ${maxRetries} reconnect attempts`)
        return
      }
      // Exponential backoff with full jitter, capped at 30s.
      const delay = Math.min(30_000, baseDelayMs * 2 ** retriesRef.current) * (0.5 + Math.random() * 0.5)
      retriesRef.current += 1
      setRetries(retriesRef.current)
      timerRef.current = window.setTimeout(connect, delay)
    }

    ws.onerror = () => {
      // The browser fires onclose after onerror; reconnection is handled there.
      ws.close()
    }
  }, [url, maxRetries, baseDelayMs, clearTimer])

  useEffect(() => {
    connect()
    return () => {
      closedByUserRef.current = true
      clearTimer()
      try {
        wsRef.current?.close()
      } catch {
        /* ignore */
      }
      wsRef.current = null
    }
  }, [connect, clearTimer])

  const reconnect = useCallback(() => {
    retriesRef.current = 0
    setRetries(0)
    try {
      wsRef.current?.close()
    } catch {
      /* ignore */
    }
    connect()
  }, [connect])

  return { data, connected, retries, reconnect }
}

export default useWebSocket
