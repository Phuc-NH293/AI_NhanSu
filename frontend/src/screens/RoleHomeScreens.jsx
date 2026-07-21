import { useState } from 'react';
import { DashboardAction, PageTitle, StatusPill } from '../components/common';
import { updateProfile } from '../config/api';
import { toast } from '../lib/toast';

function FeatureCard({ icon, title, detail }) {
  return (
    <article className="flex items-start gap-4 p-4 sm:p-5 rounded-2xl border border-slate-200/70 bg-white hover:border-vinuni-light-blue/40 transition-all">
      <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-lg flex-shrink-0">{icon}</div>
      <div>
        <b className="text-sm font-bold text-slate-800 block mb-1">{title}</b>
        <span className="text-xs text-slate-500 leading-relaxed">{detail}</span>
      </div>
    </article>
  );
}

function WorkspaceHero({ badge, badgeTone, title, detail, status }) {
  const toneClasses = {
    red: 'bg-red-100 text-red-800 border-red-200',
    amber: 'bg-amber-100 text-amber-800 border-amber-200',
    blue: 'bg-blue-100 text-blue-800 border-blue-200',
  };

  return (
    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 md:gap-6 p-4 sm:p-6 rounded-2xl border border-slate-200 bg-linear-to-br from-slate-50 to-slate-100/50">
      <div className="flex-1">
        <span className={`inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border mb-2 ${toneClasses[badgeTone] || toneClasses.blue}`}>{badge}</span>
        <h3 className="text-lg font-bold text-vinuni-blue mb-1">{title}</h3>
        <p className="text-xs text-slate-500 leading-relaxed max-w-2xl">{detail}</p>
      </div>
      <StatusPill tone={badgeTone === 'red' ? 'green' : badgeTone}>{status}</StatusPill>
    </div>
  );
}

export function AdminHome({ currentUser, onNavigate }) {
  return (
    <section className="bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-6">
      <PageTitle eyebrow="Admin Workspace" title="Hệ thống Quản trị viên">
        Xin chào <strong>{currentUser.name}</strong>! Đây là không gian làm việc của quản trị viên hệ thống để quản lý tài khoản, nạp tài liệu và giám sát chất lượng trợ lý AI.
      </PageTitle>

      <WorkspaceHero
        badge="Vai trò tối cao"
        badgeTone="red"
        title="Toàn quyền hệ thống"
        detail="Kiểm soát tài khoản người dùng, phân quyền truy cập, cập nhật nguồn dữ liệu và theo dõi hoạt động AI trong toàn bộ cổng thông tin."
        status="Admin Active"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard icon="👥" title="Quản lý tài khoản" detail="Tạo mới, phân quyền, khóa hoặc cập nhật thông tin cho tài khoản nhân sự trong hệ thống." />
        <FeatureCard icon="📚" title="Kho tri thức RAG" detail="Nạp và duy trì bộ tài liệu chính sách để AI tra cứu đúng nguồn và đúng ngữ cảnh." />
        <FeatureCard icon="⚡" title="Giám sát AI Audit" detail="Theo dõi chất lượng câu trả lời, nguồn trích dẫn và các hành vi cần kiểm soát của trợ lý." />
      </div>

      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Lối tắt hành động Admin</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <DashboardAction
            action="Quản trị"
            title="Quản lý người dùng"
            detail="Thêm, sửa hoặc phân quyền tài khoản nhân viên và HR."
            tone="green"
            onClick={() => onNavigate('users')}
          />
          <DashboardAction
            action="Dữ liệu"
            title="Nạp tài liệu chính sách"
            detail="Tải lên tài liệu PDF, DOCX, Markdown hoặc bộ FAQ mới nhất cho AI."
            tone="amber"
            onClick={() => onNavigate('upload')}
          />
          <DashboardAction
            action="Kiểm thử"
            title="Trải nghiệm RAG AI"
            detail="Đặt câu hỏi thử nghiệm để kiểm tra citation và chất lượng phản hồi của trợ lý."
            tone="blue"
            onClick={() => onNavigate('chat')}
          />
        </div>
      </div>
    </section>
  );
}

