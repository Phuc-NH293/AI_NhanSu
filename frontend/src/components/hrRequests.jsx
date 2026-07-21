import { API_BASE, getToken } from '../config/api';
import { StatusPill } from './common';

export const leaveTypes = [
  'Nghỉ phép năm',
  'Nghỉ ốm',
  'Nghỉ việc riêng',
  'Nghỉ không lương',
  'Nghỉ thai sản/chăm sóc gia đình',
];

export const initialLeaveRequestForm = {
  leaveType: 'Nghỉ phép năm',
  startDate: '',
  endDate: '',
  totalDays: '1',
  reason: '',
  contactDuringLeave: '',
  handoverNote: '',
};

export const requestStatusOptions = [
  ['approved', 'Duyệt đơn'],
  ['needs_info', 'Yêu cầu bổ sung'],
  ['rejected', 'Từ chối'],
];

export function requestStatusLabel(status) {
  if (status === 'approved') return 'Đã duyệt';
  if (status === 'rejected') return 'Từ chối';
  if (status === 'needs_info') return 'Cần bổ sung';
  return 'Chờ HR xử lý';
}

export function requestStatusTone(status) {
  if (status === 'approved') return 'green';
  if (status === 'rejected') return 'red';
  if (status === 'needs_info') return 'amber';
  return 'blue';
}

function attachmentUrl(url) {
  if (!url) return '#';
  const token = getToken();
  const separator = url.includes('?') ? '&' : '?';
  const fullUrl = url.startsWith('http') ? url : `${API_BASE.replace(/\/api$/, '')}${url}`;
  return token ? `${fullUrl}${separator}token=${token}` : fullUrl;
}

