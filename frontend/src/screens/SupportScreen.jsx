import { useEffect, useMemo, useState } from 'react';
import {
  acceptSupportConversation,
  createSupportConversation,
  getSupportConversation,
  listSupportConversations,
  sendSupportMessage,
} from '../config/api';
import { PageTitle, StatusPill } from '../components/common';
import { toast } from '../lib/toast';

function statusTone(status) {
  if (status === 'active') return 'green';
  if (status === 'pending') return 'amber';
  if (status === 'closed') return 'neutral';
  return 'blue';
}

function statusLabel(status) {
  if (status === 'active') return 'Đang chat';
  if (status === 'pending') return 'Chờ HR nhận';
  if (status === 'closed') return 'Đã kết thúc';
  return status || 'Không rõ';
}

function ConversationList({ conversations, selectedId, onSelect, onAccept, canAccept }) {
  if (!conversations.length) {
    return <p className="text-center py-6 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-dashed border-slate-200">Chưa có yêu cầu hỗ trợ trực tiếp nào.</p>;
  }

  return (
    <div className="flex flex-col gap-3 mt-4">
      {conversations.map((item) => (
        <article className={`flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between p-4 rounded-xl border transition-all ${selectedId === item.id ? 'border-vinuni-blue bg-vinuni-blue/5 shadow-xs ring-1 ring-vinuni-blue/15' : 'border-slate-200 bg-white hover:border-vinuni-light-blue/40'}`} key={item.id}>
          <button className="flex-1 text-left bg-transparent border-none p-0 cursor-pointer flex justify-between items-start gap-3 outline-hidden" onClick={() => onSelect(item)} type="button">
            <div className="min-w-0">
              <b className="text-xs font-bold text-slate-800 block break-words sm:truncate">{item.subject}</b>
              <span className="text-[10px] text-slate-500 block break-all sm:break-normal sm:truncate mt-0.5">{item.employeeName} · {item.employeeEmail}</span>
            </div>
            <StatusPill tone={statusTone(item.status)}>{statusLabel(item.status)}</StatusPill>
          </button>
          {canAccept && item.status === 'pending' && (
            <button className="py-1.5 px-3 bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white rounded-lg text-xs font-semibold cursor-pointer shrink-0 text-center hover:opacity-90 transition-all mt-2 md:mt-0" onClick={() => onAccept(item.id)} type="button">
              Nhận chat
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

function SupportMessages({ conversation, currentUser }) {
  if (!conversation) {
    return (
      <div className="bg-slate-50/80 border border-slate-200/60 border-dashed rounded-2xl p-8 text-center flex flex-col gap-2 my-2 min-h-[250px] justify-center">
        <b className="text-sm font-bold text-slate-600">Chưa chọn phiên chat.</b>
        <p className="text-xs text-slate-400">Chọn một yêu cầu trong danh sách để xem nội dung trao đổi.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 border border-slate-100 rounded-2xl p-3 sm:p-4 md:p-5 max-h-[58vh] lg:max-h-[400px] min-h-[250px] overflow-y-auto bg-slate-50/40">
      {conversation.messages.map((message) => {
        const mine = message.senderId === currentUser.id;
        return (
          <article className={`flex flex-col gap-1 max-w-[94%] sm:max-w-[85%] rounded-xl p-3 border ${mine ? 'self-end ml-[4%] sm:ml-[8%] bg-slate-100 border-slate-200/80 rounded-br-none' : 'mr-[4%] sm:mr-[8%] bg-white border-slate-200/60 rounded-bl-none'}`} key={message.id}>
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-baseline gap-1 sm:gap-4 mb-1">
              <b className={`text-xs font-bold ${mine ? 'text-vinuni-gold' : 'text-vinuni-blue'}`}>{mine ? 'Bạn' : message.senderName}</b>
              <span className="text-[9px] text-slate-400 font-mono">{message.createdAt}</span>
            </div>
            <p className="font-sans text-xs text-slate-700 leading-relaxed m-0 whitespace-pre-wrap break-words">{message.content}</p>
          </article>
        );
      })}
    </div>
  );
}

export default function SupportScreen({ currentUser }) {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [subject, setSubject] = useState('Cần HR hỗ trợ trực tiếp');
  const [initialMessage, setInitialMessage] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isEmployee = currentUser.role === 'employee';
  const canAccept = ['hr', 'admin'].includes(currentUser.role);
  const selectedCanSend = selected?.status === 'active';

  const inboxTitle = useMemo(() => {
    if (isEmployee) return 'Yêu cầu của tôi';
    return 'Hàng chờ hỗ trợ HR';
  }, [isEmployee]);

  async function loadConversations(nextSelectedId = selected?.id) {
    const data = await listSupportConversations();
    setConversations(data);
    if (nextSelectedId) {
      const fresh = data.find((item) => item.id === nextSelectedId);
      setSelected(fresh || null);
    } else if (!selected && data.length) {
      setSelected(data[0]);
    }
  }

  useEffect(() => {
    loadConversations().catch((err) => {
      setError(err.message);
      toast.error(err.message);
    });
  }, []);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        if (selected?.id) {
          const fresh = await getSupportConversation(selected.id);
          if (selected.status === 'active' && fresh.status === 'closed') {
            setSelected(null);
          } else {
            setSelected(fresh);
          }
        }
        const data = await listSupportConversations();
        setConversations(data);
      } catch {
        // Keep the current chat visible if one polling tick fails.
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [selected]);

  async function createRequest(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const created = await createSupportConversation({ subject, message: initialMessage });
      setSelected(created);
      setInitialMessage('');
      toast.success('Đã gửi yêu cầu hỗ trợ đến HR.');
      await loadConversations(created.id);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function acceptConversation(conversationId) {
    setLoading(true);
    setError('');
    try {
      const accepted = await acceptSupportConversation(conversationId);
      setSelected(accepted);
      toast.success('Đã nhận phiên chat.');
      await loadConversations(accepted.id);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitMessage(event) {
    event.preventDefault();
    if (!message.trim() || !selected) return;
    setLoading(true);
    setError('');
    try {
      const updated = await sendSupportMessage(selected.id, message);
      setSelected(updated);
      setMessage('');
      await loadConversations(updated.id);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 items-start">
      <div className="lg:col-span-5 bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5">
        <PageTitle eyebrow="Live HR Support" title={inboxTitle}>
          {isEmployee
            ? 'Tạo yêu cầu để HR nhận chat và trao đổi trực tiếp với bạn.'
            : 'Nhận yêu cầu đang chờ, sau đó trao đổi trực tiếp với nhân viên trong khung chat.'}
        </PageTitle>

        {isEmployee && (
          <form className="flex flex-col gap-4 mb-4 pb-4 border-b border-slate-100" onSubmit={createRequest}>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Chủ đề
              <input
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Nội dung cần hỗ trợ
              <textarea
                value={initialMessage}
                onChange={(event) => setInitialMessage(event.target.value)}
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all resize-y min-h-[80px]"
                required
                rows={4}
              />
            </label>
            <button className="w-full bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-2.5 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center" disabled={loading} type="submit">
              {loading ? 'Đang gửi...' : 'Gửi yêu cầu cho HR'}
            </button>
          </form>
        )}

        {error && <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 text-center font-medium">{error}</div>}

        <ConversationList
          conversations={conversations}
          selectedId={selected?.id}
          onSelect={setSelected}
          onAccept={acceptConversation}
          canAccept={canAccept}
        />
      </div>

      <div className="lg:col-span-7 bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4 pb-4 border-b border-slate-100">
          <div className="flex-1 min-w-0">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-vinuni-light-blue block break-words sm:truncate">{selected ? selected.employeeName : 'Chưa chọn phiên'}</span>
            <h3 className="text-base font-bold text-vinuni-blue mt-0.5 break-words sm:truncate">{selected?.subject || 'Hỗ trợ trực tiếp với HR'}</h3>
            {selected && (
              <p className="text-[10px] text-slate-400 mt-1.5 block">
                Trạng thái: <b className="text-slate-600 font-semibold">{statusLabel(selected.status)}</b>
                {selected.hrName ? ` · HR phụ trách: ${selected.hrName}` : ''}
              </p>
            )}
          </div>
          {selected && <StatusPill tone={statusTone(selected.status)}>{statusLabel(selected.status)}</StatusPill>}
        </div>

        <SupportMessages conversation={selected} currentUser={currentUser} />

        {selected && selected.status === 'pending' && (
          <p className="text-center py-4 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-slate-100/60">Phiên này đang chờ HR nhận. Sau khi HR bấm nhận chat, hai bên có thể trao đổi qua lại.</p>
        )}

        {selected && selected.status === 'closed' && (
          <p className="text-center py-4 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-slate-100/60">Cuộc trò chuyện này đã kết thúc do nhân viên không gửi tin nhắn trong 2 phút.</p>
        )}

        {selectedCanSend && (
          <form className="flex flex-col md:flex-row gap-3 items-stretch md:items-end mt-2" onSubmit={submitMessage}>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Nhập tin nhắn..."
              rows={3}
              className="flex-1 w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all min-h-[70px] resize-y"
            />
            <button className="w-full md:w-auto shrink-0 bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-3 px-6 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center" disabled={loading || !message.trim()} type="submit">
              Gửi
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
