import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BarChart3, Download, Settings, Loader, AlertTriangle } from 'lucide-react'
import { apiUrl } from '../lib/config'

// Configuration parameters for a single experiment run.
interface ExperimentConfig {
  num_devices: number
  num_ghosts: number
  duration_seconds: number
  random_seed: number
}

// Results produced by the backend for a single scenario run. All values come
// from the server's analytics engine (simulation metrics), never from the UI.
interface ExperimentResult {
  config: ExperimentConfig
  scenario: string
  seed: number | null
  software_version: string | null
  data_source: string
  precision: number
  recall: number
  f1_score: number
  accuracy: number
  false_positive_rate: number
  false_positives: number
  false_negatives: number
  detection_time_ms: number
  average_trust: number
  attack_success_rate: number
  defense_success_rate: number
  ledger_growth_rate: number
}

interface ScenarioResponse {
  status: string
  message: string
  data?: {
    scenario?: string
    seed?: number | null
    software_version?: string
    analytics?: {
      confusion_matrix?: Record<string, number>
      detection_accuracy?: Record<string, number>
      performance?: Record<string, number>
      attack_defense?: Record<string, number>
      ledger?: Record<string, number>
      metric_source?: string
      run_metadata?: Record<string, unknown>
    }
  }
}

function scenarioFor(devices: number, ghosts: number): string {
  if (ghosts <= 0) return 'normal'
  const ratio = devices > 0 ? ghosts / devices : 1
  if (ratio <= 0.1) return 'light_sybil_attack'
  if (ratio <= 0.25) return 'medium_sybil_attack'
  return 'heavy_sybil_attack'
}

