export function StatusPill({ children, tone = 'blue' }) {
  const tones = {
    blue: 'bg-vinuni-blue/10 text-vinuni-blue border border-vinuni-blue/20',
    amber: 'bg-vinuni-gold/15 text-amber-800 border border-vinuni-gold/30',
    red: 'bg-red-50 text-red-600 border border-red-100',
    green: 'bg-emerald-50 text-emerald-700 border border-emerald-100',
  };
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${tones[tone] || tones.blue}`}>{children}</span>;
}

export function PageTitle({ eyebrow, title, children }) {
  return (
    <div className="mb-6 flex flex-col gap-1.5">
      <span className="text-[10px] font-extrabold uppercase tracking-wider text-vinuni-light-blue">{eyebrow}</span>
      <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-vinuni-blue leading-tight break-words">{title}</h2>
      {children && <p className="text-xs text-slate-500 mt-1 leading-relaxed break-words">{children}</p>}
    </div>
  );
}

export function Score({ value }) {
  const raw = Number(value || 0);
  const score = raw <= 1 ? raw : Math.min(raw / 100, 1);
  const tone = score >= 0.75 ? 'green' : score >= 0.4 ? 'amber' : 'red';
  return <StatusPill tone={tone}>{score.toFixed(3)}</StatusPill>;
}

export function SourceList({ sources = [] }) {
  if (!sources.length) {
    return <p className="text-center py-8 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-dashed border-slate-200">Chưa có nguồn chính sách nào được truy xuất từ kho tài liệu.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {sources.map((source, index) => (
        <article className="bg-slate-50 border border-slate-200/60 rounded-xl p-4 transition-all hover:border-vinuni-light-blue" key={source.id || index}>
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 mb-2">
            <div className="min-w-0">
              <b className="text-xs text-slate-800 font-bold block">{source.metadata?.source || `Nguồn ${index + 1}`}</b>
              <small className="text-[11px] text-slate-400 block mt-0.5">{source.source || source.metadata?.type || 'kho chính sách nội bộ'}</small>
            </div>
            <Score value={source.score} />
          </div>
          <p className="text-xs text-slate-600 leading-relaxed font-normal whitespace-pre-wrap break-words">{source.content}</p>
        </article>
      ))}
    </div>
  );
}

export function DashboardAction({ title, detail, action, tone = 'blue', onClick, hasBadge }) {
  return (
    <button className="flex flex-col items-start text-left bg-white border border-slate-200 hover:border-vinuni-blue hover:shadow-lg hover:shadow-vinuni-blue/5 rounded-2xl p-4 sm:p-5 transition-all cursor-pointer relative min-w-0" onClick={onClick} type="button">
      <div className="mb-3 relative inline-block">
        <StatusPill tone={tone}>{action}</StatusPill>
        {hasBadge && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse border-2 border-white" />}
      </div>
      <b className="text-sm text-slate-800 font-bold mb-1 break-words">{title}</b>
      <span className="text-xs text-slate-500 leading-relaxed break-words">{detail}</span>
    </button>
  );
}

export function VinUniLogo({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ width: '42px', height: '42px', display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 }}
    >
      {/* Outer Golden Shield Border */}
      <path d="M50 5L15 20V50C15 75 50 95 50 95C50 95 85 75 85 50V20L50 5Z" fill="#0b1a30" stroke="#d2a95f" strokeWidth="6" strokeLinejoin="round"/>

      {/* Inner Shield */}
      <path d="M50 12L22 24V50C22 70 50 86 50 86C50 86 78 70 78 50V24L50 12Z" fill="#1e3b70" />

      {/* Star at the top */}
      <polygon points="50,20 53,28 62,28 55,33 57,41 50,36 43,41 45,33 38,28 47,28" fill="#d2a95f" />

      {/* Stylized Wing representation */}
      <path d="M28 40C35 40 45 46 50 56C55 46 65 40 72 40C75 40 76 43 74 45C68 53 58 60 50 76C42 60 32 53 26 45C24 43 25 40 28 40Z" fill="#d2a95f" />

      {/* Center book/pillar detail */}
      <rect x="47" y="44" width="6" height="18" rx="1" fill="#ffffff" opacity="0.95" />
    </svg>
  );
}
