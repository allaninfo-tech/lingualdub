import { ArrowRight, Clock, Infinity, Shield, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

const MODULES = [
  {
    title: 'Temporal Alignment',
    priority: 'Near-Term',
    dep: null,
    desc: 'Duration modelling, speech-rate control, segment fitting, and cross-lingual synchronisation. Duration models predict target speech duration from source segments for video dubbing.',
    items: ['Cross-lingual duration modelling', 'Speech-rate adaptation algorithms', 'Segment boundary fitting', 'Cross-lingual sync for dubbing'],
  },
  {
    title: 'Code-Switching',
    priority: 'Near-Term',
    dep: null,
    desc: 'Detection, representation, and per-segment routing for mixed-language speech. Handles multi-language utterances natively — a standard feature of everyday communication.',
    items: ['Per-segment language identification', 'Dynamic downstream routing', 'Mixed-language utterance representation', 'Low-resource code-switch routing'],
  },
  {
    title: 'Voice-Retention Evaluation',
    priority: 'Near-Term',
    dep: 'Prerequisite for Voice Transfer',
    desc: 'Repeatable speaker-similarity measurement and human evaluation protocols, established before automated metrics are deployed.',
    items: ['Speaker similarity metrics (MOS, SECS)', 'Human evaluation protocol design', 'Reproducible baseline establishment', 'Evaluator component interfaces'],
  },
  {
    title: 'Cross-Lingual Voice Transfer',
    priority: 'Open-Ended',
    dep: 'Requires Voice-Retention Eval',
    desc: 'Speaker representation and voice preservation across linguistic boundaries. Maintains vocal identity when translating spoken content.',
    items: ['Speaker embedding extraction', 'Cross-lingual adaptation pipelines', 'Voice preservation across language families', 'Consent-gated resource compatibility'],
  },
  {
    title: 'Audio-Visual Synchronisation',
    priority: 'Mid-Term',
    dep: 'Requires Temporal Alignment',
    desc: 'Dialogue timing and lip-sync alignment for audiovisual dubbing — the signature workload that gives LingualDub its name.',
    items: ['Lip-sync alignment models', 'Dialogue timing control', 'AV sync evaluation metrics', 'Dubbed artifact generation'],
  },
];

const priorityStyle: Record<string, string> = {
  'Near-Term': 'bg-emerald-950 border border-emerald-800 text-emerald-300',
  'Open-Ended': 'bg-blue-950 border border-blue-800 text-blue-300',
  'Mid-Term': 'bg-purple-950 border border-purple-800 text-purple-300',
};

const priorityIcon: Record<string, typeof Zap> = {
  'Near-Term': Zap,
  'Open-Ended': Infinity,
  'Mid-Term': Clock,
};

export default function Research() {
  return (
    <div className="bg-[#090d16] text-white min-h-full">
      {/* Page header */}
      <section className="border-b border-slate-800/80 py-16 bg-[#0c1220]/60">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-3">Open Investigations</p>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-5">
            Research Challenge Modules
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed max-w-3xl">
            Structured research agendas with falsifiable baselines, concrete completion criteria,
            and explicit dependency ordering.
          </p>
        </div>
      </section>

      {/* Priority Legend */}
      <section className="py-6 border-b border-slate-800/80 bg-[#0c1220]/40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap gap-3 items-center">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">Priority:</span>
            {Object.entries(priorityStyle).map(([label, style]) => {
              const Icon = priorityIcon[label];
              return (
                <span key={label} className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${style}`}>
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </span>
              );
            })}
          </div>
        </div>
      </section>

      {/* Modules */}
      <section className="py-16 border-b border-slate-800/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {MODULES.map(({ title, priority, dep, desc, items }) => {
              const Icon = priorityIcon[priority];
              return (
                <div
                  key={title}
                  className="bg-[#0f172a] rounded-2xl border border-slate-800 p-7 hover:border-slate-700 transition-all flex flex-col justify-between shadow-xl"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-4">
                      <h3 className="text-xl font-bold text-white leading-tight">{title}</h3>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold shrink-0 ${priorityStyle[priority]}`}>
                        <Icon className="w-3 h-3" />
                        {priority}
                      </span>
                    </div>

                    {dep && (
                      <div className="mb-4 flex items-center gap-2 text-xs text-brand-300 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
                        <ArrowRight className="w-3 h-3 shrink-0 text-brand-400" />
                        {dep}
                      </div>
                    )}

                    <p className="text-slate-300 text-sm leading-relaxed mb-6">{desc}</p>
                  </div>

                  <ul className="space-y-2 border-t border-slate-800/80 pt-4">
                    {items.map(item => (
                      <li key={item} className="flex items-start gap-2 text-xs text-slate-300">
                        <span className="w-1.5 h-1.5 rounded-full bg-brand-400 mt-1 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}

            {/* Ethics card */}
            <div className="bg-[#0f172a] border border-slate-800 text-white rounded-2xl p-7 flex flex-col justify-between shadow-xl">
              <div>
                <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center mb-5 text-brand-400">
                  <Shield className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">Ethical Voice Policy</h3>
                <p className="text-slate-300 text-sm leading-relaxed mb-6">
                  Voice transfer and voice-retention evaluation both process individual voice data.{' '}
                  <strong className="text-white">Consent is enforced as a structural requirement at the Resource level</strong> —
                  a voice resource without recorded consent is rejected by voice-transfer components.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 border-t border-slate-800/80 pt-4">
                  {[
                    'Consent flag on Resource',
                    'Transfer components check consent',
                    'Mandatory provenance trace',
                    'Unconsented data rejected',
                  ].map(item => (
                    <div key={item} className="flex items-start gap-2 text-xs text-slate-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-400 mt-1 shrink-0" />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-[11px] font-mono text-brand-400 mt-6 border-t border-slate-800/80 pt-3">
                Enforced via Resource.provenance.consent_verified
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Next CTA */}
      <section className="py-12 bg-[#0c1220]/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <p className="font-bold text-white">Next: Architecture</p>
            <p className="text-sm text-slate-400">Pipeline flow · Development lifecycle · Repository blueprint</p>
          </div>
          <Link
            to="/architecture"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-slate-950 bg-white hover:bg-slate-100 transition-all shadow shrink-0"
          >
            View Architecture <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
