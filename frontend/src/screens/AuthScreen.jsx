import { useEffect, useRef, useState } from 'react';
import { PageTitle, VinUniLogo } from '../components/common';
import { forgotPassword, login, register } from '../config/api';
import { toast } from '../lib/toast';

export default function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [emailError, setEmailError] = useState('');
  const loginEmailRef = useRef(null);
  const loginPasswordRef = useRef(null);

  useEffect(() => {
    if (mode !== 'login') return undefined;

    function clearLoginAutofill() {
      setEmail('');
      setPassword('');
      if (loginEmailRef.current && document.activeElement !== loginEmailRef.current) {
        loginEmailRef.current.value = '';
      }
      if (loginPasswordRef.current && document.activeElement !== loginPasswordRef.current) {
        loginPasswordRef.current.value = '';
      }
    }

    clearLoginAutofill();
    const timers = [window.setTimeout(clearLoginAutofill, 50), window.setTimeout(clearLoginAutofill, 250)];
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [mode]);

  function switchMode(nextMode) {
    setMode(nextMode);
    setError('');
    setSuccess('');
    setEmailError('');
    setEmail('');
    setPassword('');
    setShowLoginPassword(false);
    if (nextMode === 'register') {
      setName('');
    }
    setConfirmPassword('');
  }

  async function submitLogin(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const user = await login(email, password);
      toast.success('Đăng nhập thành công');
      onLogin(user);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitRegister(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      if (password !== confirmPassword) {
        throw new Error('Mật khẩu xác nhận chưa khớp');
      }
      await register({ email, name, password });
      const successMessage = 'Tài khoản đã được đăng ký thành công. Vui lòng đăng nhập.';
      toast.success(successMessage);
      setSuccess(successMessage);
      setMode('login');
      setName('');
      setPassword('');
      setConfirmPassword('');
      setShowLoginPassword(false);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitForgotPassword(event) {
    event.preventDefault();
    setError('');
    setSuccess('');
    setEmailError('');

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError('Vui lòng nhập email');
      toast.warning('Vui lòng nhập email');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setEmailError('Định dạng email không hợp lệ (Ví dụ: name@company.com)');
      toast.warning('Định dạng email không hợp lệ');
      return;
    }

    setLoading(true);
    try {
      const response = await forgotPassword(email);
      setSuccess(response.message || 'Đã ghi nhận yêu cầu đặt lại mật khẩu.');
      toast.success(response.message || 'Đã ghi nhận yêu cầu đặt lại mật khẩu.');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleEmailBlur() {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError('Vui lòng nhập email');
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(trimmedEmail)) {
        setEmailError('Định dạng email không hợp lệ (Ví dụ: name@company.com)');
      } else {
        setEmailError('');
      }
    }
  }

  const titles = {
    login: ['Đăng nhập', 'Cổng Hỏi Đáp VinUniversity'],
    register: ['Đăng ký', 'Tạo tài khoản Cán bộ / Nhân viên'],
    forgot: ['Quên mật khẩu', 'Gửi yêu cầu đặt lại mật khẩu'],
  };
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4 md:p-6">
      <section className="bg-white border-t-4 border-t-vinuni-gold rounded-2xl shadow-xl max-w-[560px] w-full p-4 sm:p-6 md:p-8 transition-all">
        <div className="flex items-center gap-4 mb-6">
          <VinUniLogo className="w-14 h-14 object-contain flex-shrink-0" />
          <div>
            <h1 className="text-2xl font-bold text-vinuni-blue tracking-tight">VinUni Portal</h1>
            <p className="text-xs text-slate-500 font-medium">Trợ lý hỏi đáp chính sách VinUniversity</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl mb-5 sm:mb-6">
          <button
            className={`py-2.5 px-3 text-center text-xs font-semibold rounded-lg transition-all duration-200 cursor-pointer ${mode === 'login' ? 'bg-white text-vinuni-blue shadow-xs border-b-2 border-b-vinuni-gold' : 'text-slate-600 hover:text-vinuni-blue'}`}
            onClick={() => switchMode('login')}
            type="button"
          >
            Đăng nhập
          </button>
          <button
            className={`py-2.5 px-3 text-center text-xs font-semibold rounded-lg transition-all duration-200 cursor-pointer ${mode === 'register' ? 'bg-white text-vinuni-blue shadow-xs border-b-2 border-b-vinuni-gold' : 'text-slate-600 hover:text-vinuni-blue'}`}
            onClick={() => switchMode('register')}
            type="button"
          >
            Đăng ký
          </button>
          <button
            className={`py-2.5 px-3 text-center text-xs font-semibold rounded-lg transition-all duration-200 cursor-pointer ${mode === 'forgot' ? 'bg-white text-vinuni-blue shadow-xs border-b-2 border-b-vinuni-gold' : 'text-slate-600 hover:text-vinuni-blue'}`}
            onClick={() => switchMode('forgot')}
            type="button"
          >
            Quên mật khẩu
          </button>
        </div>

        <PageTitle eyebrow={titles[mode][0]} title={titles[mode][1]}>
          {mode === 'login' && 'Đăng nhập theo vai trò Admin, HR hoặc User để vào đúng màn hình phân quyền.'}
          {mode === 'register' && 'Tài khoản đăng ký mới mặc định là User/Nhân viên. Quyền HR/Admin chỉ do admin cấp trong màn quản lý user.'}
          {mode === 'forgot' && 'Hệ thống sẽ đặt lại một mật khẩu ngẫu nhiên mới và gửi trực tiếp tới email của bạn.'}
        </PageTitle>

        {mode === 'login' && (
          <form className="flex flex-col gap-4" onSubmit={submitLogin} autoComplete="off">
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Email
              <input
                ref={loginEmailRef}
                type="email"
                name="vinuni-login-email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Nhập email"
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                autoComplete="off"
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Mật khẩu
              <div className="relative">
                <input
                  ref={loginPasswordRef}
                  type={showLoginPassword ? 'text' : 'password'}
                  name="vinuni-login-passcode"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Nhập mật khẩu"
                  className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden pl-4 pr-12 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-2 my-auto h-9 w-9 flex items-center justify-center rounded-lg text-slate-500 hover:text-vinuni-blue hover:bg-slate-100 transition-all cursor-pointer"
                  onClick={() => setShowLoginPassword((current) => !current)}
                  aria-label={showLoginPassword ? 'Ẩn mật khẩu' : 'Xem mật khẩu'}
                  title={showLoginPassword ? 'Ẩn mật khẩu' : 'Xem mật khẩu'}
                >
                  {showLoginPassword ? (
                    <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-5 0-9.27-3.11-11-8a11.87 11.87 0 0 1 5.06-6.06" />
                      <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c5 0 9.27 3.11 11 8a11.79 11.79 0 0 1-2.16 3.19" />
                      <path d="M14.12 14.12a3 3 0 0 1-4.24-4.24" />
                      <path d="M1 1l22 22" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </label>
            <button className="w-full bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-3 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center mt-2" disabled={loading} type="submit">
              {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
            </button>
          </form>
        )}

        {mode === 'register' && (
          <form className="flex flex-col gap-4" onSubmit={submitRegister}>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Họ tên
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                autoComplete="name"
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                autoComplete="email"
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Mật khẩu
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                autoComplete="new-password"
                minLength={6}
                required
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Xác nhận mật khẩu
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full border border-slate-200 rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:border-vinuni-light-blue focus:ring-4 focus:ring-vinuni-light-blue/10 transition-all"
                autoComplete="new-password"
                minLength={6}
                required
              />
            </label>
            <button className="w-full bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-3 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center mt-2" disabled={loading} type="submit">
              {loading ? 'Đang tạo tài khoản...' : 'Đăng ký tài khoản User'}
            </button>
          </form>
        )}

        {mode === 'forgot' && (
          <form className="flex flex-col gap-4" onSubmit={submitForgotPassword} noValidate>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
              Email tài khoản
              <input
                type="text"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (emailError) setEmailError('');
                }}
                onBlur={handleEmailBlur}
                className={`w-full border rounded-xl bg-white text-slate-900 outline-hidden px-4 py-3 text-sm focus:ring-4 transition-all ${emailError ? 'border-red-500 focus:border-red-500 focus:ring-red-500/10' : 'border-slate-200 focus:border-vinuni-light-blue focus:ring-vinuni-light-blue/10'}`}
                autoComplete="email"
              />
              {emailError && <span className="text-[11px] text-red-500 font-semibold mt-1">{emailError}</span>}
            </label>
            <button className="w-full bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-3 px-4 text-sm shadow-md shadow-vinuni-blue/15 hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center mt-2" disabled={loading} type="submit">
              {loading ? 'Đang gửi yêu cầu...' : 'Gửi yêu cầu đặt lại mật khẩu'}
            </button>
          </form>
        )}

        {error && <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 mt-4 text-center font-medium">{error}</div>}
        {success && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl p-3 mt-4 text-center font-medium">{success}</div>}
      </section>
    </main>
  );
}
