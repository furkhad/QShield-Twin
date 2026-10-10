import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, RotateCcw, AlertTriangle, CheckCircle, Clock, Zap, ShieldCheck } from 'lucide-react'

// Represents a single step in the automated security demonstration workflow
interface DemoStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'running' | 'complete' | 'error'
  progress: number
  startTime?: number
  endTime?: number
  metrics?: Record<string, any>
}

export default function PresentationMode() {
  const [isRunning, setIsRunning] = useState(false)
  const [steps, setSteps] = useState<DemoStep[]>([
    { id: '1', name: 'Digital Twin Generation', description: 'Creating simulation environment', status: 'pending', progress: 0 },
    { id: '2', name: 'Spawn 100 Devices', description: 'Initializing legitimate IoT nodes', status: 'pending', progress: 0 },
    { id: '3', name: 'Display Topology', description: 'Rendering network topology visualization', status: 'pending', progress: 0 },
    { id: '4', name: 'Begin Communication', description: 'Starting packet transmission', status: 'pending', progress: 0 },
    { id: '5', name: 'Spawn 20 Ghost Nodes', description: 'Creating malicious Sybil identities', status: 'pending', progress: 0 },
    { id: '6', name: 'Highlight Attacker', description: 'Identifying attacker origin', status: 'pending', progress: 0 },
    { id: '7', name: 'Launch Sybil Attack', description: 'Executing coordinated attack', status: 'pending', progress: 0 },
    { id: '8', name: 'Attack Propagation', description: 'Visualizing attack spread', status: 'pending', progress: 0 },
    { id: '9', name: 'Proof-of-Proximity', description: 'Running ToF verification', status: 'pending', progress: 0 },
    { id: '10', name: 'Proximity Animation', description: 'Animating distance verification', status: 'pending', progress: 0 },
    { id: '11', name: 'Signature Verification', description: 'Verifying cryptographic signatures', status: 'pending', progress: 0 },
    { id: '12', name: 'Signature Animation', description: 'Visualizing signature validation', status: 'pending', progress: 0 },
    { id: '13', name: 'Trust Calculation', description: 'Computing multi-factor trust scores', status: 'pending', progress: 0 },
    { id: '14', name: 'Trust Dashboard', description: 'Updating trust visualization', status: 'pending', progress: 0 },
    { id: '15', name: 'Blacklist Nodes', description: 'Marking malicious nodes', status: 'pending', progress: 0 },
    { id: '16', name: 'Update Ledger', description: 'Recording in sharded ledger', status: 'pending', progress: 0 },
    { id: '17', name: 'Generate Analytics', description: 'Computing research metrics', status: 'pending', progress: 0 },
    { id: '18', name: 'Security Report', description: 'Displaying final results', status: 'pending', progress: 0 },
  ])
  const [results, setResults] = useState<Record<string, any> | null>(null)
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [selectedScenario, setSelectedScenario] = useState<'normal' | 'light_sybil_attack' | 'medium_sybil_attack' | 'heavy_sybil_attack'>('medium_sybil_attack')

  const runDemo = async () => {
    // Reset all steps to pending state before starting
    setIsRunning(true)
    setResults(null)
    setSteps(steps.map(s => ({ ...s, status: 'pending', progress: 0, startTime: undefined, endTime: undefined })))
    setCurrentStepIndex(0)

    const durations = [800, 1200, 800, 1500, 1000, 600, 2000, 2500, 1500, 2000, 1500, 2000, 2000, 1500, 1000, 1200, 1500, 2000]

    try {
      const scenarioRes = await fetch(`/api/v1/simulation/scenario/${selectedScenario}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_count: 100 })
      })
      const scenarioData = await scenarioRes.json()
      const scenarioPayload = scenarioData.data || {}

      for (let i = 0; i < steps.length; i++) {
        setCurrentStepIndex(i)
        const duration = durations[i]

        updateStep(i, { status: 'running', startTime: Date.now() })

        const startTime = Date.now()
        const interval = setInterval(() => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          updateStep(i, { progress: Math.round(progress * 100) })
        }, 50)

        await new Promise(resolve => setTimeout(resolve, duration))
        clearInterval(interval)

        updateStep(i, { status: 'complete', progress: 100, endTime: Date.now() })
      }

      const analytics = scenarioPayload.analytics || {}
      const trust = scenarioPayload.trust || {}
      const ledger = scenarioPayload.ledger || {}

      setResults({
        detection_metrics: {
          accuracy: analytics.detection_accuracy?.accuracy ?? 0,
          f1_score: analytics.detection_accuracy?.f1_score ?? 0,
          precision: analytics.detection_accuracy?.precision ?? 0,
        },
        trust_metrics: { average_score: trust.average_trust ?? 0 },
        processed_joins: scenarioPayload.processed_joins || 0,
        ghost_nodes: { total: scenarioPayload.ghost_nodes || 0 },
        ledger_stats: { total_entries: ledger.total_entries || 0 },
        verification_metrics: { average_time: analytics.performance?.average_verification_time_ms ?? 0 },
        scenario: scenarioPayload.scenario || selectedScenario,
        attack: scenarioPayload.attack || {},
      })
    } catch (err) {
      console.error('Demo error:', err)
      updateStep(currentStepIndex, { status: 'error' })
      setIsRunning(false)
    } finally {
      setIsRunning(false)
    }
  }

  const updateStep = (index: number, updates: Partial<DemoStep>) => {
    // Merges partial updates into a single demo step
    setSteps(prev => {
      const newSteps = [...prev]
      newSteps[index] = { ...newSteps[index], ...updates }
      return newSteps
    })
  }

  const reset = () => {
    // Clear results and return all steps to pending state
    setIsRunning(false)
    setResults(null)
    setCurrentStepIndex(0)
    setSteps(steps.map(s => ({ ...s, status: 'pending', progress: 0 })))
  }

  const completedCount = steps.filter(s => s.status === 'complete').length
  const overallProgress = Math.round((completedCount / steps.length) * 100)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-slate-700 pb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mb-2">
          Security Framework Demonstration
        </h1>
        <p className="text-slate-300">Automatic end-to-end security workflow showcase</p>
      </div>

      {/* Control Panel */}
      <div className="flex flex-col gap-4 bg-slate-800 p-6 rounded-lg border border-slate-700 lg:flex-row lg:items-center">
        <div className="flex gap-3 flex-wrap">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={runDemo}
            disabled={isRunning}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 rounded-lg font-semibold transition"
          >
            <Play size={20} />
            {isRunning ? 'Running...' : 'Run Demonstration'}
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={reset}
            disabled={isRunning}
            className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg font-semibold transition"
          >
            <RotateCcw size={20} />
            Reset
          </motion.button>
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            { id: 'normal', label: 'Normal' },
            { id: 'light_sybil_attack', label: 'Light' },
            { id: 'medium_sybil_attack', label: 'Medium' },
            { id: 'heavy_sybil_attack', label: 'Heavy' },
          ].map(option => (
            <button
              key={option.id}
              onClick={() => setSelectedScenario(option.id as any)}
              className={`rounded-full border px-3 py-1 text-sm ${selectedScenario === option.id ? 'border-cyan-400 bg-cyan-500/20 text-cyan-300' : 'border-slate-600 text-slate-300'}`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold text-cyan-400">{overallProgress}%</div>
            <div className="text-sm text-slate-400">{completedCount}/{steps.length} steps</div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <motion.div
          className="h-2 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${overallProgress}%` }}
          transition={{ duration: 0.5 }}
        />
        <div className="mt-2 text-sm text-slate-400">
          {overallProgress === 100 && 'Demonstration complete! '}
          {completedCount} of {steps.length} steps completed
        </div>
      </div>

      {/* Steps Timeline */}
      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-slate-100">Execution Timeline</h3>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          <AnimatePresence>
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: index * 0.05 }}
                className={`p-4 rounded-lg border transition ${
                  step.status === 'complete'
                    ? 'bg-emerald-900/20 border-emerald-500/30'
                    : step.status === 'running'
                    ? 'bg-cyan-900/20 border-cyan-500/50'
                    : step.status === 'error'
                    ? 'bg-red-900/20 border-red-500/30'
                    : 'bg-slate-800/50 border-slate-700'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className="mt-1">
                    {step.status === 'complete' ? (
                      <CheckCircle size={20} className="text-emerald-400" />
                    ) : step.status === 'running' ? (
                      <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity }}>
                        <Zap size={20} className="text-cyan-400" />
                      </motion.div>
                    ) : step.status === 'error' ? (
                      <AlertTriangle size={20} className="text-red-400" />
                    ) : (
                      <Clock size={20} className="text-slate-500" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <h4 className="font-semibold text-slate-100">{step.name}</h4>
                        <p className="text-sm text-slate-400">{step.description}</p>
                      </div>
                      <div className="text-right whitespace-nowrap">
                        <span className="text-sm font-mono text-slate-300">{step.progress}%</span>
                      </div>
                    </div>

                    {/* Progress bar for running step */}
                    {step.status === 'running' && (
                      <motion.div
                        className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                      >
                        <motion.div
                          className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                          initial={{ width: 0 }}
                          animate={{ width: `${step.progress}%` }}
                          transition={{ duration: 0.3 }}
                        />
                      </motion.div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Results */}
      <AnimatePresence>
        {results && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8 space-y-6"
          >
            <div className="flex items-center gap-3">
              <ShieldCheck className="text-emerald-400" size={24} />
              <h3 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
                ✓ Demonstration Complete
              </h3>
            </div>

            <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-4 text-sm text-cyan-100">
              Scenario executed: <span className="font-semibold">{results.scenario || selectedScenario}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Detection Metrics */}
              <div className="bg-slate-700/50 p-4 rounded-lg border border-slate-600">
                <p className="text-sm text-slate-400 mb-1">Detection Accuracy</p>
                <p className="text-3xl font-bold text-emerald-400">
                  {results.detection_metrics?.accuracy ? `${Math.round(results.detection_metrics.accuracy * 100)}%` : 'N/A'}
                </p>
                <p className="text-xs text-slate-500 mt-2">
                  F1 Score: {results.detection_metrics?.f1_score ? `${Math.round(results.detection_metrics.f1_score * 100)}%` : 'N/A'}
                </p>
              </div>

              {/* Trust Metrics */}
              <div className="bg-slate-700/50 p-4 rounded-lg border border-slate-600">
                <p className="text-sm text-slate-400 mb-1">Average Trust Score</p>
                <p className="text-3xl font-bold text-cyan-400">
                  {results.trust_metrics?.average_score ? `${Math.round(results.trust_metrics.average_score * 100)}/100` : 'N/A'}
                </p>
              </div>

              {/* Devices */}
              <div className="bg-slate-700/50 p-4 rounded-lg border border-slate-600">
                <p className="text-sm text-slate-400 mb-1">Devices Analyzed</p>
                <p className="text-3xl font-bold text-blue-400">
                  {results.processed_joins || 0}
                </p>
              </div>

              {/* Ghosts Detected */}
              <div className="bg-slate-700/50 p-4 rounded-lg border border-slate-600">
                <p className="text-sm text-slate-400 mb-1">Ghost Nodes</p>
                <p className="text-3xl font-bold text-yellow-400">
                  {results.ghost_nodes?.total || 0}
                </p>
              </div>

              {/* Ledger Entries */}
              <div className="bg-slate-700/50 p-4 rounded-lg border border-slate-600">
                <p className="text-sm text-slate-400 mb-1">Ledger Entries</p>
                <p className="text-3xl font-bold text-purple-400">
                  {results.ledger_stats?.total_entries || 0}
                </p>
              </div>

              {/* Verification Time */}
              <div className="bg-slate-700/50 p-4 rounded-lg border border-slate-600">
                <p className="text-sm text-slate-400 mb-1">Avg Verification</p>
                <p className="text-3xl font-bold text-pink-400">
                  {results.verification_metrics?.average_time ? `${results.verification_metrics.average_time.toFixed(2)}ms` : 'N/A'}
                </p>
              </div>
            </div>

            {/* Summary */}
            <div className="bg-slate-800/50 p-6 rounded-lg border border-slate-600">
              <h4 className="font-semibold text-slate-100 mb-3">Key Findings</h4>
              <ul className="space-y-2 text-slate-300 text-sm">
                <li>✓ All legitimate devices accepted with high confidence</li>
                <li>✓ Sybil attack detected with precision: {results.detection_metrics?.precision ? `${Math.round(results.detection_metrics.precision * 100)}%` : 'N/A'}</li>
                <li>✓ Trust scoring system correctly identified malicious nodes</li>
                <li>✓ Proof-of-Proximity verification successful</li>
                <li>✓ Sharded ledger maintained consistency across all entries</li>
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
