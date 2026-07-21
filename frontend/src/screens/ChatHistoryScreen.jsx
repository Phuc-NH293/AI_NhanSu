import { useEffect, useState } from 'react';
import { listChatHistory } from '../config/api';
import { PageTitle, SourceList, StatusPill } from '../components/common';

function compactQuestion(query) {
  const marker = '- Câu hỏi của nhân viên:';
  const line = query.split('\n').find((item) => item.includes(marker));
  if (line) {
    return line.replace(marker, '').trim();
  }
  return query.length > 180 ? `${query.slice(0, 180)}...` : query;
}

export default function ChatHistoryScreen() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');

  async function loadHistory() {
    try {
      const data = await listChatHistory();
      setItems(data);
      setSelected((current) => current || data[0] || null);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 items-start">
      <div className="lg:col-span-5 bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5">
        <PageTitle eyebrow="AI History" title="Lịch sử hỏi đáp">
          Xem lại các câu bạn đã hỏi AI, câu trả lời của bot, nguồn tài liệu đã dùng và thời điểm hỏi.
        </PageTitle>

        {error && <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 text-center font-medium">{error}</div>}
        {!items.length && !error && <p className="text-center py-6 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-dashed border-slate-200">Chưa có lịch sử hỏi đáp nào.</p>}

        <div className="flex flex-col gap-3 mt-4">
          {items.map((item) => (
            <button
              className={`flex flex-col items-start text-left p-4 rounded-xl border transition-all cursor-pointer w-full outline-hidden ${selected?.id === item.id ? 'border-vinuni-blue bg-vinuni-blue/5 shadow-xs ring-1 ring-vinuni-blue/15' : 'border-slate-200 bg-white hover:border-vinuni-light-blue'}`}
              key={item.id}
              onClick={() => setSelected(item)}
              type="button"
            >
              <b className="text-xs font-bold text-slate-800 leading-normal block mb-1 break-words sm:truncate w-full">{compactQuestion(item.query)}</b>
              <span className="text-[10px] text-slate-400 font-mono mb-2 block">{item.createdAt}</span>
              <StatusPill tone={item.sources.length ? 'green' : 'amber'}>
                {item.sources.length} nguồn
              </StatusPill>
            </button>
          ))}
        </div>
      </div>

      <aside className="lg:col-span-7 bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5 lg:sticky lg:top-6 lg:max-h-[calc(100vh-120px)] lg:overflow-y-auto">
        {!selected && (
          <div className="bg-slate-50/80 border border-slate-200/60 border-dashed rounded-2xl p-8 text-center flex flex-col gap-2 my-2 min-h-[250px] justify-center">
            <b className="text-sm font-bold text-slate-600">Chưa chọn lịch sử.</b>
            <p className="text-xs text-slate-400">Chọn một câu hỏi bên trái để xem lại nội dung.</p>
          </div>
        )}

        {selected && (
          <div className="flex flex-col gap-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 pb-4 border-b border-slate-100">
              <div>
                <span className="text-[9px] text-slate-400 font-mono block">{selected.createdAt}</span>
                <h3 className="text-base font-bold text-vinuni-blue mt-0.5">Câu hỏi và câu trả lời</h3>
              </div>
              <StatusPill>{selected.traceId || 'history'}</StatusPill>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Câu hỏi</h4>
              <pre className="bg-slate-50 font-sans text-xs text-slate-600 leading-relaxed p-4 rounded-xl border border-slate-100/60 whitespace-pre-wrap break-words">{selected.query}</pre>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Bot trả lời</h4>
              <pre className="bg-slate-50 font-sans text-sm text-slate-800 leading-relaxed p-4 sm:p-5 rounded-2xl border border-slate-100 whitespace-pre-wrap break-words">{selected.answer}</pre>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Nguồn đã dùng</h4>
              <SourceList sources={selected.sources} />
            </div>
          </div>
        )}
      </aside>
    </section>
  );
}
