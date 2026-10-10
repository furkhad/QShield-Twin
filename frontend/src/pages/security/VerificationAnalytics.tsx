import React, { useState, useEffect } from 'react'

export default function VerificationAnalytics() {
  const [verifications, setVerifications] = useState<any>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [exportFormat, setExportFormat] = useState('json')

  useEffect(() => {
    loadMetrics()
    const iv = setInterval(loadMetrics, 3000)
    return () => clearInterval(iv)
  }, [])

  async function loadMetrics() {
    try {
      const [verRes, anaRes] = await Promise.all([
        fetch('/api/v1/security/verification/metrics'),
        fetch('/api/v1/security/analytics'),
      ])
      const verData = await verRes.json()
      const anaData = await anaRes.json()
      setVerifications(verData.data)
      setAnalytics(anaData.data)
    } catch (err) {
      console.error(err)
    }
  }

  async function exportAnalytics(format: string) {
    try {
      const url =
        format === 'json'
          ? '/api/v1/security/analytics/export/json'
          : '/api/v1/security/analytics/export/csv'
      const res = await fetch(url)
      const data = await res.json()
      const content = format === 'json' ? data.data.json : data.data.csv

      // Download
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `security-analytics.${format}`
      a.click()
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-3xl font-bold">Verification & Analytics</h2>

      {/* Export Controls */}
      <div className="bg-slate-800 p-4 rounded space-x-2">
        <button
          onClick={() => exportAnalytics('json')}
          className="bg-blue-700 hover:bg-blue-600 px-4 py-2 rounded"
        >
          Export as JSON
        </button>
        <button
          onClick={() => exportAnalytics('csv')}
          className="bg-blue-700 hover:bg-blue-600 px-4 py-2 rounded"
        >
          Export as CSV
        </button>
      </div>

      {/* Verification Metrics */}
      {verifications && (
        <div className="bg-slate-800 p-6 rounded">
          <h3 className="text-xl font-semibold mb-4">Proof-of-Proximity Metrics</h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Total Verifications</div>
              <div className="text-2xl font-bold">{verifications.total_verifications}</div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Acceptance Rate</div>
              <div className="text-2xl font-bold">
                {(verifications.acceptance_rate * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Avg Confidence</div>
              <div className="text-2xl font-bold">
                {(verifications.average_confidence * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Avg ToF (ms)</div>
              <div className="text-2xl font-bold">
                {verifications.average_propagation_delay_ms.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detection Accuracy Metrics */}
      {analytics?.detection_accuracy && (
        <div className="bg-slate-800 p-6 rounded">
          <h3 className="text-xl font-semibold mb-4">Detection Accuracy</h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Precision</div>
              <div className="text-2xl font-bold">{(analytics.detection_accuracy.precision * 100).toFixed(1)}%</div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Recall</div>
              <div className="text-2xl font-bold">{(analytics.detection_accuracy.recall * 100).toFixed(1)}%</div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">F1 Score</div>
              <div className="text-2xl font-bold">{(analytics.detection_accuracy.f1_score * 100).toFixed(1)}%</div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Accuracy</div>
              <div className="text-2xl font-bold">{(analytics.detection_accuracy.accuracy * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}

      {/* Attack Defense Metrics */}
      {analytics?.attack_defense && (
        <div className="bg-slate-800 p-6 rounded">
          <h3 className="text-xl font-semibold mb-4">Attack / Defense Results</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Ghosts Spawned</div>
              <div className="text-2xl font-bold">{analytics.attack_defense.ghosts_spawned}</div>
            </div>
            <div className="bg-slate-700 p-4 rounded">
              <div className="text-sm text-gray-300">Ghosts Detected</div>
              <div className="text-2xl font-bold">{analytics.attack_defense.ghosts_detected}</div>
            </div>
            <div className="bg-green-900 p-4 rounded">
              <div className="text-sm text-gray-300">Defense Success Rate</div>
              <div className="text-2xl font-bold">
                {(analytics.attack_defense.defense_success_rate * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-red-900 p-4 rounded">
              <div className="text-sm text-gray-300">Attack Success Rate</div>
              <div className="text-2xl font-bold">
                {(analytics.attack_defense.attack_success_rate * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confusion Matrix */}
      {analytics?.confusion_matrix && (
        <div className="bg-slate-800 p-6 rounded">
          <h3 className="text-xl font-semibold mb-4">Confusion Matrix</h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-green-900 p-4 rounded">
              <div className="text-sm text-gray-300">True Positives</div>
              <div className="text-2xl font-bold">{analytics.confusion_matrix.true_positives}</div>
            </div>
            <div className="bg-red-900 p-4 rounded">
              <div className="text-sm text-gray-300">False Positives</div>
              <div className="text-2xl font-bold">{analytics.confusion_matrix.false_positives}</div>
            </div>
            <div className="bg-orange-900 p-4 rounded">
              <div className="text-sm text-gray-300">False Negatives</div>
              <div className="text-2xl font-bold">{analytics.confusion_matrix.false_negatives}</div>
            </div>
            <div className="bg-green-900 p-4 rounded">
              <div className="text-sm text-gray-300">True Negatives</div>
              <div className="text-2xl font-bold">{analytics.confusion_matrix.true_negatives}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
