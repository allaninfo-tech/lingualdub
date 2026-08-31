import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import GithubIcon from './GithubIcon';
import TopLoadingBar from './TopLoadingBar';

const NAV_ITEMS = [
  { label: 'Home', to: '/', end: true },
  { label: 'Overview', to: '/overview', end: false },
  { label: 'Docs', to: '/docs', end: false },
  { label: 'Abstractions', to: '/abstractions', end: false },
  { label: 'Research', to: '/research', end: false },
  { label: 'Architecture', to: '/architecture', end: false },
];

export default function Layout() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close mobile menu on navigation
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  // Scroll to top on route change
  useEffect(() => { window.scrollTo({ top: 0 }); }, [pathname]);

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans selection:bg-brand-600 selection:text-white">
      <TopLoadingBar />

      {/* ── Sticky Navigation ── */}
      <header className="sticky top-0 z-50 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800/80 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 py-2.5 flex items-center justify-between gap-4">
          
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3.5 shrink-0 group">
            <div className="bg-white p-1 rounded-xl shadow-sm group-hover:scale-105 transition-transform">
              <img
                src="/logo.png"
                alt="LingualDub Logo"
                className="h-10 w-10 sm:h-11 sm:w-11 object-contain"
              />
            </div>
            <div className="flex flex-col">
              <span className="font-black text-xl sm:text-2xl tracking-tight text-white leading-tight">
                LingualDub
              </span>
              <span className="text-[10px] sm:text-[11px] font-bold text-brand-400 uppercase tracking-widest leading-none">
                Speech AI Framework
              </span>
            </div>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ label, to, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'text-white bg-slate-800/90 font-semibold shadow-inner border border-slate-700/60'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/40'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <a
              href="https://github.com/allaninfo-tech/lingualdub"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl text-slate-950 bg-white hover:bg-slate-100 shadow transition-all"
            >
              <GithubIcon className="w-4 h-4 text-slate-950" />
              <span>GitHub</span>
            </a>

            {/* Mobile hamburger */}
            <button
              aria-label="Toggle menu"
              className="md:hidden p-2 rounded-lg text-slate-200 hover:text-white hover:bg-slate-800 transition-colors"
              onClick={() => setMenuOpen(v => !v)}
            >
              {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {menuOpen && (
          <div className="md:hidden bg-[#0c1220] border-t border-slate-800 px-4 py-3 flex flex-col gap-1.5 shadow-xl">
            {NAV_ITEMS.map(({ label, to, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive ? 'text-white bg-slate-800 font-semibold' : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
            <a
              href="https://github.com/allaninfo-tech/lingualdub"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3.5 py-2.5 text-sm font-semibold text-slate-950 bg-white rounded-lg mt-2 justify-center"
            >
              <GithubIcon className="w-4 h-4" />
              <span>GitHub</span>
            </a>
          </div>
        )}
      </header>

      {/* ── Page content ── */}
      <main className="flex-1 page-fade-in">
        <Outlet />
      </main>

      {/* ── Footer ── */}
      <footer className="bg-[#050810] text-slate-400 py-12 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="bg-white p-1 rounded-lg">
                <img
                  src="/logo.png"
                  alt="LingualDub"
                  className="h-8 w-8 object-contain"
                />
              </div>
              <span className="text-white font-bold text-lg tracking-tight">LingualDub</span>
            </Link>

            <p className="text-xs text-slate-400 text-center leading-relaxed">
              Open-Source Speech AI Infrastructure for Low-Resource Languages
            </p>

            <div className="flex items-center gap-4">
              {NAV_ITEMS.map(({ label, to }) => (
                <Link
                  key={to}
                  to={to}
                  className="text-xs text-slate-400 hover:text-white transition-colors"
                >
                  {label}
                </Link>
              ))}
              <a
                href="https://github.com/allaninfo-tech/lingualdub"
                target="_blank"
                rel="noreferrer"
                className="text-slate-400 hover:text-white transition-colors ml-2"
                aria-label="GitHub Repository"
              >
                <GithubIcon className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
