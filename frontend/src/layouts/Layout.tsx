import React from 'react'
import Sidebar from '../components/Sidebar'

interface Props {
  children: React.ReactNode
}

export default function Layout({ children }: Props) {
  return (
    <div className="min-h-screen flex bg-gray-900 text-gray-100">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}
