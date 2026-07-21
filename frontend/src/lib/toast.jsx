import { useEffect, useState } from 'react';

const TOAST_EVENT = 'vinuni-toast';
const TOAST_DURATION_MS =2400;

function pushToast(type, message) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent(TOAST_EVENT, {
      detail: {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        duration: TOAST_DURATION_MS,
        message: String(message || ''),
        type,
      },
    }),
  );
}

export const toast = {
  success(message) {
    pushToast('success', message);
  },
  error(message) {
    pushToast('error', message);
  },
  warning(message) {
    pushToast('warning', message);
  },
  info(message) {
    pushToast('info', message);
  },
};

const toneClass = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
};

const toneDot = {
  success: 'bg-emerald-500',
  error: 'bg-red-500',
  warning: 'bg-amber-500',
  info: 'bg-sky-500',
};

const toneProgress = {
  success: 'bg-emerald-500',
  error: 'bg-red-500',
  warning: 'bg-amber-500',
  info: 'bg-sky-500',
};

export function Toaster() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    function handleToast(event) {
      const item = event.detail;
      setItems((current) => [item, ...current].slice(0, 4));
      window.setTimeout(() => {
        setItems((current) => current.filter((entry) => entry.id !== item.id));
      }, item.duration || TOAST_DURATION_MS);
    }

    window.addEventListener(TOAST_EVENT, handleToast);
    return () => window.removeEventListener(TOAST_EVENT, handleToast);
  }, []);

  if (!items.length) return null;

  return (
    <div className="fixed right-4 top-4 z-[2000] flex w-[min(380px,calc(100vw-2rem))] flex-col gap-3 pointer-events-none">
      <style>
        {`
          @keyframes vinuni-toast-progress {
            from { transform: scaleX(1); }
            to { transform: scaleX(0); }
          }
        `}
      </style>
      {items.map((item) => (
        <div
          className={`pointer-events-auto relative flex items-start gap-3 overflow-hidden rounded-xl border px-4 py-3 shadow-lg shadow-slate-900/10 backdrop-blur-md ${toneClass[item.type] || toneClass.info}`}
          key={item.id}
        >
          <span className={`mt-1 h-2.5 w-2.5 rounded-full shrink-0 ${toneDot[item.type] || toneDot.info}`} />
          <p className="m-0 flex-1 text-sm font-semibold leading-relaxed">{item.message}</p>
          <button
            aria-label="Đóng thông báo"
            className="rounded-md px-1.5 text-lg leading-none opacity-60 transition hover:bg-white/60 hover:opacity-100"
            onClick={() => setItems((current) => current.filter((entry) => entry.id !== item.id))}
            type="button"
          >
            ×
          </button>
          <span
            aria-hidden="true"
            className={`absolute inset-x-0 bottom-0 h-1 origin-left ${toneProgress[item.type] || toneProgress.info}`}
            style={{
              animation: `vinuni-toast-progress ${item.duration || TOAST_DURATION_MS}ms linear forwards`,
            }}
          />
        </div>
      ))}
    </div>
  );
}
