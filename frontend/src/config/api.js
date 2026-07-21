const localApiBase =
  typeof window !== 'undefined' &&
  ['127.0.0.1', 'localhost'].includes(window.location.hostname) &&
  ['5173', '5177'].includes(window.location.port)
    ? 'http://127.0.0.1:8001/api'
    : '/api';

export const API_BASE = import.meta.env.VITE_API_BASE || localApiBase;

const TOKEN_KEY = 'hr_helpdesk_token';

if (typeof window !== 'undefined') {
  try {
    const navEntries = performance.getEntriesByType("navigation");
    const isReload = navEntries.length > 0 && navEntries[0].type === 'reload';
    if (!isReload) {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  } catch (e) {
    // Fallback if performance API is not supported
  }
}

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY) || '';
}

export function saveToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseError(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return `API ${response.status} ${response.statusText}: backend dang tra ve ${contentType || 'noi dung khong xac dinh'}. Kiem tra lai API_BASE=${API_BASE}`;
  }

  try {
    const body = await response.json();
    return body.detail || body.message || response.statusText;
  } catch {
    return response.statusText || 'Unknown error';
  }
}

async function apiFetch(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...authHeaders(),
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    throw new Error(
      `Khong the ket noi toi backend. Kiem tra backend dang chay va API_BASE=${API_BASE}`,
    );
  }

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    const preview = await response.text();
    throw new Error(
      `Backend dang tra ve HTML/text thay vi JSON. Kiem tra API_BASE=${API_BASE}. Noi dung dau: ${preview.slice(0, 80)}`,
    );
  }

  return response.json();
}

export async function login(email, password) {
  const response = await apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  saveToken(response.token);
  return response.user;
}

export async function register(payload) {
  const response = await apiFetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return response;
}

export function forgotPassword(email) {
  return apiFetch('/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
}

export function getMe() {
  return apiFetch('/auth/me');
}

export function updateProfile(payload) {
  return apiFetch('/auth/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function listUsers() {
  return apiFetch('/users');
}

export function createUser(payload) {
  return apiFetch('/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateUser(userId, payload) {
  return apiFetch(`/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function deleteUser(userId) {
  return apiFetch(`/users/${userId}`, {
    method: 'DELETE',
  });
}

export function chat(payload) {
  return apiFetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: payload.query,
      useHyDE: Boolean(payload.useHyDE),
      topK: Number(payload.topK || 5),
      threshold: Number(payload.threshold || 0.3),
      searchMode: payload.searchMode || 'Hybrid',
      history: payload.history || [],
    }),
  });
}

export function listChatHistory() {
  return apiFetch('/chat/history');
}

export function retrieve(payload) {
  return apiFetch('/retrieval', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: payload.query,
      method: payload.method || 'Hybrid',
      topK: Number(payload.topK || 5),
      threshold: Number(payload.threshold || 0.3),
    }),
  });
}

export function uploadDocument(file, metadata = {}) {
  const formData = new FormData();
  formData.append('file', file);
  Object.entries(metadata).forEach(([key, value]) => formData.append(key, value ?? ''));
  return apiFetch('/upload', {
    method: 'POST',
    body: formData,
  });
}

export function listSupportConversations() {
  return apiFetch('/support/conversations');
}

export function createSupportConversation(payload) {
  return apiFetch('/support/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function acceptSupportConversation(conversationId) {
  return apiFetch(`/support/conversations/${conversationId}/accept`, {
    method: 'POST',
  });
}

export function getSupportConversation(conversationId) {
  return apiFetch(`/support/conversations/${conversationId}`);
}

export function sendSupportMessage(conversationId, content) {
  return apiFetch(`/support/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
}

export function listHrRequests() {
  return apiFetch('/hr-requests');
}

export function createLeaveRequest(payload) {
  const formData = new FormData();
  formData.append('leaveType', payload.leaveType);
  formData.append('startDate', payload.startDate);
  formData.append('endDate', payload.endDate);
  formData.append('totalDays', String(payload.totalDays));
  formData.append('reason', payload.reason);
  formData.append('contactDuringLeave', payload.contactDuringLeave || '');
  formData.append('handoverNote', payload.handoverNote || '');
  for (const file of payload.attachments || []) {
    formData.append('attachments', file);
  }
  return apiFetch('/hr-requests/leave', {
    method: 'POST',
    body: formData,
  });
}

export function updateHrRequestStatus(requestId, payload) {
  return apiFetch(`/hr-requests/${requestId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function listNotifications() {
  return apiFetch('/notifications');
}

export function markNotificationRead(notificationId) {
  return apiFetch(`/notifications/${notificationId}/read`, {
    method: 'PATCH',
  });
}

export function markAllNotificationsRead() {
  return apiFetch('/notifications/read-all', {
    method: 'PATCH',
  });
}

export function listAnnouncements() {
  return apiFetch('/announcements');
}

export function createAnnouncement(payload) {
  return apiFetch('/announcements', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateAnnouncement(announcementId, payload) {
  return apiFetch(`/announcements/${announcementId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function submitAnnouncement(announcementId) {
  return apiFetch(`/announcements/${announcementId}/submit`, { method: 'POST' });
}

export function reviewAnnouncement(announcementId, payload) {
  return apiFetch(`/announcements/${announcementId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function uploadAnnouncementAttachment(announcementId, file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch(`/announcements/${announcementId}/attachments`, { method: 'POST', body: formData });
}

export function deleteAnnouncementAttachment(announcementId, attachmentId) {
  return apiFetch(`/announcements/${announcementId}/attachments/${attachmentId}`, { method: 'DELETE' });
}

export async function getAnnouncementAttachmentBlob(announcementId, attachmentId) {
  const response = await fetch(`${API_BASE}/announcements/${announcementId}/attachments/${attachmentId}`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  return response.blob();
}

export function summarizeAnnouncementAttachment(announcementId, attachmentId) {
  return apiFetch(`/announcements/${announcementId}/attachments/${attachmentId}/summarize`, { method: 'POST' });
}

export function chatWithAnnouncementAttachment(announcementId, attachmentId, query) {
  return apiFetch(`/announcements/${announcementId}/attachments/${attachmentId}/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query }),
  });
}

export function listLeaveBalances() {
  return apiFetch('/leave-balances');
}

export function updateLeaveBalance(userId, payload) {
  return apiFetch(`/leave-balances/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
