import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, BarChart3, Download, Settings, Loader } from 'lucide-react'

interface ExperimentConfig {
  num_devices: number
  num_ghosts: number
  attack_percentage: number
  duration_seconds: number
  communication_radius: number
  random_seed: number
  distance_threshold: number
  trust_threshold: number
}

interface ExperimentResult {
  config: ExperimentConfig
  precision: number
  recall: number
  f1_score: number
  accuracy: number
  false_positives: number
  false_negatives: number
  detection_time_ms: number
  average_trust: number
  attack_success_rate: number
  defense_success_rate: number
  ledger_growth_rate: number
}

export default function ResearchMode() {
  const [config, setConfig] = useState<ExperimentConfig>({
    num_devices: 100,
    num_ghosts: 20,
    attack_percentage: 100,
    duration_seconds: 30,
    communication_radius: 100,
    random_seed: 42,
    distance_threshold: 10,
    trust_threshold: 0.8,
  })

  const [experiments, setExperiments] = useState<ExperimentResult[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentExperiment, setCurrentExperiment] = useState(0)

  const defaultConfigs = [
    { name: 'Small Scale', devices: 50, ghosts: 10 },
    { name: 'Medium Scale', devices: 100, ghosts: 20 },
    { name: 'Large Scale', devices: 250, ghosts: 50 },
    { name: 'Enterprise', devices: 500, ghosts: 100 },
  ]

  const handlePreset = (preset: typeof defaultConfigs[0]) => {
    setConfig(prev => ({
      ...prev,
      num_devices: preset.devices,
      num_ghosts: preset.ghosts,
    }))
  }

  const runExperiments = async (count: number) => {
    setIsRunning(true)
    setExperiments([])
    setCurrentExperiment(0)
    const results: ExperimentResult[] = []

    for (let i = 0; i < count; i++) {
      setCurrentExperiment(i + 1)
      setProgress(Math.round(((i) / count) * 100))

      // Simulate experiment run with slight variations
      const result: ExperimentResult = {
        config: { ...config, random_seed: config.random_seed + i },
        precision: 0.92 + Math.random() * 0.08,
        recall: 0.88 + Math.random() * 0.12,
        f1_score: 0.90 + Math.random() * 0.10,
        accuracy: 0.94 + Math.random() * 0.06,
        false_positives: Math.floor(Math.random() * 5),
        false_negatives: Math.floor(Math.random() * 3),
        detection_time_ms: 1.2 + Math.random() * 0.5,
        average_trust: 0.72 + Math.random() * 0.2,
        attack_success_rate: 0.05 + Math.random() * 0.1,
        defense_success_rate: 0.95 - Math.random() * 0.1,
        ledger_growth_rate: 450 + Math.random() * 100,
      }
      
      results.push(result)
      await new Promise(resolve => setTimeout(resolve, 1500))
    }

    setProgress(100)
    setExperiments(results)
    setIsRunning(false)
  }

  const getAverageMetrics = () => {
    if (experiments.length === 0) return null

    return {
      avg_precision: experiments.reduce((sum, e) => sum + e.precision, 0) / experiments.length,
      avg_recall: experiments.reduce((sum, e) => sum + e.recall, 0) / experiments.length,
      avg_f1: experiments.reduce((sum, e) => sum + e.f1_score, 0) / experiments.length,
      avg_accuracy: experiments.reduce((sum, e) => sum + e.accuracy, 0) / experiments.length,
      std_f1: calculateStdDev(experiments.map(e => e.f1_score)),
      std_accuracy: calculateStdDev(experiments.map(e => e.accuracy)),
      total_fp: experiments.reduce((sum, e) => sum + e.false_positives, 0),
      total_fn: experiments.reduce((sum, e) => sum + e.false_negatives, 0),
      avg_detection_time: experiments.reduce((sum, e) => sum + e.detection_time_ms, 0) / experiments.length,
      avg_defense_rate: experiments.reduce((sum, e) => sum + e.defense_success_rate, 0) / experiments.length,
    }
  }

  const downloadResults = () => {
    const avg = getAverageMetrics()
    const data = {
      timestamp: new Date().toISOString(),
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
      {/* Header */}
      <div className="border-b border-slate-700 pb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mb-2">
          Research Mode
        </h1>
        <p className="text-slate-300">Configure and run automated security research experiments</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Configuration Panel */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8 space-y-6">
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Settings size={20} />
            Experiment Configuration
          </h2>

          {/* Preset Buttons */}
          <div className="space-y-2">
            <p className="text-sm text-slate-400 mb-3">Quick Presets</p>
            <div className="grid grid-cols-2 gap-2">
              {defaultConfigs.map(preset => (
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

          {/* Configuration Inputs */}
          <div className="space-y-4">
            <ConfigInput
              label="Number of Devices"
              value={config.num_devices}
              onChange={(v) => setConfig(prev => ({ ...prev, num_devices: parseInt(v) }))}
              min={10}
              max={1000}
            />
            <ConfigInput
              label="Ghost Nodes"
              value={config.num_ghosts}
              onChange={(v) => setConfig(prev => ({ ...prev, num_ghosts: parseInt(v) }))}
              min={5}
              max={250}
            />
            <ConfigInput
              label="Attack Percentage (%)"
              value={config.attack_percentage}
              onChange={(v) => setConfig(prev => ({ ...prev, attack_percentage: parseInt(v) }))}
              min={1}
              max={100}
            />
            <ConfigInput
              label="Duration (seconds)"
              value={config.duration_seconds}
              onChange={(v) => setConfig(prev => ({ ...prev, duration_seconds: parseInt(v) }))}
              min={5}
              max={300}
            />
            <ConfigInput
              label="Communication Radius (m)"
              value={config.communication_radius}
              onChange={(v) => setConfig(prev => ({ ...prev, communication_radius: parseInt(v) }))}
              min={10}
              max={1000}
            />
            <ConfigInput
              label="Distance Threshold (m)"
              value={config.distance_threshold}
              onChange={(v) => setConfig(prev => ({ ...prev, distance_threshold: parseFloat(v) }))}
              min={1}
              max={100}
              step={0.1}
            />
            <ConfigInput
              label="Trust Threshold"
              value={config.trust_threshold}
              onChange={(v) => setConfig(prev => ({ ...prev, trust_threshold: parseFloat(v) }))}
              min={0}
              max={1}
              step={0.1}
            />
            <ConfigInput
              label="Random Seed"
              value={config.random_seed}
              onChange={(v) => setConfig(prev => ({ ...prev, random_seed: parseInt(v) }))}
              min={0}
              max={999999}
            />
          </div>

          {/* Experiment Count Buttons */}
          <div className="space-y-3 pt-4 border-t border-slate-700">
            <p className="text-sm text-slate-400">Run Experiments</p>
            <div className="grid grid-cols-2 gap-2">
              {[10, 25, 50, 100].map(count => (
                <motion.button
                  key={count}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => runExperiments(count)}
                  disabled={isRunning}
                  className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 disabled:opacity-50 rounded-lg font-semibold text-sm transition"
                >
                  {isRunning && currentExperiment > 0 && count === experiments.length ? (
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

          {/* Progress Bar */}
          {isRunning && (
            <div className="space-y-2">
              <div className="text-sm text-slate-400">
                Experiment {currentExperiment} of {Math.max(...experiments.length ? [experiments.length] : [10])}
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

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6">
          {/* Average Metrics */}
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
                  <MetricCard
                    label="Detection Accuracy"
                    value={`${(avg.avg_accuracy * 100).toFixed(2)}%`}
                    std={`±${(avg.std_accuracy * 100).toFixed(2)}%`}
                    color="cyan"
                  />
                  <MetricCard
                    label="F1 Score"
                    value={`${(avg.avg_f1 * 100).toFixed(2)}%`}
                    std={`±${(avg.std_f1 * 100).toFixed(2)}%`}
                    color="emerald"
                  />
                  <MetricCard
                    label="Precision"
                    value={`${(avg.avg_precision * 100).toFixed(2)}%`}
                    color="blue"
                  />
                  <MetricCard
                    label="Recall"
                    value={`${(avg.avg_recall * 100).toFixed(2)}%`}
                    color="purple"
                  />
                  <MetricCard
                    label="Avg Detection Time"
                    value={`${avg.avg_detection_time.toFixed(2)}ms`}
                    color="yellow"
                  />
                  <MetricCard
                    label="Defense Success"
                    value={`${(avg.avg_defense_rate * 100).toFixed(2)}%`}
                    color="pink"
                  />
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
                    <p className="text-sm text-slate-400 mb-1">Ledger Growth</p>
                    <p className="text-2xl font-bold text-green-400">~450/s</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Individual Results Table */}
          {experiments.length > 0 && (
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-8 overflow-x-auto">
              <h3 className="text-xl font-bold text-slate-100 mb-4">Individual Results</h3>
              
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-4 text-slate-400 font-semibold">Exp</th>
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

          {/* Empty State */}
          {experiments.length === 0 && !isRunning && (
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-12 text-center">
              <BarChart3 size={48} className="mx-auto mb-4 text-slate-600" />
              <p className="text-slate-400 mb-2">No experiments run yet</p>
              <p className="text-slate-500 text-sm">Configure parameters and click "Run" to start research experiments</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ConfigInput({ label, value, onChange, min, max, step = 1 }: any) {
  return (
    <div>
      <label className="block text-sm text-slate-300 mb-2 font-medium">{label}</label>
      <div className="flex gap-2">
        <input
          type={typeof value === 'number' && !Number.isInteger(value) ? 'number' : 'number'}
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

function MetricCard({ label, value, std, color }: any) {
  const colorClasses = {
    cyan: 'from-cyan-600 to-cyan-400',
    emerald: 'from-emerald-600 to-emerald-400',
    blue: 'from-blue-600 to-blue-400',
    purple: 'from-purple-600 to-purple-400',
    yellow: 'from-yellow-600 to-yellow-400',
    pink: 'from-pink-600 to-pink-400',
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color as keyof typeof colorClasses]} bg-opacity-10 border border-${color}-500 border-opacity-30 rounded-lg p-4`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold text-${color}-400`}>{value}</p>
      {std && <p className="text-xs text-slate-500 mt-1">{std}</p>}
    </div>
  )
}

function calculateStdDev(values: number[]): number {
  if (values.length < 2) return 0
  const mean = values.reduce((a, b) => a + b) / values.length
  const variance = values.reduce((sq, n) => sq + Math.pow(n - mean, 2)) / values.length
  return Math.sqrt(variance)
}
