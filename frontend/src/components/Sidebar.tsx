import React, { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Home, BarChart3, Play, Shield, Beaker, Settings, Menu, X, Presentation } from 'lucide-react'

const links = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/presentation', label: 'Presentation', icon: Presentation },
  { to: '/simulation', label: 'Simulation', icon: Play },
  { to: '/security', label: 'Security', icon: Shield },
  { to: '/research', label: 'Research', icon: Beaker },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-slate-800 border border-slate-700 rounded-lg"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <aside className={`${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } md:translate-x-0 transition-transform fixed md:static w-64 h-screen bg-gradient-to-b from-slate-900 to-slate-950 border-r border-slate-700 p-6 z-40`}>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
            QShield SecureAccess
          </h1>
          <div className="text-xs text-slate-400 mt-2">Quantum-Resilient Access-Control Security Lab</div>
        </div>

        <nav className="flex flex-col gap-1">
          {links.map((l) => {
            const Icon = l.icon
            return (
              <NavLink
                key={l.to}
                to={l.to}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-slate-100'
                  }`
                }
              >
                <Icon size={20} />
                <span className="font-medium">{l.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Version Info */}
        <div className="mt-auto pt-6 border-t border-slate-700">
          <div className="text-xs text-slate-500">
            <p className="font-semibold mb-1">QShield SecureAccess v2.0</p>
            <p>Cyber-physical access-control security prototype</p>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          className="md:hidden fixed inset-0 bg-black/50 z-30"
        />
      )}
    </>
  )
}
