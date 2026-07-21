import { useEffect, useState } from 'react';
import { createUser, deleteUser, listUsers, updateUser } from '../config/api';
import { PageTitle, StatusPill } from '../components/common';
import { roleOptions } from '../constants/navigation';
import { toast } from '../lib/toast';

export default function UsersScreen({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ email: '', name: '', password: '', role: 'employee', department: '', annualLeaveDays: 12 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // State for editing a user inline
  const [editingUserId, setEditingUserId] = useState(null);
  const [editForm, setEditForm] = useState({ email: '', password: '', department: '', annualLeaveDays: 12 });

  // State for confirming user deletion inline
  const [deletingUserId, setDeletingUserId] = useState(null);

  async function loadUsers() {
    setLoading(true);
    setError('');
    try {
      setUsers(await listUsers());
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  function updateForm(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError('');
    try {
      await createUser(form);
      setForm({ email: '', name: '', password: '', role: 'employee', department: '', annualLeaveDays: 12 });
      toast.success('Đã tạo user.');
      await loadUsers();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  async function toggleActive(user) {
    setError('');
    try {
      await updateUser(user.id, { isActive: !user.isActive });
      toast.success(user.isActive ? 'Đã khóa user.' : 'Đã mở khóa user.');
      await loadUsers();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  async function changeRole(user, role) {
    setError('');
    try {
      await updateUser(user.id, { role });
      toast.success('Đã cập nhật vai trò user.');
      await loadUsers();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  async function confirmRemoveUser(user) {
    setError('');
    try {
      await deleteUser(user.id);
      setDeletingUserId(null);
      toast.success('Đã xóa user.');
      await loadUsers();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  function startEdit(user) {
    setEditingUserId(user.id);
    setEditForm({ email: user.email, password: '', department: user.department || '', annualLeaveDays: user.annualLeaveDays ?? 12 });
  }

  function cancelEdit() {
    setEditingUserId(null);
    setError('');
  }

  async function saveEdit(user) {
    setError('');
    if (!editForm.email.trim()) {
      setError('Email không được để trống');
      toast.warning('Email không được để trống');
      return;
    }
    try {
      const payload = {
        email: editForm.email.trim(),
        department: editForm.department.trim(),
        annualLeaveDays: Number(editForm.annualLeaveDays),
      };
      if (Number.isNaN(payload.annualLeaveDays) || payload.annualLeaveDays < 0) {
        throw new Error('Quota phép năm không hợp lệ');
      }
      if (editForm.password) {
        if (editForm.password.length < 6) {
          throw new Error('Mật khẩu phải có ít nhất 6 ký tự');
        }
        payload.password = editForm.password;
      }
      await updateUser(user.id, payload);
      setEditingUserId(null);
      toast.success('Đã cập nhật user.');
      await loadUsers();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  return (
    <section className="bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-6">
      <PageTitle eyebrow="Admin" title="Quản lý người dùng">
        Tạo tài khoản nhân viên/HR/admin, phân quyền cơ bản, sửa đổi thông tin (email, mật khẩu), khóa hoặc xóa user.
      </PageTitle>

      <form className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3 sm:gap-4 items-end bg-slate-50 border border-slate-200/50 rounded-2xl p-4 sm:p-5 mb-2" onSubmit={submit}>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
          Email
          <input
            value={form.email}
            onChange={(event) => updateForm('email', event.target.value)}
            className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
            required
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
          Tên hiển thị
          <input
            value={form.name}
            onChange={(event) => updateForm('name', event.target.value)}
            className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
            required
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
          Mật khẩu
          <input
            type="password"
            value={form.password}
            onChange={(event) => updateForm('password', event.target.value)}
            className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
            required
            minLength={6}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
          Vai trò
          <select
            value={form.role}
            onChange={(event) => updateForm('role', event.target.value)}
            className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all pr-8"
          >
            {roleOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
          Quota phép
          <input
            type="number"
            min="0"
            max="365"
            step="0.5"
            value={form.annualLeaveDays}
            onChange={(event) => updateForm('annualLeaveDays', event.target.value)}
            className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
          />
        </label>
        <button className="bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-2 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all cursor-pointer text-center h-[42px] flex items-center justify-center w-full" type="submit">Tạo user</button>
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
          Phòng ban
          <input
            value={form.department}
            onChange={(event) => updateForm('department', event.target.value)}
            className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
            placeholder="hr, finance..."
          />
        </label>
      </form>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 text-center font-medium">{error}</div>}
      {loading && <p className="text-center py-4 text-xs text-slate-400 italic">Đang tải danh sách user...</p>}

      <div className="flex flex-col gap-3">
        {users.map((user) => {
          const isEditing = user.id === editingUserId;
          const isDeleting = user.id === deletingUserId;
          return (
            <article className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-[1.5fr_1.2fr_0.8fr_1.8fr] gap-3 sm:gap-4 items-center p-4 border border-slate-200/70 rounded-2xl bg-white hover:shadow-xs transition-all" key={user.id}>
              {isEditing ? (
                <div className="flex flex-col gap-2 w-full">
                  <b className="text-sm font-bold text-slate-800">{user.name}</b>
                  <input
                    value={editForm.email}
                    onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg bg-white text-slate-900 outline-hidden px-3 py-1.5 text-xs focus:border-vinuni-light-blue transition-all"
                    placeholder="Email"
                    required
                  />
                  <input
                    type="password"
                    value={editForm.password}
                    onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg bg-white text-slate-900 outline-hidden px-3 py-1.5 text-xs focus:border-vinuni-light-blue transition-all"
                    placeholder="Mật khẩu mới (bỏ trống nếu giữ nguyên)"
                  />
                  <input
                    type="number"
                    min="0"
                    max="365"
                    step="0.5"
                    value={editForm.annualLeaveDays}
                    onChange={(e) => setEditForm({ ...editForm, annualLeaveDays: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg bg-white text-slate-900 outline-hidden px-3 py-1.5 text-xs focus:border-vinuni-light-blue transition-all"
                    placeholder="Quota phép năm"
                  />
                  <input
                    value={editForm.department}
                    onChange={(e) => setEditForm({ ...editForm, department: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg bg-white text-slate-900 outline-hidden px-3 py-1.5 text-xs focus:border-vinuni-light-blue transition-all"
                    placeholder="Phòng ban"
                  />
                </div>
              ) : (
                <div className="min-w-0">
                  <b className="text-sm font-bold text-slate-800 block break-words sm:truncate">{user.name}</b>
                  <span className="text-xs text-slate-400 block break-all sm:break-normal sm:truncate mt-0.5">{user.email}</span>
                  <span className="text-[11px] text-slate-500 block mt-1">Phòng ban: {user.department || 'Chưa gán'}</span>
                  {user.role === 'employee' && (
                    <span className="text-[11px] text-emerald-700 font-semibold block mt-1">Quota phép: {user.annualLeaveDays ?? 12} ngày/năm</span>
                  )}
                </div>
              )}

              {isDeleting ? (
                <span className="text-xs font-bold text-red-600 md:col-span-2 text-left md:text-right md:pr-4">
                  Bạn có chắc chắn muốn xóa không?
                </span>
              ) : (
                <>
                  <select
                    value={user.role}
                    onChange={(event) => changeRole(user, event.target.value)}
                    disabled={user.id === currentUser.id || isEditing}
                    className="border border-slate-200 rounded-lg bg-white text-slate-800 outline-hidden px-3 py-1.5 text-xs focus:border-vinuni-light-blue transition-all disabled:opacity-50 disabled:bg-slate-50 cursor-pointer w-full"
                  >
                    {roleOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                  </select>

                  <div className="flex justify-start md:justify-center">
                    <StatusPill tone={user.isActive ? 'green' : 'red'}>
                      {user.isActive ? 'Đang hoạt động' : 'Đã khóa'}
                    </StatusPill>
                  </div>
                </>
              )}

              <div className="flex flex-wrap items-center gap-2 justify-stretch sm:justify-end w-full">
                {isEditing && (
                  <>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white text-xs font-semibold cursor-pointer shadow-xs hover:opacity-95 transition-all" onClick={() => saveEdit(user)} type="button">
                      Lưu
                    </button>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all cursor-pointer" onClick={cancelEdit} type="button">
                      Hủy
                    </button>
                  </>
                )}

                {isDeleting && (
                  <>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg border border-red-200 bg-red-50 text-xs font-semibold text-red-600 hover:bg-red-100/50 transition-all cursor-pointer" onClick={() => confirmRemoveUser(user)} type="button">
                      Có
                    </button>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all cursor-pointer" onClick={() => setDeletingUserId(null)} type="button">
                      Không
                    </button>
                  </>
                )}

                {!isEditing && !isDeleting && (
                  <>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => startEdit(user)} type="button" disabled={user.id === currentUser.id}>
                      Sửa
                    </button>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => toggleActive(user)} type="button" disabled={user.id === currentUser.id}>
                      {user.isActive ? 'Khóa' : 'Mở khóa'}
                    </button>
                    <button className="flex-1 sm:flex-none py-1.5 px-3 rounded-lg border border-red-200 bg-red-50 text-xs font-semibold text-red-600 hover:bg-red-100/50 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed" onClick={() => setDeletingUserId(user.id)} type="button" disabled={user.id === currentUser.id}>
                      Xóa
                    </button>
                  </>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
