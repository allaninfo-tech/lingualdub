import { BookOpen, Code2, Cpu, FileCode2, Layers, Sparkles, Terminal } from 'lucide-react';
import GithubIcon from '../components/GithubIcon';

export default function Docs() {
  return (
    <div className="bg-[#090d16] text-white min-h-full">
      {/* Header */}
      <section className="border-b border-slate-800/80 py-16 bg-[#0c1220]/60">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-950 border border-brand-800 text-brand-400 text-xs font-semibold uppercase tracking-wider mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            Developer & API Reference • v0.1.0
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-4">
            Documentation
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed max-w-3xl">
            API reference, SDK integration guides, and component contracts for building and composing speech AI pipelines with LingualDub.
          </p>
        </div>
      </section>

      {/* Release Announcement Banner */}
      <section className="py-8 bg-[#0c1220] border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-brand-950 border border-brand-800/80 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
            <div className="space-y-2">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Release v0.1.0 Stable</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white">LingualDub v0.1.0 is Live</h2>
              <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                All foundational milestones (M0–M8) are complete: ASR, MT, TTS, code-switching, temporal alignment, voice retention, cross-lingual voice transfer, audio-visual sync, and Runyankole generalisation proof.
              </p>
            </div>
            <a
              href="https://github.com/allannuwamanya/lingualdub"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 shadow transition-all shrink-0 text-sm"
            >
              <GithubIcon className="w-4 h-4 text-slate-950" />
              Follow on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* Python SDK Quickstart */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-2">Python SDK: End-to-End Pipeline</h2>
          <p className="text-sm text-slate-400 mb-8 max-w-2xl">
            Execute a speech dubbing pipeline with declarative configuration, assembly-time capability checking, and full provenance tracking:
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            {/* Code Block */}
            <div className="bg-black/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
              <div className="bg-slate-900/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  <span className="font-mono text-xs text-slate-400 ml-2">quickstart.py</span>
                </div>
                <span className="text-[11px] font-mono text-brand-400 font-semibold">Python 3.10+</span>
              </div>
              <pre className="p-5 font-mono text-xs sm:text-sm text-slate-200 overflow-x-auto leading-relaxed">
{`import lingualdub as ld

# 1. Initialize Registry & discover manifests
registry = ld.Registry(conflict_policy=ld.ConflictPolicy.HIGHEST_VERSION)
scanner = ld.ManifestScanner(registry)
scanner.scan()

# 2. Load declarative pipeline configuration
loader = ld.ConfigLoader(registry)
pipeline = loader.load_file("configs/luganda_english_baseline.yaml")

# 3. Create speech resource with recorded consent
audio = ld.Resource(
    id="lug_sample_01",
    kind=ld.ResourceKind.SPEECH,
    language="lug",
    version="1.0.0",
    path="data/samples/sample_lug.wav",
    provenance={"consent_basis": "research_evaluation"}
)

# 4. Execute pipeline with automatic contract checking
executor = ld.PipelineExecutor(pipeline)
result = executor.run(audio)

print(f"Status: {result.status.value.upper()}")
for seg in result.segments:
    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s] ({seg.language}): {seg.text}")
print(f"Dubbed Artifacts: {result.artifacts}")`}
              </pre>
            </div>

            {/* Architecture Highlights */}
            <div className="space-y-4">
              {[
                {
                  icon: Code2,
                  title: 'Registry & Dynamic Discovery',
                  desc: 'Discover and load ASR, translation, TTS, and alignment models declared in lingualdub.manifest.json files without modifying core code.',
                },
                {
                  icon: Cpu,
                  title: 'Assembly-Time Capability Validation',
                  desc: 'Pipelines statically verify stage requires tokens against upstream provides tokens before heavy model weights load.',
                },
                {
                  icon: Layers,
                  title: 'Multi-Tier Fault Tolerance',
                  desc: 'Selectable failure modes (ABORT, SKIP, DEGRADE) ensure graceful fallbacks and warning propagation when issues arise.',
                },
                {
                  icon: FileCode2,
                  title: 'Strict Provenance & Consent Enforcement',
                  desc: 'Every run records pipeline structure, model versions, dataset provenance, and enforces consent_basis for ethical voice AI.',
                },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="bg-[#0f172a] rounded-xl p-5 border border-slate-800 flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center shrink-0 text-brand-400">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-base mb-1">{title}</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Core Guides */}
      <section className="py-16 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-2">Technical Guides & Architecture</h2>
          <p className="text-sm text-slate-400 mb-8">
            Complete technical documentation for building adapters, registering datasets, and evaluating pipelines:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
            {[
              {
                title: 'Component Authoring Guide',
                desc: 'Subclass Component, declare requires/provides capability tokens, and implement run() and degrade() fallback paths.',
                tag: 'Components',
              },
              {
                title: 'Manifest & Plugin Registry',
                desc: 'How to write lingualdub.manifest.json files and handle conflict policies (NAMESPACED, HIGHEST_VERSION, EXPLICIT).',
                tag: 'Registry',
              },
              {
                title: 'Code-Switching & Routing',
                desc: 'Segment-authoritative language tagging and per-segment dynamic routing across heterogeneous model adapters.',
                tag: 'Code-Switch',
              },
              {
                title: 'Temporal Alignment & Speech Rate',
                desc: 'Fitting translated speech into source timing envelopes using forced alignment, duration modeling, and rate scaling.',
                tag: 'Alignment',
              },
              {
                title: 'Evaluation & Run Comparison',
                desc: 'Benchmarking WER, CER, BLEU, chrF, and speaker similarity with provenance-validated compare_runs() utilities.',
                tag: 'Evaluation',
              },
              {
                title: 'Audio-Visual Sync & Video Output',
                desc: 'Snapping segment boundaries to dialogue visual cues and generating dubbed .mp4 video artifacts with full provenance.',
                tag: 'AV-Sync',
              },
            ].map(sec => (
              <div key={sec.title} className="bg-[#0f172a] rounded-xl p-5 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-colors">
                <div>
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-slate-800 text-brand-300 border border-slate-700 inline-block mb-3">
                    {sec.tag}
                  </span>
                  <h3 className="font-bold text-white text-base mb-1.5">{sec.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{sec.desc}</p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                  <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Available in v0.1.0</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
