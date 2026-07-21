export const tabs = [
  ['userHome', 'Màn hình User', 'Cổng hỏi đáp cho nhân viên'],
  ['hrHome', 'Màn hình HR', 'Vận hành tài liệu và hỗ trợ nhân viên'],
  ['adminHome', 'Màn hình Admin', 'Quản trị hệ thống và phân quyền'],
  ['hrRequests', 'Đơn từ HR', 'Tạo và xử lý đơn nhân sự'],
  ['announcements', 'Thông báo nội bộ', 'HR soạn và Admin phê duyệt thông báo'],
  ['support', 'Hỗ trợ trực tiếp', 'User gửi yêu cầu, HR nhận chat'],
  ['chatHistory', 'Lịch sử hỏi đáp', 'Xem lại câu hỏi và trả lời AI'],
  ['chat', 'Hỏi đáp thông minh', 'Hỏi tự do theo tài liệu đã nạp'],
  ['upload', 'Nguồn chính sách', 'Nạp PDF, slide, biểu mẫu, quy trình'],
  ['users', 'Quản lý user', 'Tài khoản và phân quyền'],
];

export const roleOptions = [
  ['employee', 'User / Nhân viên'],
  ['hr', 'HR'],
  ['admin', 'Admin'],
];

export const roleCapabilities = {
  employee: ['userHome', 'hrRequests', 'announcements', 'support', 'chat', 'chatHistory'],
  hr: ['hrHome', 'hrRequests', 'announcements', 'support', 'chat', 'upload'],
  admin: ['adminHome', 'hrRequests', 'announcements', 'support', 'users', 'upload', 'chat', 'chatHistory'],
};

export const roleHome = {
  employee: 'userHome',
  hr: 'hrHome',
  admin: 'adminHome',
};

export function roleLabel(role) {
  return roleOptions.find(([key]) => key === role)?.[1] || role;
}

export function getVisibleTabs(role) {
  const allowed = roleCapabilities[role] || roleCapabilities.employee;
  return tabs.filter(([key]) => allowed.includes(key));
}

export function getRoleHome(role) {
  return roleHome[role] || roleHome.employee;
}