export function LeaveRequestForm({ currentUser, form, files, loading, onChange, onFilesChange, onSubmit }) {
  return (
    <form className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4" onSubmit={onSubmit}>
      {currentUser && (
        <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 border border-slate-200/80 rounded-xl p-3 sm:p-4">
          <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
            Người gửi
            <input
              className="w-full border border-slate-200 rounded-xl bg-white/70 text-slate-500 outline-hidden px-4 py-2.5 text-sm cursor-not-allowed"
              disabled
              value={currentUser.name || currentUser.email}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
            Email
            <input
              className="w-full border border-slate-200 rounded-xl bg-white/70 text-slate-500 outline-hidden px-4 py-2.5 text-sm cursor-not-allowed"
              disabled
              value={currentUser.email}
            />
          </label>
        </div>
      )}
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Loại nghỉ phép
        <select
          value={form.leaveType}
          onChange={(event) => onChange('leaveType', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all pr-8"
        >
          {leaveTypes.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Từ ngày
        <input
          type="date"
          value={form.startDate}
          onChange={(event) => onChange('startDate', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
          required
        />
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Đến ngày
        <input
          type="date"
          value={form.endDate}
          onChange={(event) => onChange('endDate', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
          required
        />
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Số ngày nghỉ
        <input
          min="0.5"
          step="0.5"
          type="number"
          value={form.totalDays}
          onChange={(event) => onChange('totalDays', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
          required
        />
      </label>
      <label className="md:col-span-2 flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Lý do nghỉ
        <textarea
          value={form.reason}
          onChange={(event) => onChange('reason', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all resize-y min-h-[90px]"
          required
          rows={4}
        />
      </label>
      <label className="md:col-span-2 flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Liên hệ trong thời gian nghỉ
        <input
          value={form.contactDuringLeave}
          onChange={(event) => onChange('contactDuringLeave', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
          placeholder="Số điện thoại/email nếu cần"
        />
      </label>
      <label className="md:col-span-2 flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Bàn giao công việc
        <textarea
          value={form.handoverNote}
          onChange={(event) => onChange('handoverNote', event.target.value)}
          className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all resize-y min-h-[70px]"
          rows={3}
        />
      </label>
      <label className="md:col-span-2 flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
        Ảnh minh chứng nếu cần
        <input
          accept="image/png,image/jpeg,image/jpg,image/webp"
          multiple
          onChange={onFilesChange}
          type="file"
          className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 transition-all border border-dashed border-slate-300 rounded-xl p-3 bg-slate-50"
        />
        <small className="text-[10px] text-slate-400 mt-0.5">{files.length ? `${files.length} ảnh đã chọn` : 'Hỗ trợ PNG, JPG, JPEG, WEBP'}</small>
      </label>
      <button className="md:col-span-2 bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-3 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center mt-2" disabled={loading} type="submit">
        {loading ? 'Đang gửi đơn...' : 'Gửi đơn đến HR'}
      </button>
    </form>
  );
}

export function HrRequestCard({ item, canReview, review, onReviewChange, onSubmitReview }) {
  return (
    <article className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5 md:p-6 mb-5 flex flex-col gap-4 relative overflow-hidden transition-all hover:shadow-xs">
      {item.queuePosition != null && (
        <div className="absolute top-0 right-0 bg-red-100 border-l border-b border-red-200 text-red-700 px-3 py-1 flex items-center gap-1 text-[10px] font-bold rounded-bl-xl">
          <span>#{item.queuePosition}</span>
          <span>Hàng chờ</span>
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4 pb-4 border-b border-slate-200/60">
        <div className="min-w-0 pr-16 sm:pr-0">
          <b className="text-sm font-bold text-slate-800 block truncate">{item.title}</b>
          <span className="text-[10px] text-slate-500 block break-words mt-0.5">{item.employeeName} · {item.employeeEmail}</span>
        </div>
        <StatusPill tone={requestStatusTone(item.status)}>{requestStatusLabel(item.status)}</StatusPill>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 bg-white border border-slate-200/50 rounded-xl p-4 text-xs text-slate-600">
        <p className="break-words"><b>Loại nghỉ:</b> {item.leaveType}</p>
        <p className="break-words"><b>Thời gian:</b> {item.startDate} đến {item.endDate}</p>
        <p className="break-words"><b>Số ngày:</b> {item.totalDays}</p>
        <p className="break-words"><b>Ngày gửi:</b> {item.createdAt}</p>
      </div>

      <div className="flex flex-col gap-1 text-xs">
        <b className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Lý do</b>
        <p className="text-slate-600 leading-relaxed bg-white border border-slate-200/40 rounded-xl p-3 whitespace-pre-wrap break-words font-normal">{item.reason}</p>
      </div>

      {item.contactDuringLeave && (
        <div className="flex flex-col gap-1 text-xs">
          <b className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Liên hệ khi nghỉ</b>
          <p className="text-slate-600 leading-relaxed bg-white border border-slate-200/40 rounded-xl p-3 break-words font-normal">{item.contactDuringLeave}</p>
        </div>
      )}

      {item.handoverNote && (
        <div className="flex flex-col gap-1 text-xs">
          <b className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Bàn giao công việc</b>
          <p className="text-slate-600 leading-relaxed bg-white border border-slate-200/40 rounded-xl p-3 whitespace-pre-wrap break-words font-normal">{item.handoverNote}</p>
        </div>
      )}

      {item.attachments.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mt-2">
          {item.attachments.map((attachment) => (
            <a href={attachmentUrl(attachment.url)} key={attachment.id} rel="noreferrer" target="_blank" className="flex flex-col gap-1.5 border border-slate-200 rounded-xl p-2 bg-white hover:border-vinuni-light-blue transition-all group overflow-hidden">
              <img alt={attachment.fileName} src={attachmentUrl(attachment.url)} className="w-full h-20 object-cover rounded-lg" />
              <span className="text-[9px] text-slate-500 font-medium truncate block px-1 group-hover:text-vinuni-blue">{attachment.fileName}</span>
            </a>
          ))}
        </div>
      )}

      {item.hrNote && (
        <div className="bg-amber-50/50 border border-amber-200/60 rounded-xl p-4 text-xs text-slate-700 flex flex-col gap-1">
          <b className="font-bold text-amber-800 uppercase tracking-wider text-[10px]">Phản hồi HR</b>
          <p className="leading-relaxed font-normal">{item.hrNote}</p>
          {item.reviewedByName && <span className="text-[9px] text-slate-400 font-mono block mt-1">{item.reviewedByName} · {item.reviewedAt}</span>}
        </div>
      )}

      {canReview && (
        <form className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-slate-200/60 pt-4 mt-2" onSubmit={(event) => onSubmitReview(event, item.id)}>
          <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
            Trạng thái xử lý
            <select
              value={review.status}
              onChange={(event) => onReviewChange('status', event.target.value)}
              className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all pr-8"
            >
              {requestStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="md:col-span-2 flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
            Ghi chú HR
            <textarea
              value={review.hrNote}
              onChange={(event) => onReviewChange('hrNote', event.target.value)}
              className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all resize-y min-h-[70px]"
              rows={3}
            />
          </label>
          <button className="md:col-span-2 bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-2.5 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all cursor-pointer text-center mt-2" type="submit">Cập nhật đơn</button>
        </form>
      )}
    </article>
  );
}
