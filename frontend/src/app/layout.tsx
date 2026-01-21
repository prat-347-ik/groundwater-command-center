import './globals.css';
import Link from 'next/link';
import { LayoutDashboard, ShieldCheck } from 'lucide-react';

export const metadata = {
  title: 'Groundwater Command Center',
  description: 'AI-Powered Aquifer Monitoring',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 min-h-screen flex flex-col">
        {/* Global Navigation Bar */}
        <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            
            {/* Logo / Home */}
            <Link href="/" className="flex items-center gap-2 font-bold text-slate-900 text-lg">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
                <LayoutDashboard className="h-5 w-5" />
              </div>
              <span>HydroCommand</span>
            </Link>

            {/* Nav Links */}
            <div className="flex items-center gap-6 text-sm font-medium text-slate-600">
              <Link href="/" className="hover:text-blue-600 transition-colors">
                Dashboard
              </Link>
              <Link href="/admin" className="flex items-center gap-2 hover:text-blue-600 transition-colors">
                <ShieldCheck className="h-4 w-4" />
                Data Ops
              </Link>
            </div>

          </div>
        </nav>

        {/* Page Content */}
        <div className="flex-1">
          {children}
        </div>
      </body>
    </html>
  );
}