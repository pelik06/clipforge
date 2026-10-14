import './globals.css'

export const metadata = {
  title: 'ClipForge Studio — Video Clipping & Review Workspace',
  description: 'Precision automated 9:16 video clipping, reframing, and caption review workstation.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0c0d11] text-[#f3f4f6] min-h-screen antialiased selection:bg-[#2563eb] selection:text-white">
        {children}
      </body>
    </html>
  )
}
