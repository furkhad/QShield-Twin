import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Download, FileJson, FileText, BarChart3, FileImage, Loader } from 'lucide-react'
import { extractDetectionMetrics, extractSecurityCounters, extractVerification } from '../lib/metrics'

// Data structure for export payloads including security metrics and analytics
interface ExportData {
  timestamp: string
  security_status: any
  analytics: any
  verification_metrics: any
  research_summary?: any
}

export default function ExportSystem() {
  const [isLoading, setIsLoading] = useState(false)
  const [exportedFormats, setExportedFormats] = useState<string[]>([])

  const loadData = async (): Promise<ExportData | null> => {
    // Fetches fresh security, analytics, and verification metrics in parallel
    try {
      const [statusRes, analyticsRes, verificationRes] = await Promise.all([
        fetch('/api/v1/security/status'),
        fetch('/api/v1/security/analytics'),
        fetch('/api/v1/security/verification/metrics'),
      ])

      return {
        timestamp: new Date().toISOString(),
        security_status: (await statusRes.json()).data,
        analytics: (await analyticsRes.json()).data,
        verification_metrics: (await verificationRes.json()).data,
      }
    } catch (err) {
      console.error('Failed to load export data:', err)
      return null
    }
  }

  const exportJSON = async () => {
    // Serializes all security data to a pretty-printed JSON file
    setIsLoading(true)
    const data = await loadData()
    if (!data) {
      setIsLoading(false)
      return
    }

    const jsonStr = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    downloadFile(blob, `qshield-security-report-${Date.now()}.json`)
    setExportedFormats(prev => ['json', ...prev])
    setIsLoading(false)
  }

  const exportCSV = async () => {
    // Builds a multi-section CSV report of security metrics
    setIsLoading(true)
    const data = await loadData()
    if (!data) {
      setIsLoading(false)
      return
    }

    // Generate comprehensive CSV with multiple sections
    let csv = 'QShield Twin - Security Report\n'
    csv += `Generated: ${data.timestamp}\n\n`

    // Security Status Section
    const counters = extractSecurityCounters(data.security_status)
    csv += 'SECURITY STATUS\n'
    csv += 'Metric,Value\n'
    csv += `Processed Joins,${counters.processed_joins}\n`
    csv += `Processed Packets,${counters.processed_packets}\n`
    csv += `Legitimate Devices,${counters.legitimate_devices}\n`
    csv += `Ghost Nodes Detected,${counters.ghost_nodes}\n\n`

    // Analytics Section
    const detection = extractDetectionMetrics(data.analytics)
    csv += 'ANALYTICS METRICS\n'
    csv += 'Metric,Value\n'
    csv += `Precision,${(detection.precision * 100).toFixed(2)}%\n`
    csv += `Recall,${(detection.recall * 100).toFixed(2)}%\n`
    csv += `F1 Score,${(detection.f1_score * 100).toFixed(2)}%\n`
    csv += `Accuracy,${(detection.accuracy * 100).toFixed(2)}%\n`
    csv += `False-Positive Rate,${(detection.false_positive_rate * 100).toFixed(2)}%\n`
    csv += '\n'

    // Verification Metrics
    const verification = extractVerification(data.verification_metrics)
    csv += 'VERIFICATION METRICS\n'
    csv += 'Metric,Value\n'
    csv += `Total Verifications,${verification.total}\n`
    csv += `Acceptance Rate,${(verification.acceptanceRate * 100).toFixed(2)}%\n`
    csv += `Average Confidence,${(verification.avgConfidence * 100).toFixed(2)}%\n`
    csv += `Average Propagation Delay (ms),${verification.avgPropagationMs.toFixed(2)}\n`

    const blob = new Blob([csv], { type: 'text/csv' })
    downloadFile(blob, `qshield-security-report-${Date.now()}.csv`)
    setExportedFormats(prev => ['csv', ...prev])
    setIsLoading(false)
  }

  const exportPDFReport = async () => {
    // Generates a markdown research report (convertible to PDF via pandoc)
    setIsLoading(true)
    const data = await loadData()
    if (!data) {
      setIsLoading(false)
      return
    }

    // Generate markdown for PDF conversion
    let markdown = `# QShield Twin - Security Research Report\n\n`
    markdown += `**Generated:** ${new Date(data.timestamp).toLocaleString()}\n\n`

    markdown += `## Executive Summary\n`
    markdown += `This report documents the comprehensive security analysis conducted using the QShield Twin platform.\n\n`

    markdown += `## Security Status\n`
    const counters = extractSecurityCounters(data.security_status)
    markdown += `| Metric | Value |\n`
    markdown += `|--------|-------|\n`
    markdown += `| Processed Joins | ${counters.processed_joins} |\n`
    markdown += `| Processed Packets | ${counters.processed_packets} |\n`
    markdown += `| Legitimate Devices | ${counters.legitimate_devices} |\n`
    markdown += `| Ghost Nodes Detected | ${counters.ghost_nodes} |\n\n`

    markdown += `## Detection Accuracy\n`
    const detection = extractDetectionMetrics(data.analytics)
    markdown += `| Metric | Value |\n`
    markdown += `|--------|-------|\n`
    markdown += `| Precision | ${(detection.precision * 100).toFixed(2)}% |\n`
    markdown += `| Recall | ${(detection.recall * 100).toFixed(2)}% |\n`
    markdown += `| F1 Score | ${(detection.f1_score * 100).toFixed(2)}% |\n`
    markdown += `| Accuracy | ${(detection.accuracy * 100).toFixed(2)}% |\n`
    markdown += `| False-Positive Rate | ${(detection.false_positive_rate * 100).toFixed(2)}% |\n\n`

    markdown += `## Verification Performance\n`
    const verification = extractVerification(data.verification_metrics)
    markdown += `| Metric | Value |\n`
    markdown += `|--------|-------|\n`
    markdown += `| Total Verifications | ${verification.total} |\n`
    markdown += `| Acceptance Rate | ${(verification.acceptanceRate * 100).toFixed(2)}% |\n`
    markdown += `| Average Confidence | ${(verification.avgConfidence * 100).toFixed(2)}% |\n`
    markdown += `| Average Propagation Delay | ${verification.avgPropagationMs.toFixed(2)}ms |\n\n`

    markdown += `## Data Source & Limitations\n`
    markdown += `All values above are produced by the QShield Twin simulation using synthetic\n`
    markdown += `ground-truth labels. They characterise the simulator, not validated real-world\n`
    markdown += `security, proximity, or cryptographic guarantees.\n\n`

    markdown += `## Conclusion\n`
    markdown += `Within the simulated scenarios exercised, the platform reported the detection\n`
    markdown += `and verification metrics above. These are simulation outputs and are not evidence\n`
    markdown += `of production effectiveness.\n\n`

    markdown += `---\n*This report was automatically generated by QShield Twin*\n`

    // Create downloadable markdown (can be converted to PDF with tools like pandoc)
    const blob = new Blob([markdown], { type: 'text/markdown' })
    downloadFile(blob, `qshield-security-report-${Date.now()}.md`)
    setExportedFormats(prev => ['pdf', ...prev])
    setIsLoading(false)
  }

  const downloadFile = (blob: Blob, filename: string) => {
    // Triggers a browser download for the given blob and filename
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-700 pb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mb-2">
          Export & Reports
        </h1>
        <p className="text-slate-300">Download security data and research findings in multiple formats</p>
      </div>

      {/* Export Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <ExportCard
          icon={<FileJson size={32} />}
          title="JSON Export"
          description="Complete security data and metrics in JSON format"
          onClick={exportJSON}
          isLoading={isLoading}
          isExported={exportedFormats.includes('json')}
        />

        <ExportCard
          icon={<FileText size={32} />}
          title="CSV Export"
          description="Tabular format for analysis in spreadsheet applications"
          onClick={exportCSV}
          isLoading={isLoading}
          isExported={exportedFormats.includes('csv')}
        />

        <ExportCard
          icon={<FileText size={32} />}
          title="PDF Report"
          description="Professional research report with visualizations"
          onClick={exportPDFReport}
          isLoading={isLoading}
          isExported={exportedFormats.includes('pdf')}
        />
      </div>

      {/* Advanced Export Options */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8">
        <h2 className="text-xl font-bold text-slate-100 mb-6 flex items-center gap-2">
          <BarChart3 size={24} className="text-cyan-400" />
          Advanced Export Options
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <button className="p-6 rounded-lg border border-slate-600 hover:border-cyan-500 hover:bg-slate-700/50 transition text-left">
            <h3 className="font-semibold text-slate-100 mb-2 flex items-center gap-2">
              <BarChart3 size={20} />
              Analysis Graphs
            </h3>
            <p className="text-sm text-slate-400 mb-4">High-resolution charts for publications</p>
            <span className="text-xs text-cyan-400">PNG + SVG Formats</span>
          </button>

          <button className="p-6 rounded-lg border border-slate-600 hover:border-cyan-500 hover:bg-slate-700/50 transition text-left">
            <h3 className="font-semibold text-slate-100 mb-2">Dataset</h3>
            <p className="text-sm text-slate-400 mb-4">Raw simulation data for further analysis</p>
            <span className="text-xs text-cyan-400">Parquet + HDF5 Formats</span>
          </button>

          <button className="p-6 rounded-lg border border-slate-600 hover:border-cyan-500 hover:bg-slate-700/50 transition text-left">
            <h3 className="font-semibold text-slate-100 mb-2">Research Summary</h3>
            <p className="text-sm text-slate-400 mb-4">Academic paper with findings</p>
            <span className="text-xs text-cyan-400">LaTeX + PDF</span>
          </button>

          <button className="p-6 rounded-lg border border-slate-600 hover:border-cyan-500 hover:bg-slate-700/50 transition text-left">
            <h3 className="font-semibold text-slate-100 mb-2">Experiment Logs</h3>
            <p className="text-sm text-slate-400 mb-4">Complete simulation execution logs</p>
            <span className="text-xs text-cyan-400">Text + Compressed</span>
          </button>
        </div>
      </div>

      {/* Export History */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8">
        <h2 className="text-xl font-bold text-slate-100 mb-4">Export History</h2>

        {exportedFormats.length === 0 ? (
          <p className="text-slate-400 text-center py-8">No exports yet. Use the buttons above to create your first export.</p>
        ) : (
          <div className="space-y-2">
            {exportedFormats.map((format, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/30 border border-slate-600 rounded">
                <span className="text-slate-200">Export #{exportedFormats.length - idx} ({format.toUpperCase()})</span>
                <span className="text-xs text-slate-500">{new Date().toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Reusable card component for a single export format option
function ExportCard({ icon, title, description, onClick, isLoading, isExported }: any) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      disabled={isLoading}
      className="p-6 bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 hover:border-cyan-500 rounded-lg text-left transition group"
    >
      <div className={`mb-4 ${isExported ? 'text-emerald-400' : 'text-cyan-400 group-hover:text-cyan-300'}`}>
        {isLoading ? <Loader size={32} className="animate-spin" /> : icon}
      </div>
      <h3 className="font-semibold text-slate-100 mb-2">{title}</h3>
      <p className="text-sm text-slate-400 mb-4">{description}</p>
      <div className="flex items-center gap-2 text-sm">
        <Download size={16} className="opacity-0 group-hover:opacity-100 transition" />
        <span className="text-cyan-400">{isExported ? '✓ Exported' : 'Export Now'}</span>
      </div>
    </motion.button>
  )
}
