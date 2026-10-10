import React, { useEffect, useState } from 'react'

// Security overview page — displays raw security status JSON from the API
export default function SecurityOverview() {
  const [status, setStatus] = useState<any>(null)

  useEffect(() => {
    // Fetches the raw security status once on mount
    async function load() {
      try {
        const res = await fetch('/api/v1/security/status')
        const j = await res.json()
        setStatus(j.data)
      } catch (err) {
        console.error(err)
      }
    }
    load()
  }, [])

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Security Overview</h2>
      <pre className="bg-slate-800 p-4 rounded">{JSON.stringify(status, null, 2)}</pre>
    </div>
  )
}
