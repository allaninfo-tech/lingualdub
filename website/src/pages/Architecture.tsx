import GithubIcon from '../components/GithubIcon';

const PIPELINE_STEPS = [
  { label: 'LANGUAGE + RESOURCES', sub: 'Language metadata, resource profiles, and available audio/text data assets' },
  { label: 'COMPONENTS', sub: 'ASR · Translation · TTS · Alignment · Speaker Modelling · Evaluation' },
  { label: 'PIPELINE COMPOSITION', sub: 'Assembly-time contract validation and fault-tolerance mode selection' },
  { label: 'EXECUTION', sub: 'Per-segment routing, code-switch handling, and degraded execution fallback' },
  { label: 'EVALUATE + ARTIFACTS', sub: 'Evaluator components, metrics recording, and provenance-tracked outputs' },
  { label: 'TARGET APPLICATIONS', sub: 'Dubbing · Speech-to-Speech · Subtitles · Custom research pipelines' },
];

const DEV_LIFECYCLE = [
  'Profile language + resources',
  'Select / register components',
  'Compose pipeline',
  'Run baseline',
  'Adapt / generate data / process',
  'Evaluate',
  'Save models, datasets, metrics, and artifacts',
  'Replace components or iterate',
];

const REPO_STRUCTURE = [
  { path: 'lingualdub/', desc: 'Core framework package', sub: [
    'core/', 'registry/', 'components/', 'pipeline/', 'languages/', 'utils/',
  ]},
  { path: 'research/', desc: 'Research module workspaces', sub: [
    'temporal_alignment/', 'code_switching/', 'voice_transfer/', 'voice_retention_eval/', 'av_sync/',
  ]},
  { path: 'configs/', desc: 'Pipeline configuration templates', sub: [] },
  { path: 'notebooks/', desc: 'Jupyter notebooks for testing and pipelines', sub: [] },
  { path: 'website/', desc: 'LingualDub Web Portal (React + Tailwind + Vite)', sub: [] },
  { path: 'tests/', desc: 'Test suite mirroring package structure', sub: [] },
  { path: 'docs/', desc: 'Architecture guides and per-module documentation', sub: [] },
];

export default function Architecture() {
  return (
    <div className="bg-[#090d16] text-white min-h-full">
      {/* Page header */}
      <section className="border-b border-slate-800/80 py-16 bg-[#0c1220]/60">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-3">System Blueprint</p>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-5">
            Architecture
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed max-w-3xl">
            How the core abstractions connect into a reproducible, closed-loop development cycle —
            from language profiling through evaluation back into the registry.
          </p>
        </div>
      </section>

      {/* Pipeline flow */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-10">Pipeline Execution Flow</h2>
          <div className="relative max-w-2xl mx-auto">
            {PIPELINE_STEPS.map((step, i) => (
              <div key={step.label} className="relative flex items-start gap-5 mb-4 last:mb-0">
                {/* Connector line */}
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className="absolute left-5 top-11 bottom-0 w-0.5 bg-slate-800" />
                )}
                {/* Step badge */}
                <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 text-white flex items-center justify-center text-sm font-bold shrink-0 z-10 shadow">
                  {i + 1}
                </div>
                {/* Step content */}
                <div className="flex-1 pb-4">
                  <div className="bg-[#0f172a] rounded-xl border border-slate-800 px-5 py-4 hover:border-slate-700 transition-colors shadow">
                    <p className="font-bold text-white text-sm tracking-wide">{step.label}</p>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{step.sub}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Development lifecycle loop */}
      <section className="py-16 border-b border-slate-800/80 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-3">Iterative Development Loop</h2>
          <p className="text-slate-400 mb-10 text-sm leading-relaxed max-w-2xl">
            Saved artifacts re-enter the loop as registered resources and components — making iteration
            a true feedback loop.
          </p>

          <div className="flex flex-wrap gap-2.5 items-center">
            {DEV_LIFECYCLE.map((step, i) => (
              <span key={step} className="flex items-center gap-2">
                <span className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold shadow ${
                  i === 0 || i === DEV_LIFECYCLE.length - 1
                    ? 'bg-white text-slate-950 font-bold'
                    : 'bg-[#0f172a] border border-slate-800 text-slate-200'
                }`}>
                  {step}
                </span>
                {i < DEV_LIFECYCLE.length - 1 && (
                  <span className="text-brand-500 font-bold text-sm">→</span>
                )}
              </span>
            ))}
            <span className="text-brand-400 font-bold text-sm ml-1">↺ loop</span>
          </div>
        </div>
      </section>

      {/* Component types */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-8">Supported Component Categories</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {[
              { type: 'asr', label: 'ASR', desc: 'Automatic Speech Recognition' },
              { type: 'translation', label: 'Translation', desc: 'Text & Speech translation' },
              { type: 'tts', label: 'TTS', desc: 'Text-to-Speech synthesis' },
              { type: 'alignment', label: 'Alignment', desc: 'Temporal & forced alignment' },
              { type: 'speaker', label: 'Speaker', desc: 'Speaker embeddings & modelling' },
              { type: 'code_switch', label: 'Code-Switch', desc: 'Multilingual segment routing' },
              { type: 'adaptation', label: 'Adaptation', desc: 'LoRA, adapters & fine-tuning' },
              { type: 'eval', label: 'Evaluation', desc: 'Metrics & human eval protocols' },
              { type: 'preprocessing', label: 'Preprocessing', desc: 'Audio & text normalization' },
              { type: 'custom', label: '+ Custom', desc: 'User-defined registered types' },
            ].map(c => (
              <div key={c.type} className="bg-[#0f172a] rounded-xl border border-slate-800 p-4 text-center hover:border-slate-700 transition-all shadow">
                <p className="font-bold text-white text-sm mb-1">{c.label}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Repository blueprint */}
      <section className="py-16 border-b border-slate-800/80 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-8">Repository Layout</h2>
          <div className="bg-black/80 rounded-2xl p-6 sm:p-8 font-mono text-sm border border-slate-800 shadow-xl">
            <p className="text-brand-300 font-bold mb-4 text-sm">lingualdub/</p>
            {REPO_STRUCTURE.map(({ path, desc, sub }) => (
              <div key={path} className="mb-3.5 last:mb-0">
                <div className="flex items-baseline gap-3">
                  <span className="text-white font-semibold">├── {path}</span>
                  <span className="text-slate-400 text-xs hidden sm:inline"># {desc}</span>
                </div>
                {sub.length > 0 && (
                  <div className="ml-6 mt-1 flex flex-wrap gap-x-4 gap-y-0.5">
                    {sub.map(s => (
                      <span key={s} className="text-slate-400 text-xs">│&nbsp;&nbsp;├── {s}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* GitHub CTA */}
      <section className="py-16 bg-[#0c1220]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold mb-3">Explore the Codebase</h2>
          <p className="text-slate-300 mb-8 text-sm max-w-xl mx-auto">
            The complete Python package, research modules, notebooks, and docs are open source on GitHub.
          </p>
          <a
            href="https://github.com/allaninfo-tech/lingualdub"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 shadow transition-all"
          >
            <GithubIcon className="w-5 h-5 text-slate-950" />
            allaninfo-tech/lingualdub
          </a>
        </div>
      </section>
    </div>
  );
}
