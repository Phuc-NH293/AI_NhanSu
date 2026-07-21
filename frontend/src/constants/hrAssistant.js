export const outputTypes = {
  answer: {
    label: 'Trả lời chính sách',
    hint: 'Giải thích ngắn gọn, có căn cứ và citation từ tài liệu HR.',
  },
  procedure: {
    label: 'Hướng dẫn thủ tục',
    hint: 'Các bước thực hiện, hồ sơ cần chuẩn bị, nơi tiếp nhận.',
  },
  checklist: {
    label: 'Checklist hồ sơ',
    hint: 'Danh sách giấy tờ, điều kiện, lưu ý và thời hạn nếu có.',
  },
  email: {
    label: 'Soạn mẫu email',
    hint: 'Mẫu email gửi HR/quản lý, lịch sự và đủ thông tin.',
  },
  escalation: {
    label: 'Đề xuất chuyển tiếp HR',
    hint: 'Tóm tắt ca, thông tin cần xác minh, lý do cần người phụ trách xử lý.',
  },
};

export const employeeTypes = [
  'Giảng viên cơ hữu',
  'Nhân viên hành chính',
  'Giảng viên thỉnh giảng',
  'Cộng tác viên',
  'Quản lý đơn vị',
];

export const topicOptions = [
  'Nghỉ phép',
  'Lương thưởng',
  'Bảo hiểm',
  'Hợp đồng lao động',
  'Phúc lợi',
  'Công tác phí',
  'Đào tạo nội bộ',
  'Quy trình kỷ luật/khiếu nại',
];

export const actionCards = [
  {
    type: 'answer',
    title: 'Trả lời nhanh',
    detail: 'Dựa trên tài liệu chính thức, có citation và cảnh báo khi thiếu căn cứ.',
  },
  {
    type: 'procedure',
    title: 'Hướng dẫn từng bước',
    detail: 'Biến chính sách thành quy trình dễ làm cho nhân viên.',
  },
  {
    type: 'checklist',
    title: 'Tạo checklist',
    detail: 'Điều kiện, giấy tờ, thời hạn, phòng ban phụ trách.',
  },
  {
    type: 'escalation',
    title: 'Chuyển tiếp HR',
    detail: 'Dành cho ca nhạy cảm, thiếu dữ liệu hoặc cần xác minh cá nhân.',
  },
];

export const quickStarts = [
  {
    label: 'Xin nghỉ phép',
    values: {
      topic: 'Nghỉ phép',
      question: 'Tôi muốn xin nghỉ phép 2 ngày vào tuần sau thì cần làm thủ tục gì?',
      outputType: 'procedure',
    },
  },
  {
    label: 'Bảo hiểm',
    values: {
      topic: 'Bảo hiểm',
      question: 'Chính sách BHXH, BHYT áp dụng cho nhân viên mới như thế nào?',
      outputType: 'answer',
    },
  },
  {
    label: 'Checklist hồ sơ',
    values: {
      topic: 'Hợp đồng lao động',
      question: 'Nhân viên mới cần nộp những giấy tờ gì khi nhận việc?',
      outputType: 'checklist',
    },
  },
];

export function composePrompt(form) {
  const output = outputTypes[form.outputType] || outputTypes.answer;

  return [
    'Bạn là AI Trợ Lý Hỏi Đáp Chính Sách Nhân Sự & Hỗ Trợ Nhân Viên cho môi trường đại học.',
    'Chỉ trả lời nội dung chính sách/quy trình khi có căn cứ trong tài liệu HR được cung cấp. Nếu thiếu căn cứ, nói rõ chưa tìm thấy trong tài liệu chính sách.',
    `Yêu cầu đầu ra: ${output.label}.`,
    '',
    'THÔNG TIN CA HỎI',
    `- Loại nhân sự: ${form.employeeType || 'Chưa cung cấp'}`,
    `- Chủ đề chính sách: ${form.topic || 'Chưa cung cấp'}`,
    `- Câu hỏi của nhân viên: ${form.question || 'Chưa cung cấp'}`,
    `- Ngữ cảnh bổ sung: ${form.context || 'Không có'}`,
    `- Đơn vị/phòng ban liên quan: ${form.department || 'Chưa cung cấp'}`,
    `- Mức độ khẩn/cần xử lý: ${form.urgency || 'Bình thường'}`,
    '',
    'YÊU CẦU BẮT BUỘC',
    '1. Trả lời bằng tiếng Việt có dấu, rõ ràng, thân thiện, đúng vai trò trợ lý HR nội bộ.',
    '2. Mỗi kết luận về chính sách/quy trình phải có citation dạng [tên_nguồn, loại_nguồn] nếu lấy từ tài liệu.',
    '3. Không tự bịa chính sách, không tư vấn ngoài chính sách nội bộ, không thay phòng HR ra quyết định.',
    '4. Nếu thông tin không đủ, ghi: "Chưa có căn cứ trong tài liệu chính sách đã nạp" và liệt kê thông tin cần bổ sung.',
    '5. Nếu là thủ tục, trình bày theo các bước: điều kiện, hồ sơ, nơi gửi, thời hạn xử lý, người/phòng ban phụ trách nếu nguồn có nêu.',
    '6. Nếu ca nhạy cảm như lương tranh chấp, kỷ luật, chấm dứt hợp đồng, khiếu nại, sức khỏe cá nhân hoặc dữ liệu mật, hãy đề xuất chuyển tiếp HR và chỉ tóm tắt thông tin cần xác minh.',
    '7. Kết thúc bằng mục "Nhân viên nên kiểm tra thêm" gồm các điểm còn phụ thuộc vào hồ sơ cá nhân hoặc quy định cập nhật.',
  ].join('\n');
}
