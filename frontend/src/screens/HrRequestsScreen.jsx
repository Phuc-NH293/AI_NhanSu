import { useEffect, useMemo, useState } from 'react';
import { createLeaveRequest, listHrRequests, listLeaveBalances, updateHrRequestStatus, updateLeaveBalance } from '../config/api';
import { PageTitle } from '../components/common';
import { HrRequestCard, initialLeaveRequestForm, LeaveRequestForm } from '../components/hrRequests';
import { toast } from '../lib/toast';

function formatDays(value) {
  const numberValue = Number(value || 0);
  return Number.isInteger(numberValue) ? String(numberValue) : numberValue.toFixed(1).replace(/\.0$/, '');
}

export default function HrRequestsScreen({ currentUser }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(initialLeaveRequestForm);
  const [files, setFiles] = useState([]);
  const [review, setReview] = useState({ status: 'approved', hrNote: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('pending');
  const [leaveBalances, setLeaveBalances] = useState([]);
  const [savingBalanceId, setSavingBalanceId] = useState('');

  const isEmployee = currentUser.role === 'employee';
  const canReview = ['hr', 'admin'].includes(currentUser.role);

  const title = useMemo(() => {
    if (isEmployee) return 'Tạo đơn gửi HR';
    return 'Quản lý đơn từ nhân sự';
  }, [isEmployee]);

  const pendingItems = useMemo(
    () => items.filter((item) => item.status === 'pending' || item.status === 'needs_info'),
    [items],
  );

  const processedItems = useMemo(
    () => items.filter((item) => item.status === 'approved' || item.status === 'rejected'),
    [items],
  );

  const displayedItems = activeTab === 'pending' ? pendingItems : processedItems;

  async function loadRequests() {
    const data = await listHrRequests();
    setItems(data);
    if (canReview) {
      setLeaveBalances(await listLeaveBalances());
    }
  }

  useEffect(() => {
    loadRequests().catch((err) => {
      setError(err.message);
      toast.error(err.message);
    });
  }, []);

  function updateForm(name, value) {
    setForm((current) => {
      const next = { ...current, [name]: value };
      if (name === 'startDate' || name === 'endDate') {
        const start = next.startDate ? new Date(next.startDate) : null;
        const end = next.endDate ? new Date(next.endDate) : null;
        if (start && end && end >= start) {
          const diffMs = end.getTime() - start.getTime();
          const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24)) + 1;
          next.totalDays = String(diffDays);
        }
      }
      return next;
    });
  }

  function updateReview(name, value) {
    setReview((current) => ({ ...current, [name]: value }));
  }

  async function submitLeaveRequest(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await createLeaveRequest({
        ...form,
        totalDays: Number(form.totalDays),
        attachments: files,
      });
      setForm(initialLeaveRequestForm);
      setFiles([]);
      setSuccess('Đã gửi đơn đến bộ phận HR.');
      toast.success('Đã gửi đơn đến bộ phận HR.');
      await loadRequests();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitReview(event, requestId) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await updateHrRequestStatus(requestId, review);
      setReview({ status: 'approved', hrNote: '' });
      setSuccess('Đã cập nhật trạng thái đơn.');
      toast.success('Đã cập nhật trạng thái đơn.');
      await loadRequests();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  function updateLeaveEntitlement(userId, value) {
    setLeaveBalances((current) =>
      current.map((item) =>
        item.userId === userId ? { ...item, annualEntitlement: value } : item,
      ),
    );
  }

  async function saveLeaveEntitlement(item) {
    setSavingBalanceId(item.userId);
    setError('');
    setSuccess('');
    try {
      const annualEntitlement = Number(item.annualEntitlement);
      if (Number.isNaN(annualEntitlement) || annualEntitlement < 0) {
        throw new Error('Quota phép năm không hợp lệ');
      }
      const updated = await updateLeaveBalance(item.userId, { annualEntitlement });
      setLeaveBalances((current) =>
        current.map((balance) => (balance.userId === updated.userId ? updated : balance)),
      );
      setSuccess('Đã cập nhật quota phép năm.');
      toast.success('Đã cập nhật quota phép năm.');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setSavingBalanceId('');
    }
  }

  return (
    <section className={isEmployee ? 'grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 items-start' : 'bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5'}>
      {isEmployee && (
        <div className="bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5">
          <PageTitle eyebrow="HR Forms" title={title}>
            Tạo đơn xin nghỉ phép với đầy đủ thời gian, lý do, bàn giao công việc và ảnh minh chứng nếu cần. Đơn sẽ gửi trực tiếp đến bộ phận HR.
          </PageTitle>
          <LeaveRequestForm
            currentUser={currentUser}
            files={files}
            form={form}
            loading={loading}
            onChange={updateForm}
            onFilesChange={(event) => setFiles(Array.from(event.target.files || []))}
            onSubmit={submitLeaveRequest}
          />
        </div>
      )}

      <div className={isEmployee ? 'bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-5' : 'flex flex-col gap-5'}>
        <PageTitle eyebrow="HR Requests" title={isEmployee ? 'Đơn đã gửi' : title}>
          {isEmployee
            ? 'Theo dõi trạng thái các đơn bạn đã gửi cho HR.'
            : 'Xem, duyệt đơn nhân viên gửi và quản lý lịch sử các đơn đã xử lý.'}
        </PageTitle>

        {canReview && (
          <div className="border border-slate-200/70 rounded-2xl bg-slate-50 p-4 md:p-5 flex flex-col gap-3">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Quản lý phép năm</h3>
                <p className="text-xs text-slate-500 mt-1">HR/Admin chỉnh quota, xem số ngày đã duyệt, đang chờ và còn lại của từng nhân viên.</p>
              </div>
              <span className="text-[11px] font-semibold text-slate-500 bg-white border border-slate-200 rounded-full px-3 py-1 w-fit">
                {leaveBalances.length} nhân viên
              </span>
            </div>

            {leaveBalances.length === 0 ? (
              <p className="text-center py-4 text-xs text-slate-400 italic bg-white rounded-xl border border-dashed border-slate-200">
                Chưa có nhân viên active để quản lý phép năm.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {leaveBalances.map((item) => {
                  const entitlement = Number(item.annualEntitlement || 0);
                  const approvedUsed = Number(item.approvedUsed || 0);
                  const pendingDays = Number(item.pendingDays || 0);
                  const previewRemaining = Math.max(entitlement - approvedUsed, 0);
                  return (
                    <article className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1.4fr_0.9fr_0.8fr_0.8fr_0.8fr_auto] gap-3 items-end bg-white border border-slate-200 rounded-xl p-3" key={item.userId}>
                      <div className="min-w-0">
                        <b className="text-sm text-slate-900 block break-words sm:truncate">{item.name}</b>
                        <span className="text-xs text-slate-400 block break-all sm:break-normal sm:truncate">{item.email}</span>
                      </div>
                      <label className="flex flex-col gap-1 text-[11px] font-semibold text-slate-500">
                        Quota năm
                        <input
                          className="w-full border border-slate-200 rounded-lg bg-white text-slate-900 outline-hidden px-3 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                          min="0"
                          max="365"
                          onChange={(event) => updateLeaveEntitlement(item.userId, event.target.value)}
                          step="0.5"
                          type="number"
                          value={item.annualEntitlement}
                        />
                      </label>
                      <div className="text-xs">
                        <span className="block text-slate-400 font-semibold">Đã duyệt</span>
                        <b className="text-slate-800">{formatDays(approvedUsed)} ngày</b>
                      </div>
                      <div className="text-xs">
                        <span className="block text-slate-400 font-semibold">Đang chờ</span>
                        <b className="text-amber-600">{formatDays(pendingDays)} ngày</b>
                      </div>
                      <div className="text-xs">
                        <span className="block text-slate-400 font-semibold">Còn lại</span>
                        <b className="text-emerald-700">{formatDays(previewRemaining)} ngày</b>
                      </div>
                      <button
                        className="h-10 px-4 rounded-lg bg-vinuni-blue text-white text-xs font-semibold shadow-xs hover:opacity-95 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-wait sm:col-span-2 lg:col-span-1"
                        disabled={savingBalanceId === item.userId}
                        onClick={() => saveLeaveEntitlement(item)}
                        type="button"
                      >
                        {savingBalanceId === item.userId ? 'Đang lưu' : 'Lưu'}
                      </button>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {canReview && (
          <div className="flex gap-2 border-b border-slate-100 pb-3 mb-2 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none]">
            <button
              className={`flex shrink-0 items-center gap-2 py-2 px-4 text-xs font-semibold rounded-xl transition-all cursor-pointer border ${activeTab === 'pending' ? 'bg-vinuni-blue/5 text-vinuni-blue border-vinuni-blue/20' : 'text-slate-500 hover:text-vinuni-blue hover:bg-slate-50 border-transparent'}`}
              onClick={() => setActiveTab('pending')}
              type="button"
            >
              <span className="text-sm">📋</span>
              Chờ xử lý
              {pendingItems.length > 0 && (
                <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-600 border border-red-200 ml-1">{pendingItems.length}</span>
              )}
            </button>
            <button
              className={`flex shrink-0 items-center gap-2 py-2 px-4 text-xs font-semibold rounded-xl transition-all cursor-pointer border ${activeTab === 'processed' ? 'bg-vinuni-blue/5 text-vinuni-blue border-vinuni-blue/20' : 'text-slate-500 hover:text-vinuni-blue hover:bg-slate-50 border-transparent'}`}
              onClick={() => setActiveTab('processed')}
              type="button"
            >
              <span className="text-sm">✅</span>
              Đã xử lý
              {processedItems.length > 0 && (
                <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-600 border border-emerald-200 ml-1">{processedItems.length}</span>
              )}
            </button>
          </div>
        )}

        {error && <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 text-center font-medium mb-2">{error}</div>}
        {success && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl p-3 text-center font-medium mb-2">{success}</div>}

        <div className="flex flex-col gap-4 mt-2">
          {canReview && displayedItems.length === 0 && (
            <p className="text-center py-6 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-dashed border-slate-200">
              {activeTab === 'pending'
                ? 'Không có đơn nào đang chờ xử lý.'
                : 'Chưa có đơn nào được xử lý.'}
            </p>
          )}
          {!canReview && items.length === 0 && (
            <p className="text-center py-6 text-xs text-slate-400 italic bg-slate-50 rounded-xl border border-dashed border-slate-200">Chưa có đơn nhân sự nào.</p>
          )}

          {canReview
            ? displayedItems.map((item) => (
                <HrRequestCard
                  canReview={activeTab === 'pending'}
                  item={item}
                  key={item.id}
                  onReviewChange={updateReview}
                  onSubmitReview={submitReview}
                  review={review}
                />
              ))
            : items.map((item) => (
                <HrRequestCard
                  canReview={false}
                  item={item}
                  key={item.id}
                  onReviewChange={updateReview}
                  onSubmitReview={submitReview}
                  review={review}
                />
              ))}
        </div>
      </div>
    </section>
  );
}
