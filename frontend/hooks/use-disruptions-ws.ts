import { useEffect, useState, useRef } from "react"

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/disruptions"
const RECONNECT_DELAY_MS = 3000

export interface DisruptionEvent {
  type: string;
  event?: string;
  message?: string;
  channel?: string;
  [key: string]: any;
}

export function useDisruptionsWS(companyId: string = "default") {
  const [events, setEvents] = useState<DisruptionEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [status, setStatus] = useState<"connecting" | "connected" | "degraded" | "reconnecting">("connecting")
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let active = true

    const connect = () => {
      const url = `${WS_URL}/${companyId}`
      setStatus("connecting")
      console.log("Connecting to WS:", url)
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        if (!active) return
        setConnected(true)
        setStatus("connected")
        console.log("WS Connected")
      }

      ws.current.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data)
          if (data.type === "heartbeat") return
          if (data.type === "stream_degraded") {
            setStatus("degraded")
            console.warn("WS degraded:", data.message)
            return
          }

          console.log("WS Received:", data)
          setEvents((prev) => [data, ...prev])
        } catch (err) {
          console.error("WS Parse Error:", err)
        }
      }

      ws.current.onerror = () => {
        if (!active) return
        setStatus("reconnecting")
      }

      ws.current.onclose = () => {
        if (!active) return
        setConnected(false)
        setStatus("reconnecting")
        console.log("WS Disconnected; retrying...")
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    return () => {
      active = false
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
      ws.current?.close()
    }
  }, [companyId])

  return { events, connected, status }
}
