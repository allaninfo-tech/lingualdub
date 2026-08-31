import { ArrowRight, AudioWaveform, Cpu, GitBranch, Globe2, Layers, Sliders } from 'lucide-react';
import { Link } from 'react-router-dom';

const ABSTRACTIONS = [
  {
    icon: Globe2,
    name: 'Language',
    tagline: 'Resource-Aware Profile',
    desc: 'Represents a language together with its metadata, supported processing tasks, available resources, related languages, and compatible components. Resource scarcity is a first-class property.',
    highlights: ['Dialect and orthography flags', 'Resource scarcity profile', 'Related-language affinities', 'Compatible component list'],
  },
  {
    icon: Layers,
    name: 'Resource',
    tagline: 'Ethical & Provenance-Backed Asset',
    desc: 'Represents a data asset — speech recordings, text corpora, parallel translations, lexicons, pronunciation dictionaries, model checkpoints, or evaluation sets — with mandatory provenance and consent verification.',
    highlights: ['Mandatory provenance tracking', 'Voice consent verification', 'Quality & version metadata', 'Compatible component mapping'],
  },
  {
    icon: Cpu,
    name: 'Component',
    tagline: 'Compose-Time Contract Safety',
    desc: 'A replaceable processing unit with a stable input/output contract. Declares what capabilities it requires from upstream stages and provides to downstream stages, catching incompatibilities before execution.',
    highlights: ['Types: ASR, TTS, Translation, Alignment, Speaker, Eval', 'requires / provides contracts', 'Degraded execution fallback path', 'Manifest-based registration'],
  },
  {
    icon: GitBranch,
    name: 'Pipeline',
    tagline: 'Resilient Workflow Execution',
    desc: 'A composition of components connected by shared data representations, executed as a reproducible workflow. Built-in 3-mode fault tolerance (abort, skip, degrade) and per-segment language routing for code-switching.',
    highlights: ['3-mode fault tolerance: abort · skip · degrade', 'Per-segment language routing', 'Structural code-switching support', 'Reproducible execution config'],
  },
  {
    icon: AudioWaveform,
    name: 'Result',
    tagline: 'Structured Output with Provenance',
    desc: 'A structured output carrying text content, segment-level data, speaker and language information, confidence, processing status (complete, partial, degraded), warnings, and links to generated audio/text artifacts.',
    highlights: ['Status: complete · partial · degraded', 'Segment-level language tags', 'Confidence scores & warnings', 'Artifact provenance links'],
  },
  {
    icon: Sliders,
    name: 'Registry',
    tagline: 'Zero Core Modifications',
    desc: 'The mechanism for discovering, registering, and resolving languages, resources, components, and evaluators without editing framework internals. Extensions ship a manifest; the registry scans manifests at startup.',
    highlights: ['Manifest-based discovery', 'Versioned entry pinning', 'Namespaced conflict resolution', 'Automatic startup discovery'],
  },
];

export default function Abstractions() {
  return (
    <div className="bg-[#090d16] text-white min-h-full">
      {/* Page header */}
      <section className="border-b border-slate-800/80 py-16 bg-[#0c1220]/60">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-3">Architectural Foundation</p>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-5">
            Core Abstractions
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed max-w-3xl">
            LingualDub is organized around five interoperable primitives in a closed, provenance-tracked loop,
            managed by a decoupled Registry for zero-core-modification extensibility.
          </p>
        </div>
      </section>

      {/* Closed loop sequence */}
      <section className="py-8 border-b border-slate-800/80 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-center gap-2 text-sm font-semibold">
            {['Language', 'Resource', 'Component', 'Pipeline', 'Result', '↺ Registry'].map((a, i) => (
              <span key={a} className="flex items-center gap-2">
                <span className={`px-4 py-2 rounded-xl border ${i < 5 ? 'bg-[#0f172a] border-slate-800 text-white' : 'bg-white border-white text-slate-950'} shadow`}>
                  {a}
                </span>
                {i < 5 && <span className="text-brand-500 font-bold">→</span>}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Abstractions grid */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {ABSTRACTIONS.map(({ icon: Icon, name, tagline, desc, highlights }) => (
              <div
                key={name}
                className="bg-[#0f172a] rounded-2xl border border-slate-800 p-7 hover:border-slate-700 transition-all group shadow-xl"
              >
                <div className="flex items-start gap-4 mb-5">
                  <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-brand-400 group-hover:text-white transition-colors">
                    <Icon className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">{name}</h3>
                    <span className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-md bg-slate-900 text-brand-300 border border-slate-800 mt-1">
                      {tagline}
                    </span>
                  </div>
                </div>

                <p className="text-slate-300 text-sm leading-relaxed mb-6">{desc}</p>

                <ul className="space-y-2 border-t border-slate-800/80 pt-4">
                  {highlights.map(h => (
                    <li key={h} className="flex items-start gap-2 text-xs text-slate-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-400 mt-1 shrink-0" />
                      {h}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architectural success criteria */}
      <section className="py-16 bg-[#0c1220]/40 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-2">Architectural Success Criteria</h2>
          <p className="text-slate-400 mb-8 text-sm">
            The framework succeeds if all extensions happen without touching core framework source code:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              ['New language', 'Register language metadata & resource profiles'],
              ['New model', 'Implement and register a component interface'],
              ['New method', 'Add a component or custom pipeline stage'],
              ['New dataset', 'Register a resource with consent provenance'],
              ['New evaluator', 'Implement and register an evaluator component'],
              ['New pipeline', 'Compose existing components in pipeline config'],
            ].map(([action, how]) => (
              <div key={action} className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 shadow">
                <p className="font-bold text-white text-sm mb-1.5">{action}</p>
                <p className="text-slate-400 text-xs leading-relaxed">{how}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Next CTA */}
      <section className="py-12 bg-[#0c1220]/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <p className="font-bold text-white">Next: Research Modules</p>
            <p className="text-sm text-slate-400">Temporal Alignment · Code-Switching · Voice Transfer · AV Sync</p>
          </div>
          <Link
            to="/research"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 transition-all shadow shrink-0"
          >
            View Research <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
