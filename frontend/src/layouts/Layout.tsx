import React from 'react'
import Sidebar from '../components/Sidebar'

interface Props {
  children: React.ReactNode
}

// Shared layout wrapper providing sidebar navigation and main content area
// Used by App.tsx to wrap all page routes
export default function Layout({ children }: Props) {
  return (
    <div className="min-h-screen flex bg-gray-900 text-gray-100">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}