export default function ResearchMode() {
  const [config, setConfig] = useState<ExperimentConfig>({
    num_devices: 100,
    num_ghosts: 20,
    duration_seconds: 30,
    random_seed: 42,
  })

  const [experiments, setExperiments] = useState<ExperimentResult[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentExperiment, setCurrentExperiment] = useState(0)
  const [plannedRuns, setPlannedRuns] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const defaultConfigs = [
    { name: 'Small Scale', devices: 50, ghosts: 10 },
    { name: 'Medium Scale', devices: 100, ghosts: 20 },
    { name: 'Large Scale', devices: 250, ghosts: 50 },
    { name: 'Enterprise', devices: 500, ghosts: 100 },
  ]

  const handlePreset = (preset: (typeof defaultConfigs)[0]) => {
    setConfig((prev) => ({
      ...prev,
      num_devices: preset.devices,
      num_ghosts: preset.ghosts,
    }))
  }

  // Runs real scenarios against the backend. Each run uses a distinct, recorded
  // seed so results are reproducible and auditable. No metrics are fabricated.
  const runExperiments = async (count: number) => {
    setIsRunning(true)
    setExperiments([])
    setError(null)
    setCurrentExperiment(0)
    setPlannedRuns(count)
    setProgress(0)

    const results: ExperimentResult[] = []
    const scenario = scenarioFor(config.num_devices, config.num_ghosts)

    try {
      for (let i = 0; i < count; i++) {
        const seed = config.random_seed + i
        setCurrentExperiment(i + 1)

        const response = await fetch(apiUrl(`/simulation/scenario/${scenario}`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device_count: config.num_devices,
            ghost_count: config.num_ghosts,
            seed,
          }),
        })
        if (!response.ok) {
          throw new Error(`Backend returned HTTP ${response.status}`)
        }
        const body = (await response.json()) as ScenarioResponse
        if (body.status !== 'ok' || !body.data) {
          throw new Error(body.message || 'Scenario failed')
        }

        const analytics = body.data.analytics ?? {}
        const cm = analytics.confusion_matrix ?? {}
        const da = analytics.detection_accuracy ?? {}
        const perf = analytics.performance ?? {}
        const ad = analytics.attack_defense ?? {}
        const led = analytics.ledger ?? {}

        results.push({
          config: { ...config, random_seed: seed },
          scenario: body.data.scenario ?? scenario,
          seed: body.data.seed ?? seed,
          software_version: body.data.software_version ?? null,
          data_source: analytics.metric_source ?? 'simulation',
          precision: da.precision ?? 0,
          recall: da.recall ?? 0,
          f1_score: da.f1_score ?? 0,
          accuracy: da.accuracy ?? 0,
          false_positive_rate: da.false_positive_rate ?? 0,
          false_positives: cm.false_positives ?? 0,
          false_negatives: cm.false_negatives ?? 0,
          detection_time_ms: perf.average_verification_time_ms ?? 0,
          average_trust: perf.average_trust_score ?? 0,
          attack_success_rate: ad.attack_success_rate ?? 0,
          defense_success_rate: ad.defense_success_rate ?? 0,
          ledger_growth_rate: led.growth_rate_per_second ?? 0,
        })

        setProgress(Math.round(((i + 1) / count) * 100))
      }
      setExperiments(results)
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message}. Ensure the backend is running (default http://localhost:8000).`
          : 'Failed to run experiments',
      )
    } finally {
      setIsRunning(false)
    }
  }

  const getAverageMetrics = () => {
    if (experiments.length === 0) return null

    return {
      avg_precision: experiments.reduce((sum, e) => sum + e.precision, 0) / experiments.length,
      avg_recall: experiments.reduce((sum, e) => sum + e.recall, 0) / experiments.length,
      avg_f1: experiments.reduce((sum, e) => sum + e.f1_score, 0) / experiments.length,
      avg_accuracy: experiments.reduce((sum, e) => sum + e.accuracy, 0) / experiments.length,
      std_f1: calculateStdDev(experiments.map((e) => e.f1_score)),
      std_accuracy: calculateStdDev(experiments.map((e) => e.accuracy)),
      total_fp: experiments.reduce((sum, e) => sum + e.false_positives, 0),
      total_fn: experiments.reduce((sum, e) => sum + e.false_negatives, 0),
      avg_detection_time: experiments.reduce((sum, e) => sum + e.detection_time_ms, 0) / experiments.length,
      avg_defense_rate: experiments.reduce((sum, e) => sum + e.defense_success_rate, 0) / experiments.length,
      avg_ledger_growth: experiments.reduce((sum, e) => sum + e.ledger_growth_rate, 0) / experiments.length,
    }
  }

  const downloadResults = () => {
    const avg = getAverageMetrics()
    const data = {
      timestamp: new Date().toISOString(),
      data_source: avg ? 'simulation' : 'none',
      note:
        'Metrics are produced by the QShield Twin simulation backend (seeded scenarios). ' +
        'They are synthetic and must not be represented as real-world field performance.',
      configuration: config,
      experiments: experiments,
      average_metrics: avg,
      experiment_count: experiments.length,
    }

    const jsonStr = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `qshield-research-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const avg = getAverageMetrics()

  return (
    <div className="space-y-8">
      <div className="border-b border-slate-700 pb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mb-2">
          Research Mode
        </h1>
        <p className="text-slate-300">
          Run seeded scenarios against the live backend and inspect the resulting detection metrics.
        </p>
        <p className="mt-2 inline-flex items-center gap-2 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-1">
          <AlertTriangle size={14} />
          Metrics are simulation outputs (synthetic ground truth), not validated real-world performance.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8 space-y-6">
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Settings size={20} />
            Experiment Configuration
          </h2>

          <div className="space-y-2">
            <p className="text-sm text-slate-400 mb-3">Quick Presets</p>
            <div className="grid grid-cols-2 gap-2">
              {defaultConfigs.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => handlePreset(preset)}
                  className="px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-sm transition border border-slate-600 text-slate-300"
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <ConfigInput
              label="Number of Devices"
              value={config.num_devices}
              onChange={(v) => setConfig((prev) => ({ ...prev, num_devices: parseInt(v) || 1 }))}
              min={10}
              max={1000}
            />
            <ConfigInput
              label="Ghost Nodes"
              value={config.num_ghosts}
              onChange={(v) => setConfig((prev) => ({ ...prev, num_ghosts: parseInt(v) || 0 }))}
              min={0}
              max={1000}
            />
            <ConfigInput
              label="Duration (seconds)"
              value={config.duration_seconds}
              onChange={(v) => setConfig((prev) => ({ ...prev, duration_seconds: parseInt(v) || 1 }))}
              min={1}
              max={300}
            />
            <ConfigInput
              label="Random Seed"
              value={config.random_seed}
              onChange={(v) => setConfig((prev) => ({ ...prev, random_seed: parseInt(v) || 0 }))}
              min={0}
              max={999999}
            />
          </div>

          <div className="space-y-3 pt-4 border-t border-slate-700">
            <p className="text-sm text-slate-400">Run Experiments</p>
            <div className="grid grid-cols-2 gap-2">
              {[5, 10, 25, 50].map((count) => (
                <motion.button
                  key={count}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => runExperiments(count)}
                  disabled={isRunning}
                  className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 disabled:opacity-50 rounded-lg font-semibold text-sm transition"
                >
                  {isRunning && count === plannedRuns ? (
                    <span className="flex items-center gap-1">
                      <Loader size={14} className="animate-spin" />
                      {currentExperiment}
                    </span>
                  ) : (
                    `Run ${count}`
                  )}
                </motion.button>
              ))}
            </div>
          </div>

          {isRunning && (
            <div className="space-y-2">
              <div className="text-sm text-slate-400">
                Experiment {currentExperiment} of {plannedRuns}
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/40 rounded-lg p-4 text-red-300 flex items-start gap-3">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <AnimatePresence>
            {avg && experiments.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8"
              >
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    <BarChart3 size={20} className="text-cyan-400" />
                    Averaged Results ({experiments.length} experiments)
                  </h3>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={downloadResults}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-semibold text-sm"
                  >
                    <Download size={16} />
                    Export JSON
                  </motion.button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <MetricCard label="Detection Accuracy" value={`${(avg.avg_accuracy * 100).toFixed(2)}%`} std={`±${(avg.std_accuracy * 100).toFixed(2)}%`} color="cyan" />
                  <MetricCard label="F1 Score" value={`${(avg.avg_f1 * 100).toFixed(2)}%`} std={`±${(avg.std_f1 * 100).toFixed(2)}%`} color="emerald" />
                  <MetricCard label="Precision" value={`${(avg.avg_precision * 100).toFixed(2)}%`} color="blue" />
                  <MetricCard label="Recall" value={`${(avg.avg_recall * 100).toFixed(2)}%`} color="purple" />
                  <MetricCard label="Avg Detection Time" value={`${avg.avg_detection_time.toFixed(2)}ms`} color="yellow" />
                  <MetricCard label="Defense Success" value={`${(avg.avg_defense_rate * 100).toFixed(2)}%`} color="pink" />
                </div>

                <div className="mt-6 pt-6 border-t border-slate-700 grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-slate-400 mb-1">Total False Positives</p>
                    <p className="text-2xl font-bold text-orange-400">{avg.total_fp}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-slate-400 mb-1">Total False Negatives</p>
                    <p className="text-2xl font-bold text-red-400">{avg.total_fn}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-slate-400 mb-1">Avg Ledger Growth</p>
                    <p className="text-2xl font-bold text-green-400">{avg.avg_ledger_growth.toFixed(1)}/s</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {experiments.length > 0 && (
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8 overflow-x-auto">
              <h3 className="text-xl font-bold text-slate-100 mb-4">Individual Results</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Exp</th>
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Seed</th>
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Accuracy</th>
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">F1 Score</th>
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Precision</th>
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Recall</th>
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Detection (ms)</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((exp, idx) => (
                    <tr key={idx} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                      <td className="py-3 px-4 text-slate-300 font-mono">#{idx + 1}</td>
                      <td className="py-3 px-4 text-slate-400 font-mono">{exp.seed}</td>
                      <td className="py-3 px-4 text-cyan-400">{(exp.accuracy * 100).toFixed(1)}%</td>
                      <td className="py-3 px-4 text-emerald-400">{(exp.f1_score * 100).toFixed(1)}%</td>
                      <td className="py-3 px-4 text-blue-400">{(exp.precision * 100).toFixed(1)}%</td>
                      <td className="py-3 px-4 text-purple-400">{(exp.recall * 100).toFixed(1)}%</td>
                      <td className="py-3 px-4 text-yellow-400">{exp.detection_time_ms.toFixed(2)}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {experiments.length === 0 && !isRunning && (
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-12 text-center">
              <BarChart3 size={48} className="mx-auto mb-4 text-slate-600" />
              <p className="text-slate-400 mb-2">No experiments run yet</p>
              <p className="text-slate-500 text-sm">
                Configure parameters and click "Run" to execute seeded scenarios against the backend.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ConfigInputProps {
  label: string
  value: number
  onChange: (value: string) => void
  min?: number
  max?: number
  step?: number
}

function ConfigInput({ label, value, onChange, min, max, step = 1 }: ConfigInputProps) {
  return (
    <div>
      <label className="block text-sm text-slate-300 mb-2 font-medium">{label}</label>
      <div className="flex gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          min={min}
          max={max}
          step={step}
          className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 focus:outline-none focus:border-cyan-500"
        />
        <input
          type="range"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          min={min}
          max={max}
          step={step}
          className="flex-1"
        />
      </div>
    </div>
  )
}

type MetricColor = 'cyan' | 'emerald' | 'blue' | 'purple' | 'yellow' | 'pink'

interface MetricCardProps {
  label: string
  value: string
  std?: string
  color: MetricColor
}

// Static class names (not interpolated) so Tailwind's JIT can detect them.
const METRIC_CARD_CLASSES: Record<MetricColor, string> = {
  cyan: 'from-cyan-600 to-cyan-400 border-cyan-500 text-cyan-400',
  emerald: 'from-emerald-600 to-emerald-400 border-emerald-500 text-emerald-400',
  blue: 'from-blue-600 to-blue-400 border-blue-500 text-blue-400',
  purple: 'from-purple-600 to-purple-400 border-purple-500 text-purple-400',
  yellow: 'from-yellow-600 to-yellow-400 border-yellow-500 text-yellow-400',
  pink: 'from-pink-600 to-pink-400 border-pink-500 text-pink-400',
}

function MetricCard({ label, value, std, color }: MetricCardProps) {
  return (
    <div className={`bg-gradient-to-br ${METRIC_CARD_CLASSES[color]} bg-opacity-10 border border-opacity-30 rounded-lg p-4`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${METRIC_CARD_CLASSES[color].split(' ').pop()}`}>{value}</p>
      {std && <p className="text-xs text-slate-500 mt-1">{std}</p>}
    </div>
  )
}

function calculateStdDev(values: number[]): number {
  if (values.length < 2) return 0
  const mean = values.reduce((a, b) => a + b) / values.length
  const variance = values.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / values.length
  return Math.sqrt(variance)
}
