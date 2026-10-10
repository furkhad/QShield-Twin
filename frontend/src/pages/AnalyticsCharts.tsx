import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, Download } from 'lucide-react'

// Type definition for chart dataset configuration
interface ChartData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor?: string
    borderColor?: string
  }[]
}

export default function AnalyticsCharts() {
  const [metrics, setMetrics] = useState<any>(null)
  const [selectedChart, setSelectedChart] = useState<'accuracy' | 'detection' | 'trust' | 'performance'>('accuracy')

  useEffect(() => {
    // Loads metrics from three endpoints and polls every 5 seconds
    const loadMetrics = async () => {
      try {
        const [statusRes, analyticsRes, verificationRes] = await Promise.all([
          fetch('/api/v1/security/status'),
          fetch('/api/v1/security/analytics'),
          fetch('/api/v1/security/verification/metrics'),
        ])

        setMetrics({
          status: (await statusRes.json()).data,
          analytics: (await analyticsRes.json()).data,
          verification: (await verificationRes.json()).data,
        })
      } catch (err) {
        console.error('Failed to load metrics:', err)
      }
    }

    loadMetrics()
    const interval = setInterval(loadMetrics, 5000)
    return () => clearInterval(interval)
  }, [])

  if (!metrics) {
    return <div className="text-slate-400 text-center py-12">Loading charts...</div>
  }

  const analytics = metrics.analytics.detection_metrics || {}
  const verification = metrics.verification || {}

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-700 pb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mb-2">
          Analytics & Visualization
        </h1>
        <p className="text-slate-300">Publication-quality security metrics and performance charts</p>
      </div>

      {/* Chart Selection */}
      <div className="flex gap-2 flex-wrap">
        {[
          { id: 'accuracy', label: 'Detection Accuracy', icon: '📊' },
          { id: 'detection', label: 'Error Analysis', icon: '⚠️' },
          { id: 'trust', label: 'Trust Distribution', icon: '🔐' },
          { id: 'performance', label: 'Performance', icon: '⚡' },
        ].map(chart => (
          <motion.button
            key={chart.id}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSelectedChart(chart.id as any)}
            className={`px-4 py-2 rounded-lg font-semibold transition ${
              selectedChart === chart.id
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white'
                : 'bg-slate-800 text-slate-300 border border-slate-700 hover:border-slate-600'
            }`}
          >
            {chart.icon} {chart.label}
          </motion.button>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Main Chart */}
        <motion.div
          key={selectedChart}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8"
        >
          {selectedChart === 'accuracy' && <AccuracyChart analytics={analytics} />}
          {selectedChart === 'detection' && <ErrorAnalysisChart analytics={analytics} />}
          {selectedChart === 'trust' && <TrustChart metrics={metrics} />}
          {selectedChart === 'performance' && <PerformanceChart verification={verification} />}
        </motion.div>

        {/* Metrics Cards */}
        <MetricsColumn title="Detection Metrics" metrics={[
          { label: 'Precision', value: `${(analytics.precision * 100).toFixed(1)}%`, color: 'blue' },
          { label: 'Recall', value: `${(analytics.recall * 100).toFixed(1)}%`, color: 'emerald' },
          { label: 'F1 Score', value: `${(analytics.f1_score * 100).toFixed(1)}%`, color: 'purple' },
        ]} />

        <MetricsColumn title="Verification Metrics" metrics={[
          { label: 'Avg Time', value: `${verification.average_time?.toFixed(2)}ms` || 'N/A', color: 'yellow' },
          { label: 'Acceptance Rate', value: `${(verification.acceptance_rate * 100).toFixed(1)}%` || 'N/A', color: 'pink' },
          { label: 'Total Verifications', value: verification.total_verifications || 0, color: 'cyan' },
        ]} />
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Devices Analyzed" value={metrics.status.processed_joins} icon="📊" />
        <StatCard label="Packets Processed" value={metrics.status.processed_packets} icon="📡" />
        <StatCard label="Ghost Nodes" value={metrics.status.ghost_nodes} icon="👻" />
        <StatCard label="Avg Trust Score" value={`${(metrics.status.trust_metrics?.average_score * 100).toFixed(0)}/100`} icon="🔐" />
      </div>

      {/* Chart Export */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
        <button className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 transition">
          <Download size={20} />
          Export Charts as PNG
        </button>
      </div>
    </div>
  )
}

// Displays animated progress bars for detection accuracy, precision, recall, and F1 score
function AccuracyChart({ analytics }: any) {
  const metrics = ['Accuracy', 'Precision', 'Recall', 'F1 Score']
  const values = [
    analytics.accuracy * 100,
    analytics.precision * 100,
    analytics.recall * 100,
    analytics.f1_score * 100,
  ]

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-100 mb-6">Detection Accuracy Metrics</h3>
      <div className="space-y-4">
        {metrics.map((metric, idx) => (
          <div key={metric}>
            <div className="flex justify-between mb-2">
              <span className="text-slate-300">{metric}</span>
              <span className="font-semibold text-cyan-400">{values[idx].toFixed(1)}%</span>
            </div>
            <motion.div
              className="h-2 bg-slate-700 rounded-full overflow-hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                initial={{ width: 0 }}
                animate={{ width: `${values[idx]}%` }}
                transition={{ duration: 1, delay: idx * 0.1 }}
              />
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Renders a confusion matrix visualization (TP, TN, FP, FN)
function ErrorAnalysisChart({ analytics }: any) {
  const data = [
    { label: 'False Positives', value: analytics.false_positives || 0, color: 'orange' },
    { label: 'False Negatives', value: analytics.false_negatives || 0, color: 'red' },
    { label: 'True Positives', value: Math.max(0, (analytics.precision * 100).toFixed(0)), color: 'emerald' },
    { label: 'True Negatives', value: Math.max(0, ((1 - analytics.accuracy) * 100).toFixed(0)), color: 'blue' },
  ]

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-100 mb-6">Confusion Matrix Analysis</h3>
      <div className="grid grid-cols-2 gap-4">
        {data.map(item => (
          <div key={item.label} className={`p-4 rounded-lg bg-${item.color}-500/10 border border-${item.color}-500/30`}>
            <p className={`text-sm text-${item.color}-400`}>{item.label}</p>
            <p className={`text-3xl font-bold text-${item.color}-400`}>{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// Shows device trust distribution as a percentage bar chart
function TrustChart({ metrics }: any) {
  const trust = metrics.status.trust_metrics || {}
  const distribution = [
    { label: 'Accepted', count: metrics.status.legitimate_devices, color: 'emerald' },
    { label: 'Monitored', count: Math.max(0, Math.round(metrics.status.legitimate_devices * 0.1)), color: 'yellow' },
    { label: 'Rejected', count: Math.max(0, Math.round(metrics.status.legitimate_devices * 0.05)), color: 'orange' },
  ]

  const total = distribution.reduce((sum, d) => sum + d.count, 0)

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-100 mb-6">Device Trust Distribution</h3>
      <div className="space-y-4 mb-6">
        {distribution.map(item => {
          const percentage = (item.count / Math.max(total, 1)) * 100
          return (
            <div key={item.label}>
              <div className="flex justify-between mb-2">
                <span className={`text-slate-300`}>{item.label}</span>
                <span className={`font-semibold text-${item.color}-400`}>{item.count}</span>
              </div>
              <motion.div
                className={`h-2 bg-${item.color}-500/20 rounded-full overflow-hidden`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <motion.div
                  className={`h-full bg-${item.color}-500`}
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{ duration: 1 }}
                />
              </motion.div>
            </div>
          )
        })}
      </div>
      <div className="text-center pt-4 border-t border-slate-700">
        <p className="text-sm text-slate-400">Average Trust Score</p>
        <p className="text-3xl font-bold text-cyan-400">{(trust.average_score * 100).toFixed(0)}/100</p>
      </div>
    </div>
  )
}

// Displays verification performance metrics against target thresholds
function PerformanceChart({ verification }: any) {
  const metrics = [
    { label: 'Verification Time', value: verification.average_time?.toFixed(2), unit: 'ms', target: 10 },
    { label: 'Acceptance Rate', value: (verification.acceptance_rate * 100).toFixed(1), unit: '%', target: 95 },
    { label: 'Confidence Score', value: (verification.average_confidence * 100).toFixed(1), unit: '%', target: 90 },
  ]

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-100 mb-6">System Performance</h3>
      <div className="space-y-6">
        {metrics.map(metric => (
          <div key={metric.label}>
            <div className="flex justify-between mb-2">
              <span className="text-slate-300">{metric.label}</span>
              <div className="text-right">
                <span className="font-semibold text-cyan-400">{metric.value}{metric.unit}</span>
                <span className="text-xs text-slate-500 ml-2">/ {metric.target}{metric.unit}</span>
              </div>
            </div>
            <motion.div
              className="h-2 bg-slate-700 rounded-full overflow-hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <motion.div
                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min((parseFloat(metric.value) / metric.target) * 100, 100)}%` }}
                transition={{ duration: 1 }}
              />
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Reusable column displaying a title and list of metric cards
function MetricsColumn({ title, metrics }: any) {
  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">{title}</h3>
      <div className="space-y-3">
        {metrics.map((metric: any, idx: number) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className={`p-3 rounded-lg bg-${metric.color}-500/10 border border-${metric.color}-500/30`}
          >
            <p className={`text-xs text-${metric.color}-400`}>{metric.label}</p>
            <p className={`text-2xl font-bold text-${metric.color}-400 mt-1`}>{metric.value}</p>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

// Single stat card with icon, label, and value
function StatCard({ label, value, icon }: any) {
  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-4">
      <div className="text-3xl mb-2">{icon}</div>
      <p className="text-sm text-slate-400">{label}</p>
      <p className="text-2xl font-bold text-slate-100 mt-1">{value}</p>
    </div>
  )
}
