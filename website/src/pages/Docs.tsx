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
            Developer & API Reference
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-4">
            Documentation
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed max-w-3xl">
            API reference, SDK integration guides, and component contracts for building and composing speech AI pipelines with LingualDub.
          </p>
        </div>
      </section>

      {/* Under Active Development Banner */}
      <section className="py-8 bg-[#0c1220] border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-brand-950 border border-brand-800/80 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
            <div className="space-y-2">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Framework Specification in Progress</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white">The LingualDub API & SDK is in Active Development</h2>
              <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                The core Python package, component schemas, and pipeline executor interfaces are currently being formalized.
                Explore the planned architecture below or contribute to the open specification on GitHub.
              </p>
            </div>
            <a
              href="https://github.com/allaninfo-tech/lingualdub"
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

      {/* Planned SDK Architecture Preview */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-2">Planned Python SDK Preview</h2>
          <p className="text-sm text-slate-400 mb-8 max-w-2xl">
            Here is a high-level preview of how the composable pipeline and registry API will look when building multilingual speech workflows:
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            {/* Code Block */}
            <div className="bg-black/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
              <div className="bg-slate-900/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  <span className="font-mono text-xs text-slate-400 ml-2">pipeline_example.py</span>
                </div>
                <span className="text-[11px] font-mono text-brand-400 font-semibold">Python 3.10+</span>
              </div>
              <pre className="p-5 font-mono text-xs sm:text-sm text-slate-200 overflow-x-auto leading-relaxed">
{`from lingualdub import Registry, Pipeline
from lingualdub.core import Language, Resource

# 1. Resolve Language & Resources
lang = Registry.get_language("lug")
voice_ref = Registry.get_resource("speaker_voice_sample")

# 2. Compose Pipeline with contract validation
pipeline = Pipeline(
    stages=[
        Registry.get_component("asr.whisper_adapted"),
        Registry.get_component("translate.nllb_transfer"),
        Registry.get_component("alignment.temporal_sync"),
        Registry.get_component("tts.vits_luganda"),
    ],
    fault_tolerance="degrade",
)

# 3. Execute Speech Dubbing Workflow
result = pipeline.run(
    audio_path="input_video.wav",
    target_language=lang,
    speaker_reference=voice_ref,
)

print(result.status)        # Status.COMPLETE
print(result.output_audio)  # "artifacts/dubbed_audio.wav"`}
              </pre>
            </div>

            {/* API Concepts */}
            <div className="space-y-4">
              {[
                {
                  icon: Code2,
                  title: 'Registry & Dynamic Discovery',
                  desc: 'Discover and load ASR, translation, TTS, and alignment models registered via manifest files without modifying core code.',
                },
                {
                  icon: Cpu,
                  title: 'Contract Validation at Assembly',
                  desc: 'Pipelines verify upstream provides and downstream requires capabilities before runtime to catch mismatched types early.',
                },
                {
                  icon: Layers,
                  title: 'Fault-Tolerant Execution',
                  desc: 'Selectable failure modes (abort, skip, degrade) ensure audio generation continues even when non-critical stages fail.',
                },
                {
                  icon: FileCode2,
                  title: 'Provenance & Consent Validation',
                  desc: 'Result objects carry cryptographic provenance metadata, ensuring voice consent policies are satisfied.',
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

      {/* Planned Modules & Guides */}
      <section className="py-16 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-white mb-2">Upcoming Documentation Sections</h2>
          <p className="text-sm text-slate-400 mb-8">
            These guides and API references will be published alongside the first public alpha release:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
            {[
              {
                title: 'Quickstart Guide',
                desc: 'Installing the package, configuring audio devices, and running your first speech-to-speech pipeline.',
                tag: 'Getting Started',
              },
              {
                title: 'Custom Component Contract',
                desc: 'How to implement the Component base class and register external ASR or TTS models via manifest.',
                tag: 'Extension',
              },
              {
                title: 'Language Metadata Registry',
                desc: 'Defining resource scarcity profiles, orthography settings, and language family affinities.',
                tag: 'Languages',
              },
              {
                title: 'Temporal Alignment API',
                desc: 'Using duration models and speech rate scaling for video dubbing and audio-visual sync.',
                tag: 'Research',
              },
              {
                title: 'Evaluator Metrics',
                desc: 'Running automated and human evaluation protocols with standardized metric outputs.',
                tag: 'Evaluation',
              },
              {
                title: 'REST / WebSocket Server',
                desc: 'Deploying LingualDub pipelines as real-time microservices for production dubbing workloads.',
                tag: 'Deployment',
              },
            ].map(sec => (
              <div key={sec.title} className="bg-[#0f172a] rounded-xl p-5 border border-slate-800 flex flex-col justify-between">
                <div>
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-slate-800 text-brand-300 border border-slate-700 inline-block mb-3">
                    {sec.tag}
                  </span>
                  <h3 className="font-bold text-white text-base mb-1.5">{sec.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{sec.desc}</p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center gap-1 text-[11px] text-slate-400 font-medium">
                  <BookOpen className="w-3.5 h-3.5 text-brand-400" />
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
