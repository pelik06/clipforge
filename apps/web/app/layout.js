import './globals.css'

export const metadata = {
  title: 'ClipForge - Streamer Clipping & Review Dashboard',
  description: 'Streamer-first short-form clipping automation and review UI',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  )
}