export function HrHome({ currentUser, onNavigate, hasPendingSupport }) {
  return (
    <section className="bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-6">
      <PageTitle eyebrow="HR Workspace" title="Không gian vận hành HR">
        Xin chào <strong>{currentUser.name}</strong>! Đây là cổng thông tin để phòng nhân sự cập nhật chính sách, duyệt đơn và hỗ trợ nhân viên nhanh hơn.
      </PageTitle>

      <WorkspaceHero
        badge="Cổng vận hành"
        badgeTone="amber"
        title="Quản lý chính sách và đơn từ"
        detail="Cập nhật quy chế, xử lý yêu cầu từ nhân viên và dùng AI để giảm tải các câu hỏi lặp lại."
        status="HR Coordinator"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard icon="📂" title="Nạp tài liệu quy chế" detail="Cập nhật sổ tay, bảo hiểm, nghỉ phép, phúc lợi và các hướng dẫn mới nhất." />
        <FeatureCard icon="❤️" title="Chăm sóc nhân sự" detail="Theo dõi câu hỏi thường gặp và hỗ trợ nhân viên qua nhiều kênh ngay trong hệ thống." />
        <FeatureCard icon="🛡️" title="Giới hạn bảo mật" detail="HR được quản lý nghiệp vụ và chính sách nhưng không có toàn quyền như admin." />
      </div>

      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Công cụ hỗ trợ HR</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <DashboardAction
            action="Tài liệu"
            title="Cập nhật chính sách"
            detail="Đưa tài liệu mới vào kho dữ liệu để AI tra cứu theo phiên bản mới nhất."
            tone="amber"
            onClick={() => onNavigate('upload')}
          />
          <DashboardAction
            action="Đơn từ"
            title="Duyệt đơn nghỉ phép"
            detail="Xem và xử lý các đơn nghỉ phép do nhân viên gửi lên."
            tone="green"
            onClick={() => onNavigate('hrRequests')}
          />
          <DashboardAction
            action="Hỗ trợ"
            title="Phòng chat trực tuyến"
            detail="Nhận yêu cầu hỗ trợ trực tiếp từ nhân viên theo thời gian thực."
            tone="blue"
            onClick={() => onNavigate('support')}
            hasBadge={hasPendingSupport}
          />
          <DashboardAction
            action="Tra cứu"
            title="Kiểm tra chatbot chính sách"
            detail="Thử câu hỏi theo dữ liệu nội bộ để kiểm tra phản hồi của trợ lý."
            tone="green"
            onClick={() => onNavigate('chat')}
          />
        </div>
      </div>
    </section>
  );
}

