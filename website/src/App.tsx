import React from 'react';
import { 
  AudioWaveform, 
  Layers, 
  GitBranch, 
  Terminal, 
  Sparkles, 
  Globe2, 
  ShieldCheck, 
  ArrowRight, 
  Github, 
  BookOpen,
  Cpu,
  RefreshCw,
  Sliders
} from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-brand-900 selection:text-white">
      {/* Navigation */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-white/80 border-b border-slate-200/80 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img 
              src="/logo.png" 
              alt="LingualDub Logo" 
              className="h-10 w-auto object-contain hover:scale-105 transition-transform" 
            />
            <div className="flex flex-col">
              <span className="font-extrabold text-xl tracking-tight text-brand-900 leading-tight">
                LingualDub
              </span>
              <span className="text-[10px] font-semibold text-brand-600 uppercase tracking-widest">
                Speech AI Framework
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
            <a href="#overview" className="hover:text-brand-900 transition-colors">Overview</a>
            <a href="#abstractions" className="hover:text-brand-900 transition-colors">Abstractions</a>
            <a href="#research" className="hover:text-brand-900 transition-colors">Research</a>
            <a href="#architecture" className="hover:text-brand-900 transition-colors">Architecture</a>
          </nav>

          <div className="flex items-center gap-3">
            <a 
              href="https://github.com/allaninfo-tech/lingualdub" 
              target="_blank" 
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-brand-900 hover:bg-brand-800 rounded-lg shadow-sm hover:shadow transition-all"
            >
              <Github className="w-4 h-4" />
              <span>GitHub</span>
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-24 bg-gradient-to-b from-white via-brand-50/30 to-slate-50 border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
            
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-100/80 border border-brand-200 text-brand-900 text-xs font-semibold uppercase tracking-wider mb-6 shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-brand-600" />
              Low-Resource Speech AI Architecture
            </div>

            <h1 className="text-4xl sm:text-6xl font-black text-brand-900 tracking-tight leading-[1.1] mb-6">
              Composable, Registry-Driven Speech AI for <span className="bg-gradient-to-r from-brand-800 to-blue-600 bg-clip-text text-transparent">Low-Resource Languages</span>
            </h1>

            <p className="text-lg sm:text-xl text-slate-600 leading-relaxed mb-8 max-w-3xl">
              An open, modular development framework for building, adapting, composing, and evaluating 
              speech pipelines. Stop rewriting infrastructure — standardize and extend.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4">
              <a 
                href="https://github.com/allaninfo-tech/lingualdub" 
                target="_blank" 
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold text-white bg-brand-900 hover:bg-brand-800 shadow-md hover:shadow-lg transition-all"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </a>
              <a 
                href="https://github.com/allaninfo-tech/lingualdub/tree/main/docs" 
                target="_blank" 
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold text-brand-900 bg-white border border-slate-300 hover:bg-slate-50 hover:border-slate-400 shadow-sm transition-all"
              >
                <BookOpen className="w-4 h-4" />
                Documentation
              </a>
            </div>

            {/* Quick Install Banner */}
            <div className="mt-12 w-full max-w-xl bg-brand-950 text-slate-200 rounded-2xl p-4 shadow-xl border border-brand-900/50 flex items-center justify-between text-left font-mono text-sm">
              <div className="flex items-center gap-3 overflow-hidden">
                <Terminal className="w-4 h-4 text-brand-400 shrink-0" />
                <span className="text-slate-400 select-none">$</span>
                <span className="truncate text-white">git clone https://github.com/allaninfo-tech/lingualdub.git</span>
              </div>
              <span className="text-xs bg-brand-800/80 px-2 py-1 rounded text-brand-200 font-sans font-semibold shrink-0">v0.1.0-dev</span>
            </div>

          </div>
        </div>
      </section>

      {/* Core Abstractions Section */}
      <section id="abstractions" className="py-20 bg-white border-b border-slate-200/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-brand-700 uppercase tracking-widest mb-2">Architectural Foundation</h2>
            <p className="text-3xl sm:text-4xl font-extrabold text-brand-900 tracking-tight">
              Five Core Abstractions in a Closed Loop
            </p>
            <p className="mt-4 text-slate-600 text-base sm:text-lg">
              Everything in LingualDub is built around interoperable primitives with contract-based compatibility and complete provenance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Language */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 hover:border-brand-300 transition-all shadow-sm hover:shadow-md">
              <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-900 mb-5">
                <Globe2 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-brand-900 mb-2">Language</h3>
              <p className="text-slate-600 text-sm leading-relaxed mb-4">
                First-class language profiles capturing resource scarcity, related language affinities, dialect flags, and compatible components.
              </p>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-800 border border-brand-200">
                Resource-Aware
              </span>
            </div>

            {/* Resource */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 hover:border-brand-300 transition-all shadow-sm hover:shadow-md">
              <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-900 mb-5">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-brand-900 mb-2">Resource</h3>
              <p className="text-slate-600 text-sm leading-relaxed mb-4">
                Speech, text, lexicons, and checkpoints backed by mandatory provenance and ethical consent validation for voice artifacts.
              </p>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-800 border border-brand-200">
                Ethical & Provenance-Backed
              </span>
            </div>

            {/* Component */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 hover:border-brand-300 transition-all shadow-sm hover:shadow-md">
              <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-900 mb-5">
                <Cpu className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-brand-900 mb-2">Component</h3>
              <p className="text-slate-600 text-sm leading-relaxed mb-4">
                Replaceable stages declaring explicit <code className="text-xs font-mono bg-slate-200 px-1 py-0.5 rounded">requires</code> and <code className="text-xs font-mono bg-slate-200 px-1 py-0.5 rounded">provides</code> contracts, verified at compose time.
              </p>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-800 border border-brand-200">
                Compose-Time Validation
              </span>
            </div>

            {/* Pipeline */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 hover:border-brand-300 transition-all shadow-sm hover:shadow-md">
              <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-900 mb-5">
                <GitBranch className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-brand-900 mb-2">Pipeline</h3>
              <p className="text-slate-600 text-sm leading-relaxed mb-4">
                Flexible workflow execution with 3-mode fault tolerance (<code className="text-xs font-mono text-brand-800">abort</code>, <code className="text-xs font-mono text-brand-800">skip</code>, <code className="text-xs font-mono text-brand-800">degrade</code>) and segment-level language routing.
              </p>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-800 border border-brand-200">
                Resilient Execution
              </span>
            </div>

            {/* Registry */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 hover:border-brand-300 transition-all shadow-sm hover:shadow-md">
              <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-900 mb-5">
                <Sliders className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-brand-900 mb-2">Registry</h3>
              <p className="text-slate-600 text-sm leading-relaxed mb-4">
                Decoupled component discovery and version resolution with namespaced conflict policies. Add models without touching core code.
              </p>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-800 border border-brand-200">
                Zero Core Modifications
              </span>
            </div>

            {/* Reproducibility */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 hover:border-brand-300 transition-all shadow-sm hover:shadow-md">
              <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-900 mb-5">
                <RefreshCw className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-brand-900 mb-2">Development Loop</h3>
              <p className="text-slate-600 text-sm leading-relaxed mb-4">
                Profile → Compose → Baseline → Adapt → Evaluate → Re-register. Checkpoints and adapters feed straight back into the Registry.
              </p>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-brand-50 text-brand-800 border border-brand-200">
                Iterative Lifecycle
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Research Modules Section */}
      <section id="research" className="py-20 bg-slate-50 border-b border-slate-200/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-brand-700 uppercase tracking-widest mb-2">Open Investigations</h2>
            <p className="text-3xl sm:text-4xl font-extrabold text-brand-900 tracking-tight">
              Research Challenge Modules
            </p>
            <p className="mt-4 text-slate-600 text-base sm:text-lg">
              Structured research agendas with falsifiable baselines and concrete completion criteria.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-bold text-brand-900">Temporal Alignment</h4>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">Near-Term</span>
              </div>
              <p className="text-sm text-slate-600">Cross-lingual duration modeling, speech-rate control, and segment fitting.</p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-bold text-brand-900">Code-Switching</h4>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">Near-Term</span>
              </div>
              <p className="text-sm text-slate-600">Per-segment language identification and dynamic downstream routing for mixed utterances.</p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-bold text-brand-900">Voice-Retention Eval</h4>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">Near-Term</span>
              </div>
              <p className="text-sm text-slate-600">Repeatable speaker similarity protocols before automated metrics are deployed.</p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-bold text-brand-900">Cross-Lingual Voice Transfer</h4>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-100 text-blue-800 rounded">Open-Ended</span>
              </div>
              <p className="text-sm text-slate-600">Speaker representation preservation across Bantu linguistic boundaries.</p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-bold text-brand-900">Audio-Visual Sync</h4>
                <span className="text-[10px] font-bold px-2 py-0.5 bg-purple-100 text-purple-800 rounded">Mid-Term</span>
              </div>
              <p className="text-sm text-slate-600">Dialogue timing and lip-sync alignment for the signature Luganda dubbing workload.</p>
            </div>

            <div className="bg-brand-900 text-white p-6 rounded-2xl shadow-sm flex flex-col justify-between">
              <div>
                <ShieldCheck className="w-6 h-6 text-brand-300 mb-2" />
                <h4 className="font-bold text-white mb-1">Ethical Data Policy</h4>
                <p className="text-xs text-brand-100">Voice consent verification is enforced at the Resource contract level.</p>
              </div>
              <span className="text-[10px] font-mono text-brand-300 mt-4">Verified by Resource.provenance</span>
            </div>
          </div>
        </div>
      </section>

      {/* Cloudflare Pages Deploy Instructions Section */}
      <section className="py-16 bg-white border-b border-slate-200/80">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-brand-900 mb-4">Deploy to Cloudflare Pages via Wrangler</h2>
          <p className="text-slate-600 mb-8 text-sm sm:text-base">
            Build and deploy directly from your local terminal using Cloudflare's Wrangler CLI.
          </p>

          <div className="bg-brand-950 text-slate-100 p-6 rounded-2xl text-left font-mono text-xs sm:text-sm border border-brand-900/40 shadow-lg space-y-3">
            <div className="text-slate-400"># 1. Install dependencies & build site</div>
            <div className="text-brand-300">cd website && npm install && npm run build</div>
            
            <div className="text-slate-400 pt-2"># 2. Deploy to Cloudflare Pages using Wrangler</div>
            <div className="text-brand-300">npx wrangler pages deploy dist --project-name=lingualdub</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-brand-950 text-slate-400 py-12 border-t border-brand-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Logo" className="h-8 w-auto brightness-200 contrast-200" />
            <span className="text-white font-bold tracking-tight">LingualDub</span>
          </div>

          <p className="text-xs text-slate-400 text-center sm:text-left">
            Master Architecture Blueprint · Luganda & Runyankole Validation
          </p>

          <div className="flex items-center gap-4">
            <a 
              href="https://github.com/allaninfo-tech/lingualdub" 
              className="text-slate-400 hover:text-white transition-colors"
              target="_blank" 
              rel="noreferrer"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
