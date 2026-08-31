import { AlertTriangle, ArrowRight, CheckCircle2, Globe2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Overview() {
  return (
    <div className="bg-[#090d16] text-white min-h-full">
      {/* Page header */}
      <section className="border-b border-slate-800/80 py-16 bg-[#0c1220]/60">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-3">Project Overview</p>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-5">
            What is LingualDub?
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed max-w-3xl">
            An open, modular development framework for speech AI research in low-resource language contexts —
            designed to standardise and reuse infrastructure rather than rebuild it from scratch for every language.
          </p>
        </div>
      </section>

      {/* The Problem */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-9 h-9 rounded-xl bg-red-950/60 border border-red-800/60 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-4 h-4 text-red-400" />
            </div>
            <h2 className="text-2xl font-bold text-white">The Problem</h2>
          </div>
          <div className="bg-[#0f172a] rounded-2xl border border-slate-800 p-8 space-y-5 shadow-xl">
            <p className="text-slate-300 leading-relaxed">
              Low-resource languages rarely share the same combination of speech data, text corpora,
              parallel translations, pronunciation resources, pretrained models, and evaluation sets.
              Developers and researchers repeatedly glue together incompatible ASR, translation, TTS,
              alignment, data, and evaluation components by hand.
            </p>
            <p className="text-slate-300 leading-relaxed">
              Critical research challenges — code-switching, language transfer, voice preservation,
              timing alignment, and evaluation — are typically scattered across separate projects
              rather than available in one composable environment.
            </p>
            <div className="border-l-4 border-red-500 pl-4 bg-red-950/30 py-3 rounded-r-lg">
              <p className="text-red-200 font-medium leading-relaxed text-sm">
                When a new language or research method is introduced, the surrounding infrastructure
                often has to be rebuilt rather than simply extended.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* The Solution */}
      <section className="py-16 border-b border-slate-800/80 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-9 h-9 rounded-xl bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-white">The Solution</h2>
          </div>
          <div className="bg-[#0f172a] rounded-2xl p-8 border border-slate-800 shadow-xl">
            <p className="text-slate-200 leading-relaxed text-lg mb-8">
              LingualDub makes the repeated engineering and research work around low-resource speech{' '}
              <span className="text-white font-bold">reusable, composable, and replaceable</span>.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              {[
                {
                  title: 'Reusable',
                  desc: 'Components register once and are discovered by any compatible pipeline without copy-paste.',
                },
                {
                  title: 'Composable',
                  desc: 'Contracts define required and provided data types — verified at assembly time, not at runtime.',
                },
                {
                  title: 'Replaceable',
                  desc: 'Swap any model or component implementation without touching downstream stages or the framework core.',
                },
              ].map(p => (
                <div key={p.title} className="bg-slate-900/80 rounded-xl p-5 border border-slate-800">
                  <h3 className="font-bold text-white mb-2 text-base">{p.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{p.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Extension Matrix */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-4">Extension Matrix</h2>
          <p className="text-slate-400 mb-8 leading-relaxed">
            Components are the primary extension point. Add new capabilities without editing framework internals:
          </p>
          <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0f172a] shadow-xl">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800">
                  <th className="px-6 py-4 text-left font-semibold text-white">Goal</th>
                  <th className="px-6 py-4 text-left font-semibold text-white">Mechanism</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {[
                  ['New language', 'Register language metadata, resource profile, and available resources'],
                  ['New model', 'Implement and register a component conforming to interface'],
                  ['New method', 'Add a component or custom pipeline stage'],
                  ['New dataset', 'Register a resource with verified provenance and consent'],
                  ['New evaluator', 'Implement an evaluator component and register it'],
                  ['New pipeline', 'Compose existing components into a new pipeline flow'],
                ].map(([goal, how]) => (
                  <tr key={goal} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4 font-semibold text-brand-400 whitespace-nowrap">{goal}</td>
                    <td className="px-6 py-4 text-slate-300">{how}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Next CTA */}
      <section className="py-12 bg-[#0c1220]/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <p className="font-bold text-white">Next: Core Abstractions</p>
            <p className="text-sm text-slate-400">Language · Resource · Component · Pipeline · Result · Registry</p>
          </div>
          <Link
            to="/abstractions"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 transition-all shadow shrink-0"
          >
            Explore Abstractions <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