export function UserHome({ currentUser, onNavigate, onUpdateUser }) {
  const [profileName, setProfileName] = useState(currentUser.name);
  const [newPassword, setNewPassword] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  async function handleUpdateProfile(event) {
    event.preventDefault();

    if (!profileName.trim()) {
      setError('Họ và tên không được để trống');
      toast.warning('Họ và tên không được để trống');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const payload = { name: profileName.trim() };

      if (newPassword) {
        if (newPassword.length < 6) {
          throw new Error('Mật khẩu phải có ít nhất 6 ký tự');
        }
        payload.password = newPassword;
      }

      const updatedUser = await updateProfile(payload);
      onUpdateUser?.(updatedUser);
      setSuccess('Cập nhật thông tin cá nhân thành công!');
      toast.success('Cập nhật thông tin cá nhân thành công!');
      setNewPassword('');
      setIsEditing(false);
    } catch (err) {
      setError(err.message || 'Có lỗi xảy ra');
      toast.error(err.message || 'Có lỗi xảy ra');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <PageTitle eyebrow="Employee Portal" title="Cổng thông tin Nhân viên">
            Xin chào <strong>{currentUser.name}</strong>! Bạn có thể tra cứu nhanh chính sách, gửi yêu cầu đến HR và theo dõi lại lịch sử hỏi đáp ngay trong cùng một nơi.
          </PageTitle>
          <button
            className={`w-full md:w-auto shrink-0 py-2 px-4 rounded-xl border border-slate-200 text-xs font-semibold hover:bg-slate-50 transition-all cursor-pointer ${isEditing ? 'bg-slate-100 text-slate-700' : 'bg-white text-slate-600'}`}
            onClick={() => {
              setIsEditing((current) => !current);
              setError('');
              setSuccess('');
            }}
            type="button"
          >
            {isEditing ? 'Hủy chỉnh sửa' : 'Sửa thông tin'}
          </button>
        </div>

        {isEditing && (
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 md:p-6 transition-all">
            <h5 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">Chỉnh sửa thông tin cá nhân</h5>
            <form onSubmit={handleUpdateProfile} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Địa chỉ email</label>
                <input
                  type="email"
                  value={currentUser.email}
                  disabled
                  className="w-full border border-slate-200 rounded-xl bg-slate-100 text-slate-400 outline-hidden px-4 py-2.5 text-sm cursor-not-allowed"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Họ và tên hiển thị</label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(event) => setProfileName(event.target.value)}
                  className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                  placeholder="Nhập họ và tên của bạn"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5 md:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Mật khẩu mới</label>
                <div className="relative w-full flex items-center">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden pl-4 pr-16 py-2.5 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                    placeholder="Để trống nếu giữ nguyên"
                  />
                  <button
                    type="button"
                    className="absolute right-3 text-slate-500 hover:text-slate-700 cursor-pointer text-xs font-semibold"
                    onClick={() => setShowPassword((current) => !current)}
                  >
                    {showPassword ? 'Ẩn' : 'Hiện'}
                  </button>
                </div>
              </div>

              <div className="md:col-span-2 flex justify-end mt-2">
                <button
                  className="bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-2.5 px-6 text-sm shadow-md shadow-vinuni-blue/10 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer"
                  disabled={loading}
                  type="submit"
                >
                  {loading ? 'Đang lưu...' : 'Lưu thay đổi'}
                </button>
              </div>
            </form>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 mt-4 text-center font-medium">{error}</div>}
          </div>
        )}

        {success && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl p-3 text-center font-medium">{success}</div>}

        <WorkspaceHero
          badge="Cổng nhân viên"
          badgeTone="blue"
          title="Tra cứu chính sách tự động"
          detail="Hỏi nhanh về nghỉ phép, bảo hiểm, lương thưởng, thủ tục và biểu mẫu nội bộ với trợ lý dùng chính dữ liệu HR đã nạp."
          status="Thành viên"
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FeatureCard icon="🔍" title="Tìm kiếm tức thì" detail="Nhận câu trả lời nhanh về thủ tục nhân sự phổ biến chỉ trong vài giây." />
          <FeatureCard icon="📌" title="Có nguồn dẫn chứng" detail="Phản hồi từ AI đi kèm trích dẫn để bạn dễ xác minh thông tin." />
          <FeatureCard icon="🔒" title="Bảo vệ thông tin" detail="Lịch sử trao đổi và thông tin cá nhân của bạn được tách biệt với tài khoản khác." />
        </div>

        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Lựa chọn tiện ích</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <DashboardAction
              action="Đơn từ"
              title="Tạo đơn xin nghỉ phép"
              detail="Mở nhanh luồng gửi đơn đến HR và theo dõi trạng thái xử lý."
              tone="green"
              onClick={() => onNavigate('hrRequests')}
            />
            <DashboardAction
              action="Hỗ trợ"
              title="Gửi yêu cầu hỗ trợ"
              detail="Kết nối với HR khi bạn cần trao đổi trực tiếp ngoài luồng chatbot."
              tone="amber"
              onClick={() => onNavigate('support')}
            />
            <DashboardAction
              action="Chat"
              title="Mở Hỏi đáp thông minh"
              detail="Dùng màn hình chat đầy đủ nếu bạn muốn hỏi dài hơn hoặc theo dõi hội thoại thoải mái hơn."
              tone="green"
              onClick={() => onNavigate('chat')}
            />
            <DashboardAction
              action="Nhật ký"
              title="Lịch sử hỏi đáp AI"
              detail="Xem lại các câu hỏi và câu trả lời mà trợ lý đã phản hồi trước đó."
              tone="blue"
              onClick={() => onNavigate('chatHistory')}
            />
          </div>
        </div>
      </section>
  );
}
