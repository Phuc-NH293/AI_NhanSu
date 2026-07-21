import { useEffect, useRef, useState } from 'react';
import { listNotifications, markAllNotificationsRead, markNotificationRead } from '../config/api';
import { toast } from '../lib/toast';

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </svg>
  );
}

function statusTone(type) {
  if (type.endsWith('approved')) return 'bg-emerald-100 text-emerald-700';
  if (type.endsWith('rejected')) return 'bg-red-100 text-red-700';
  if (type.endsWith('needs_info')) return 'bg-amber-100 text-amber-700';
  return 'bg-sky-100 text-sky-700';
}

function statusIcon(type) {
  if (type.endsWith('approved')) return '✓';
  if (type.endsWith('rejected')) return '×';
  if (type.endsWith('needs_info')) return '!';
  return 'i';
}

function formatNotificationTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export default function NotificationBell({ onNavigate, userRole }) {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const knownIdsRef = useRef(new Set());
  const initializedRef = useRef(false);
  const panelRef = useRef(null);

  const unreadCount = notifications.filter((item) => !item.read).length;

  useEffect(() => {
    async function refresh() {
      try {
        const items = await listNotifications();
        if (initializedRef.current) {
          const newUnread = items.find((item) => !item.read && !knownIdsRef.current.has(item.id));
          if (newUnread) toast.success(newUnread.title);
        }
        knownIdsRef.current = new Set(items.map((item) => item.id));
        initializedRef.current = true;
        setNotifications(items);
      } catch {
        // Notification polling should not interrupt the employee workflow.
      }
    }

    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function closeOnOutsideClick(event) {
      if (panelRef.current && !panelRef.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener('mousedown', closeOnOutsideClick);
    return () => document.removeEventListener('mousedown', closeOnOutsideClick);
  }, []);

  async function openNotification(item) {
    if (!item.read) {
      try {
        await markNotificationRead(item.id);
        setNotifications((current) => current.map((entry) => (
          entry.id === item.id ? { ...entry, read: true } : entry
        )));
      } catch {
        toast.error('Chưa thể đánh dấu thông báo đã đọc.');
      }
    }
    setOpen(false);
    if (item.relatedType === 'hr_request') onNavigate('hrRequests');
    if (item.relatedType === 'announcement') onNavigate('announcements');
  }

  async function readAll() {
    setLoading(true);
    try {
      await markAllNotificationsRead();
      setNotifications((current) => current.map((item) => ({ ...item, read: true })));
    } catch {
      toast.error('Chưa thể đánh dấu tất cả đã đọc.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        className={`relative flex h-10 w-10 items-center justify-center rounded-xl border transition-all cursor-pointer ${open ? 'border-vinuni-light-blue bg-sky-50 text-vinuni-blue' : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-vinuni-blue'}`}
        onClick={() => setOpen((current) => !current)}
        aria-label={`Thông báo${unreadCount ? `, ${unreadCount} chưa đọc` : ''}`}
      >
        <BellIcon />
        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex min-h-5 min-w-5 items-center justify-center rounded-full border-2 border-white bg-red-500 px-1 text-[10px] font-extrabold text-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-[1200] w-[min(380px,calc(100vw-1.5rem))] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-900/15">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <b className="block text-sm text-slate-900">Thông báo</b>
              <span className="text-[11px] text-slate-400">{unreadCount} thông báo chưa đọc</span>
            </div>
            {unreadCount > 0 && (
              <button type="button" disabled={loading} onClick={readAll} className="text-[11px] font-semibold text-vinuni-blue hover:underline disabled:opacity-50 cursor-pointer">
                Đánh dấu đã đọc
              </button>
            )}
          </div>

          <div className="max-h-[420px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-400"><BellIcon /></div>
                <b className="block text-sm text-slate-600">Chưa có thông báo</b>
                <span className="mt-1 block text-xs text-slate-400">Thông tin xử lý đơn sẽ xuất hiện tại đây.</span>
              </div>
            ) : notifications.map((item) => (
              <button
                type="button"
                key={item.id}
                onClick={() => openNotification(item)}
                className={`flex w-full gap-3 border-b border-slate-100 px-4 py-3.5 text-left transition-colors last:border-b-0 hover:bg-slate-50 cursor-pointer ${item.read ? 'bg-white' : 'bg-sky-50/60'}`}
              >
                <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-extrabold ${statusTone(item.type)}`}>
                  {statusIcon(item.type)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-start gap-2">
                    <b className="flex-1 text-xs leading-relaxed text-slate-800">{item.title}</b>
                    {!item.read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-sky-500" />}
                  </span>
                  <span className="mt-1 block text-[11px] leading-relaxed text-slate-500">{item.message}</span>
                  <span className="mt-1.5 block text-[10px] text-slate-400">{formatNotificationTime(item.createdAt)}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
