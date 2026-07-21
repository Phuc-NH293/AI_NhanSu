import { useEffect, useMemo, useState } from 'react';
import { clearToken, getMe, getToken, listSupportConversations } from './config/api';
import HrPolicyChatPanel from './components/HrPolicyChatPanel';
import { Toaster } from './lib/toast';
import { getRoleHome, getVisibleTabs, roleLabel } from './constants/navigation';
import { VinUniLogo } from './components/common';
import NotificationBell from './components/NotificationBell';
import AuthScreen from './screens/AuthScreen';
import AnnouncementsScreen from './screens/AnnouncementsScreen';
import ChatScreen from './screens/ChatScreen';
import ChatHistoryScreen from './screens/ChatHistoryScreen';
import HrRequestsScreen from './screens/HrRequestsScreen';
import { AdminHome, HrHome, UserHome } from './screens/RoleHomeScreens';
import SupportScreen from './screens/SupportScreen';
import UploadScreen from './screens/UploadScreen';
import UsersScreen from './screens/UsersScreen';

export default function App() {
  const [active, setActive] = useState('');
  const [currentUser, setCurrentUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(getToken()));
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    async function restoreSession() {
      if (!getToken()) {
        setBooting(false);
        return;
      }
      try {
        const user = await getMe();
        setCurrentUser(user);
        setActive(getRoleHome(user.role));
      } catch {
        clearToken();
      } finally {
        setBooting(false);
      }
    }
    restoreSession();
  }, []);

  const [hasPendingSupport, setHasPendingSupport] = useState(false);

  useEffect(() => {
    if (!currentUser || !['hr', 'admin'].includes(currentUser.role)) {
      setHasPendingSupport(false);
      return;
    }

    async function checkPending() {
      try {
        const conversations = await listSupportConversations();
        const pending = conversations.some(c => c.status === 'pending');
        setHasPendingSupport(pending);
      } catch (err) {
        // Silent error
      }
    }

    checkPending();
    const interval = setInterval(checkPending, 5000);
    return () => clearInterval(interval);
  }, [currentUser]);

  const visibleTabs = useMemo(() => getVisibleTabs(currentUser?.role), [currentUser?.role]);
  const activeTab = visibleTabs.find(([key]) => key === active) || visibleTabs[0];
  const canUpload = ['hr', 'admin'].includes(currentUser?.role);
  const canManageUsers = currentUser?.role === 'admin';

  useEffect(() => {
    if (currentUser && !visibleTabs.some(([key]) => key === active)) {
      setActive(getRoleHome(currentUser.role));
    }
  }, [active, currentUser, visibleTabs]);

  function handleLogin(user) {
    setCurrentUser(user);
    setActive(getRoleHome(user.role));
  }

  function logout() {
    clearToken();
    setCurrentUser(null);
    setActive('');
    setMenuOpen(false);
  }

  if (booting) {
    return (
      <>
        <Toaster richColors position="top-right" closeButton />
        <main className="min-h-screen flex items-center justify-center bg-slate-50"><p className="text-slate-500 font-medium">Đang kiểm tra phiên đăng nhập...</p></main>
      </>
    );
  }

  if (!currentUser) {
    return (
      <>
        <Toaster richColors position="top-right" closeButton />
        <AuthScreen onLogin={handleLogin} />
      </>
    );
  }

  return (
    <div className={`min-h-screen bg-slate-50 flex flex-col md:grid md:grid-cols-[288px_1fr] shell-role-${currentUser.role} ${menuOpen ? 'menu-open' : ''}`}>
      <Toaster richColors position="top-right" closeButton />
      {menuOpen && <div className="fixed inset-0 bg-vinuni-blue/40 backdrop-blur-xs z-[999] md:hidden" onClick={() => setMenuOpen(false)} />}

      <aside className={`fixed inset-y-0 left-0 h-screen w-[min(288px,86vw)] overflow-hidden bg-linear-to-b from-vinuni-blue via-[#15386d] to-vinuni-navy border-r border-vinuni-border p-4 sm:p-6 flex flex-col z-[1000] transition-transform duration-300 md:w-[288px] md:translate-x-0 md:sticky md:top-0 ${menuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-14 -left-10 h-36 w-36 rounded-full bg-white/10 blur-2xl" />
          <div className="absolute top-1/4 -right-14 h-40 w-40 rounded-full bg-vinuni-light-blue/20 blur-3xl" />
          <div className="absolute bottom-20 -left-12 h-44 w-44 rounded-full bg-vinuni-gold/10 blur-3xl" />
          <div className="absolute bottom-0 right-0 h-32 w-32 translate-x-8 translate-y-8 rounded-full bg-white/8 blur-2xl" />
        </div>

        <div className="relative z-10 flex items-center gap-3 mb-6 bg-white/8 border border-white/10 rounded-xl p-3 backdrop-blur-sm">
          <VinUniLogo className="w-10 h-10 flex-shrink-0" />
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-white leading-tight truncate">VinUni Portal</h1>
            <p className="text-[10px] text-slate-300 leading-tight truncate">Trợ lý chính sách VinUniversity</p>
          </div>
          <button
            className="md:hidden flex items-center justify-center p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-all cursor-pointer ml-auto"
            onClick={() => setMenuOpen(false)}
            type="button"
            aria-label="Đóng menu"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <nav className="relative z-10 flex flex-col gap-2 overflow-y-auto pr-1">
          {visibleTabs.map(([key, label]) => {
            const isActive = active === key;
            return (
              <button
                className={`group flex items-center text-left p-3.5 rounded-2xl border transition-all cursor-pointer w-full backdrop-blur-sm ${isActive ? 'bg-white/10 border-vinuni-gold/25 text-vinuni-gold shadow-lg shadow-slate-950/20' : 'border-white/5 text-slate-200 hover:text-vinuni-gold hover:bg-white/8 hover:border-white/12'}`}
                key={key}
                onClick={() => { setActive(key); setMenuOpen(false); }}
                type="button"
              >
                <b className="text-sm font-semibold flex items-center justify-between w-full">
                  <span>{label}</span>
                  {key === 'support' && hasPendingSupport && (
                    <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse border border-vinuni-blue" />
                  )}
                </b>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="flex-1 p-3 sm:p-4 md:p-6 lg:p-8 min-w-0 overflow-x-hidden">
        <header className="flex items-center justify-between gap-2 sm:gap-4 bg-white/80 border border-slate-200/80 rounded-2xl p-3 sm:p-4 md:px-5 md:py-4 shadow-xs mb-4 md:mb-6 backdrop-blur-md">
          <button
            className="md:hidden flex items-center justify-center p-2 rounded-lg text-vinuni-blue hover:bg-vinuni-blue/5 transition-all cursor-pointer"
            onClick={() => setMenuOpen(true)}
            type="button"
            aria-label="Mở menu"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>

          <div className="flex-1 min-w-0">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-vinuni-light-blue block truncate">AI Trợ Lý Hỏi Đáp Chính Sách Nhân Sự</span>
            <h2 className="text-base sm:text-lg md:text-xl font-bold text-vinuni-blue mt-0.5 truncate">{activeTab?.[1]}</h2>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <NotificationBell onNavigate={setActive} userRole={currentUser.role} />
            <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl px-4 py-2 max-sm:bg-transparent max-sm:border-none max-sm:p-0">
            <div className="max-sm:hidden">
              <b className="text-xs font-bold text-slate-800 block text-right">{currentUser.name}</b>
              <span className="text-[10px] text-slate-500 block text-right mt-0.5">{roleLabel(currentUser.role)}</span>
            </div>
            <button className="py-1.5 px-2.5 sm:px-3 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-all cursor-pointer whitespace-nowrap" onClick={logout} type="button">Đăng xuất</button>
            </div>
          </div>
        </header>

        {active === 'adminHome' && currentUser.role === 'admin' && (
          <AdminHome currentUser={currentUser} onNavigate={setActive} hasPendingSupport={hasPendingSupport} />
        )}
        {active === 'hrHome' && currentUser.role === 'hr' && (
          <HrHome currentUser={currentUser} onNavigate={setActive} hasPendingSupport={hasPendingSupport} />
        )}
        {active === 'userHome' && currentUser.role === 'employee' && (
          <UserHome currentUser={currentUser} onNavigate={setActive} onUpdateUser={setCurrentUser} />
        )}
        {active === 'hrRequests' && <HrRequestsScreen currentUser={currentUser} />}
        {active === 'announcements' && <AnnouncementsScreen currentUser={currentUser} />}
        {active === 'support' && <SupportScreen currentUser={currentUser} />}
        {active === 'chat' && <ChatScreen currentUser={currentUser} />}
        {active === 'chatHistory' && <ChatHistoryScreen />}
        {active === 'upload' && canUpload && <UploadScreen />}
        {active === 'users' && canManageUsers && <UsersScreen currentUser={currentUser} />}
        {active !== 'chat' && <HrPolicyChatPanel currentUser={currentUser} variant="widget" />}
      </main>
    </div>
  );
}
