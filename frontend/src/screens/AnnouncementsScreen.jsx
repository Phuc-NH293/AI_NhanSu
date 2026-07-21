import { useEffect, useMemo, useState } from 'react';
import { chatWithAnnouncementAttachment, createAnnouncement, deleteAnnouncementAttachment, getAnnouncementAttachmentBlob, listAnnouncements, reviewAnnouncement, submitAnnouncement, summarizeAnnouncementAttachment, updateAnnouncement, uploadAnnouncementAttachment } from '../config/api';
import { PageTitle, StatusPill } from '../components/common';
import { toast } from '../lib/toast';

const emptyForm = {
  title: '', content: '', category: 'holiday', priority: 'important', audienceType: 'all_employees', department: '',
};

const statusMeta = {
  draft: ['Bản nháp', 'blue'],
  pending_approval: ['Chờ Admin duyệt', 'amber'],
  changes_requested: ['Cần chỉnh sửa', 'amber'],
  rejected: ['Bị từ chối', 'red'],
  published: ['Đã phát hành', 'green'],
};

function formatDate(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}

export default function AnnouncementsScreen({ currentUser }) {
  const isHr = currentUser.role === 'hr';
  const isAdmin = currentUser.role === 'admin';
  const isEmployee = currentUser.role === 'employee';
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState('');
  const [reviewNotes, setReviewNotes] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [viewer, setViewer] = useState(null);
  const [aiPanels, setAiPanels] = useState({});
  const [selectedFiles, setSelectedFiles] = useState([]);

  const pendingCount = useMemo(() => items.filter((item) => item.status === 'pending_approval').length, [items]);

  async function refresh() {
    try {
      setItems(await listAnnouncements());
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  function editItem(item) {
    setEditingId(item.id);
    setForm({
      title: item.title,
      content: item.content,
      category: item.category,
      priority: item.priority,
      audienceType: item.audienceType,
      department: item.department || '',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function saveDraft(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const saved = editingId
        ? await updateAnnouncement(editingId, form)
        : await createAnnouncement(form);
      for (const file of selectedFiles) {
        await uploadAnnouncementAttachment(saved.id, file);
      }
      toast.success(editingId ? 'Đã cập nhật bản nháp.' : 'Đã lưu bản nháp.');
      setEditingId('');
      setForm(emptyForm);
      setSelectedFiles([]);
      await refresh();
      return saved;
    } catch (err) {
      toast.error(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  function selectPdfFiles(event) {
    const files = Array.from(event.target.files || []);
    const pdfFiles = files.filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'));
    const oversized = pdfFiles.find((file) => file.size > 20 * 1024 * 1024);
    if (oversized) {
      toast.warning(`${oversized.name} vượt quá giới hạn 20 MB.`);
    }
    setSelectedFiles((current) => [...current, ...pdfFiles.filter((file) => file.size <= 20 * 1024 * 1024)].slice(0, 5));
    event.target.value = '';
  }

  async function sendForApproval(item) {
    setLoading(true);
    try {
      await submitAnnouncement(item.id);
      toast.success('Đã gửi thông báo lên Admin duyệt.');
      await refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function review(item, action) {
    const note = (reviewNotes[item.id] || '').trim();
    if (action !== 'approve' && !note) {
      toast.warning('Vui lòng nhập lý do trước khi xử lý.');
      return;
    }
    setLoading(true);
    try {
      await reviewAnnouncement(item.id, { action, note });
      toast.success(action === 'approve' ? 'Đã duyệt và phát hành tới nhân viên.' : 'Đã gửi phản hồi cho HR.');
      setReviewNotes((current) => ({ ...current, [item.id]: '' }));
      await refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function uploadPdf(item, file) {
    if (!file) return;
    setLoading(true);
    try {
      await uploadAnnouncementAttachment(item.id, file);
      toast.success('Đã tải PDF và trích xuất nội dung.');
      await refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function removePdf(item, attachment) {
    setLoading(true);
    try {
      await deleteAnnouncementAttachment(item.id, attachment.id);
      toast.success('Đã xóa file đính kèm.');
      await refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function openPdf(item, attachment) {
    try {
      const blob = await getAnnouncementAttachmentBlob(item.id, attachment.id);
      const url = URL.createObjectURL(blob);
      setViewer({ url, fileName: attachment.fileName });
    } catch (err) {
      toast.error(err.message);
    }
  }

  function closeViewer() {
    if (viewer?.url) URL.revokeObjectURL(viewer.url);
    setViewer(null);
  }

  async function summarizePdf(item, attachment) {
    const key = `${item.id}:${attachment.id}`;
    setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), loading: true } }));
    try {
      const response = await summarizeAnnouncementAttachment(item.id, attachment.id);
      setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), loading: false, summary: response.summary } }));
    } catch (err) {
      toast.error(err.message);
      setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), loading: false } }));
    }
  }

  async function askPdf(item, attachment) {
    const key = `${item.id}:${attachment.id}`;
    const query = (aiPanels[key]?.query || '').trim();
    if (!query) return;
    setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), loading: true } }));
    try {
      const response = await chatWithAnnouncementAttachment(item.id, attachment.id, query);
      setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), loading: false, answer: response.answer } }));
    } catch (err) {
      toast.error(err.message);
      setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), loading: false } }));
    }
  }

  return (
    <section className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
      {isHr && (
        <form onSubmit={saveDraft} className="xl:col-span-5 rounded-2xl border border-slate-200/70 bg-white p-5 md:p-6 shadow-sm">
          <PageTitle eyebrow="HR Announcement" title={editingId ? 'Chỉnh sửa thông báo' : 'Tạo thông báo nội bộ'}>
            Nội dung phải được Admin duyệt trước khi gửi xuống nhân viên.
          </PageTitle>
          <div className="space-y-4">
            <label className="block text-xs font-semibold text-slate-700">Tiêu đề
              <input required maxLength={200} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3.5 py-3 text-sm outline-none focus:border-vinuni-light-blue" placeholder="Ví dụ: Lịch nghỉ lễ 30/04 và 01/05/2027" />
            </label>
            <label className="block text-xs font-semibold text-slate-700">Nội dung
              <textarea required rows={8} maxLength={10000} value={form.content} onChange={(event) => setForm({ ...form, content: event.target.value })} className="mt-1.5 w-full resize-y rounded-xl border border-slate-200 px-3.5 py-3 text-sm leading-relaxed outline-none focus:border-vinuni-light-blue" placeholder="Nhập nội dung thông báo chính thức..." />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs font-semibold text-slate-700">Loại
                <select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm">
                  <option value="holiday">Lịch nghỉ lễ</option><option value="policy">Chính sách</option><option value="training">Đào tạo</option><option value="general">Thông báo chung</option>
                </select>
              </label>
              <label className="text-xs font-semibold text-slate-700">Mức độ
                <select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm">
                  <option value="normal">Thông thường</option><option value="important">Quan trọng</option><option value="urgent">Khẩn</option>
                </select>
              </label>
            </div>
            <label className="block text-xs font-semibold text-slate-700">Đối tượng nhận
              <select value={form.audienceType} onChange={(event) => setForm({ ...form, audienceType: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-3 text-sm">
                <option value="all_employees">Toàn bộ nhân viên</option><option value="department">Theo phòng ban</option>
              </select>
            </label>
            {form.audienceType === 'department' && <input required value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} className="w-full rounded-xl border border-slate-200 px-3.5 py-3 text-sm" placeholder="Tên phòng ban chính xác" />}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div><b className="block text-xs text-slate-800">Văn bản quyết định đính kèm</b><span className="mt-1 block text-[10px] leading-relaxed text-slate-400">Chọn tối đa 5 file PDF, mỗi file không quá 20 MB. File sẽ tự tải lên khi bạn lưu bản nháp.</span></div>
                <span className="shrink-0 rounded-full bg-white px-2 py-1 text-[10px] font-bold text-slate-500">{selectedFiles.length}/5</span>
              </div>
              <label className="mt-3 flex cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white px-4 py-4 text-xs font-semibold text-slate-500 transition-colors hover:border-vinuni-light-blue hover:text-vinuni-blue">
                <input type="file" accept="application/pdf,.pdf" multiple className="hidden" disabled={loading || selectedFiles.length >= 5} onChange={selectPdfFiles} />
                📎 Chọn quyết định PDF
              </label>
              {selectedFiles.length > 0 && <div className="mt-3 space-y-2">{selectedFiles.map((file, index) => <div key={`${file.name}-${file.size}-${index}`} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"><span className="text-lg">📄</span><div className="min-w-0 flex-1"><b className="block truncate text-[11px] text-slate-700">{file.name}</b><span className="text-[10px] text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><button type="button" onClick={() => setSelectedFiles((current) => current.filter((_, fileIndex) => fileIndex !== index))} className="h-7 w-7 rounded-full text-sm text-slate-400 hover:bg-red-50 hover:text-red-600 cursor-pointer">×</button></div>)}</div>}
            </div>
            <div className="flex gap-2">
              <button disabled={loading} type="submit" className="flex-1 rounded-xl bg-vinuni-blue px-4 py-3 text-sm font-semibold text-white disabled:opacity-50 cursor-pointer">{loading ? 'Đang lưu và tải file...' : editingId ? 'Lưu chỉnh sửa' : 'Lưu bản nháp'}</button>
              {editingId && <button type="button" onClick={() => { setEditingId(''); setForm(emptyForm); setSelectedFiles([]); }} className="rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 cursor-pointer">Hủy</button>}
            </div>
          </div>
        </form>
      )}

      <div className={`${isHr ? 'xl:col-span-7' : 'xl:col-span-12'} rounded-2xl border border-slate-200/70 bg-white p-5 md:p-6 shadow-sm`}>
        <PageTitle eyebrow={isAdmin ? 'Admin Approval' : isEmployee ? 'Company News' : 'Announcement Workflow'} title={isAdmin ? `Duyệt thông báo (${pendingCount})` : isEmployee ? 'Thông báo dành cho bạn' : 'Thông báo đã tạo'}>
          {isAdmin ? 'Kiểm tra nội dung, PDF và đối tượng nhận trước khi phát hành.' : isEmployee ? 'Xem văn bản chính thức hoặc nhờ AI tóm tắt nội dung.' : 'Theo dõi trạng thái xử lý của từng thông báo.'}
        </PageTitle>
        {error && <p className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</p>}
        <div className="space-y-4">
          {items.length === 0 && <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-xs text-slate-400">Chưa có thông báo nội bộ.</p>}
          {items.map((item) => {
            const [label, tone] = statusMeta[item.status] || [item.status, 'blue'];
            const editable = isHr && ['draft', 'changes_requested'].includes(item.status);
            return (
              <article key={item.id} className={`rounded-2xl border p-4 md:p-5 ${item.status === 'pending_approval' ? 'border-amber-200 bg-amber-50/30' : 'border-slate-200 bg-white'}`}>
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="min-w-0"><h3 className="text-sm font-bold text-slate-900">{item.title}</h3><p className="mt-1 text-[11px] text-slate-400">Tạo bởi {item.createdByName} · {formatDate(item.createdAt)}</p></div>
                  <StatusPill tone={tone}>{label}</StatusPill>
                </div>
                <p className="mt-4 whitespace-pre-wrap text-xs leading-6 text-slate-600">{item.content}</p>
                <div className="mt-4 flex flex-wrap gap-2 text-[10px] text-slate-500"><span className="rounded-full bg-slate-100 px-2.5 py-1">{item.audienceType === 'all_employees' ? 'Toàn bộ nhân viên' : `Phòng ${item.department}`}</span><span className="rounded-full bg-slate-100 px-2.5 py-1">{item.priority}</span>{item.status === 'published' && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700">Đã đọc {item.readCount}/{item.recipientCount}</span>}</div>
                {item.reviewNote && <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"><b>Phản hồi Admin:</b> {item.reviewNote}</div>}
                {item.attachments?.length > 0 && <div className="mt-4 space-y-3">{item.attachments.map((attachment) => {
                  const key = `${item.id}:${attachment.id}`;
                  const ai = aiPanels[key] || {};
                  return <div key={attachment.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-3"><div className="flex-1 min-w-0"><b className="block truncate text-xs text-slate-800">📄 {attachment.fileName}</b><span className="text-[10px] text-slate-400">{attachment.pageCount || '?'} trang · {(attachment.size / 1024 / 1024).toFixed(2)} MB · {attachment.processingStatus}</span></div><div className="flex flex-wrap gap-2"><button type="button" onClick={() => openPdf(item, attachment)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-[11px] font-semibold text-slate-600 cursor-pointer">Mở PDF</button><button type="button" disabled={ai.loading} onClick={() => summarizePdf(item, attachment)} className="rounded-lg bg-vinuni-blue px-3 py-2 text-[11px] font-semibold text-white disabled:opacity-50 cursor-pointer">AI tóm tắt</button>{editable && <button type="button" onClick={() => removePdf(item, attachment)} className="rounded-lg border border-red-200 bg-white px-3 py-2 text-[11px] font-semibold text-red-600 cursor-pointer">Xóa</button>}</div></div>
                    {ai.summary && <div className="mt-3 whitespace-pre-wrap rounded-lg border border-sky-100 bg-white p-3 text-xs leading-6 text-slate-600"><b className="text-vinuni-blue">Tóm tắt AI</b><div className="mt-1">{ai.summary}</div></div>}
                    <div className="mt-3 flex gap-2"><input value={ai.query || ''} onChange={(event) => setAiPanels((current) => ({ ...current, [key]: { ...(current[key] || {}), query: event.target.value } }))} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); askPdf(item, attachment); } }} className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" placeholder="Hỏi AI về văn bản này..." /><button type="button" disabled={ai.loading || !ai.query?.trim()} onClick={() => askPdf(item, attachment)} className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40 cursor-pointer">Hỏi</button></div>
                    {ai.answer && <div className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-xs leading-6 text-slate-100">{ai.answer}</div>}
                  </div>;
                })}</div>}
                {isHr && editable && item.attachments?.length < 5 && <label className="mt-4 flex cursor-pointer items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-xs font-semibold text-slate-500 hover:border-vinuni-light-blue"><input type="file" accept="application/pdf,.pdf" className="hidden" disabled={loading} onChange={(event) => { uploadPdf(item, event.target.files?.[0]); event.target.value = ''; }} />+ Đính kèm quyết định PDF</label>}
                {isHr && editable && <div className="mt-4 flex gap-2"><button type="button" onClick={() => editItem(item)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 cursor-pointer">Chỉnh sửa</button><button disabled={loading} type="button" onClick={() => sendForApproval(item)} className="rounded-lg bg-vinuni-blue px-3 py-2 text-xs font-semibold text-white disabled:opacity-50 cursor-pointer">Gửi Admin duyệt</button></div>}
                {isAdmin && item.status === 'pending_approval' && <div className="mt-4 border-t border-slate-200 pt-4"><textarea rows={2} value={reviewNotes[item.id] || ''} onChange={(event) => setReviewNotes({ ...reviewNotes, [item.id]: event.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-xs" placeholder="Ghi chú hoặc lý do yêu cầu chỉnh sửa/từ chối..." /><div className="mt-2 flex flex-wrap gap-2"><button disabled={loading} type="button" onClick={() => review(item, 'approve')} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white cursor-pointer">Duyệt và phát hành</button><button disabled={loading} type="button" onClick={() => review(item, 'request_changes')} className="rounded-lg bg-amber-500 px-3 py-2 text-xs font-semibold text-white cursor-pointer">Yêu cầu chỉnh sửa</button><button disabled={loading} type="button" onClick={() => review(item, 'reject')} className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white cursor-pointer">Từ chối</button></div></div>}
              </article>
            );
          })}
        </div>
      </div>
      {viewer && <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-950/70 p-3 backdrop-blur-sm"><div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"><div className="flex items-center justify-between border-b border-slate-200 px-4 py-3"><b className="truncate text-sm text-slate-800">{viewer.fileName}</b><button type="button" onClick={closeViewer} className="h-9 w-9 rounded-full border border-slate-200 text-slate-500 cursor-pointer">×</button></div><iframe title={viewer.fileName} src={viewer.url} className="min-h-0 flex-1 bg-slate-100" /></div></div>}
    </section>
  );
}
