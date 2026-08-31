import { ArrowRight, BookOpen, Cpu, ShieldCheck, Sliders } from 'lucide-react';
import { Link } from 'react-router-dom';
import GithubIcon from '../components/GithubIcon';

// Clean audio-waveform bars in modern royal blue
function WaveformHero() {
  const bars = [28, 52, 70, 85, 60, 92, 74, 48, 80, 65, 44, 78, 68, 54, 38, 74, 60, 88, 50, 66, 42, 76, 58, 84];
  return (
    <div className="flex items-center justify-center gap-1.5 h-14 mb-8" aria-hidden="true">
      {bars.map((h, i) => (
        <div
          key={i}
          className="w-1.5 rounded-full bg-brand-500 origin-center"
          style={{
            height: `${h}%`,
            animation: 'waveform 1.6s ease-in-out infinite',
            animationDelay: `${(i * 0.07).toFixed(2)}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function Home() {
  return (
    <div className="bg-[#090d16] text-white">
      {/* ── Hero ── */}
      <section className="relative pt-20 pb-24 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          
          {/* Waveform animation */}
          <WaveformHero />

          {/* Headline - Explicitly for Low-Resource Languages */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black text-white tracking-tight leading-[1.08]">
            Speech AI Infrastructure
            <br />
            <span className="text-brand-400">
              for Low-Resource Languages
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-300 leading-relaxed max-w-3xl mx-auto font-normal">
            An open, modular development framework for building, adapting, composing, and evaluating 
            speech-AI systems — standardizing pipelines so models and tools can be wired together and extended.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-4 mt-10">
            <Link
              to="/docs"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 shadow-xl transition-all"
            >
              <BookOpen className="w-4 h-4 text-slate-950" />
              Documentation
            </Link>
            <Link
              to="/overview"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 shadow transition-all"
            >
              Explore Framework
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="https://github.com/allaninfo-tech/lingualdub"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-slate-300 bg-slate-900 border border-slate-700 hover:bg-slate-800 transition-all"
            >
              <GithubIcon className="w-4 h-4 text-slate-300" />
              GitHub
            </a>
          </div>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="bg-[#0c1220] border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
            {[
              { value: '5', label: 'Core Abstractions' },
              { value: '5', label: 'Research Modules' },
              { value: '10+', label: 'Component Types' },
              { value: 'MIT', label: 'Open Source' },
            ].map(s => (
              <div key={s.label} className="group">
                <dt className="text-4xl font-black text-white">{s.value}</dt>
                <dd className="text-sm text-slate-400 mt-1 font-medium">{s.label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── Why LingualDub ── */}
      <section className="py-20 bg-[#090d16]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Stop rewriting. Start composing.
            </h2>
            <p className="mt-3 text-slate-400 text-base max-w-2xl mx-auto">
              Standardize low-resource speech pipelines with reusable modules, contract validation, and provenance tracking.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                Icon: Cpu,
                title: 'Composable Components',
                desc: 'Replaceable ASR, TTS, translation, and alignment units with explicit requires/provides contracts — verified at assembly time, not runtime.',
                tag: 'Compose-Time Safety',
              },
              {
                Icon: Sliders,
                title: 'Registry-Driven Extension',
                desc: 'New models, languages, datasets, and evaluators register via manifest without modifying core framework code.',
                tag: 'Zero Core Modifications',
              },
              {
                Icon: ShieldCheck,
                title: 'Ethical Consent Enforced',
                desc: 'Voice consent is enforced as a structural requirement at the Resource level. Unconsented data is rejected by voice transfer modules.',
                tag: 'Consent-Enforced',
              },
            ].map(({ Icon, title, desc, tag }) => (
              <div
                key={title}
                className="bg-[#0f172a] rounded-2xl p-7 border border-slate-800 hover:border-slate-700 transition-all group shadow-xl"
              >
                <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-brand-400 mb-5 group-hover:text-white transition-colors">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2.5">{title}</h3>
                <p className="text-slate-300 text-sm leading-relaxed mb-6">{desc}</p>
                <span className="text-xs font-semibold px-3 py-1 rounded-md bg-slate-900 text-brand-300 border border-slate-800">
                  {tag}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="py-16 bg-[#0c1220] border-t border-slate-800/80">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4 tracking-tight">
            Explore the Framework
          </h2>
          <p className="text-slate-300 text-base mb-8 leading-relaxed">
            Discover the 5 core abstractions, research agendas, and system architecture.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/abstractions"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 shadow transition-all"
            >
              Core Abstractions
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/docs"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-bold text-white bg-slate-800 border border-slate-700 hover:bg-slate-700 transition-all"
            >
              <BookOpen className="w-4 h-4" />
              Developer Docs
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
