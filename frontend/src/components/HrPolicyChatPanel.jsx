import { useEffect, useRef, useState } from 'react';
import { chat, createLeaveRequest } from '../config/api';
import { toast } from '../lib/toast';
import { PageTitle } from './common';
import { initialLeaveRequestForm, LeaveRequestForm } from './hrRequests';

function normalizeText(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase();
}

const supportedHrTopicAliases = [
  'nghi phep', 'xin nghi', 'phep nam', 'ngay phep',
  'nghi om', 'om dau', 'bi om', 'dang om', 'bi benh', 'khong khoe',
  'giay xac nhan y te', 'bao hiem xa hoi',
  'nghi viec', 'thoi viec', 'cham dut hop dong', 'resign',
  'cham cong', 'quen cham cong', 'gio lam', 'di muon', 'tan ca',
  'lam them', 'ot', 'overtime', 'ngoai gio',
  'luong', 'thuong', 'kpi', 'luong thuong',
  'bao hiem', 'bhxh', 'bhyt', 'bhtn',
  'thu viec', 'nhan vien moi', 'onboarding', 'hoi nhap',
  'phuc loi', 'kham suc khoe', 'hoc phi', 'gui xe', 'an trua', 'phu cap',
  'dao tao', 'khoa hoc', 'nang luc',
  'phan anh', 'ho tro', 'khieu nai', 'moi truong lam viec', 'quan he lao dong',
  'cong tac', 'quyet toan', 'chi phi',
  'ung xu', 'quy tac', 'dao duc', 'chuan muc',
  'hieu suat', 'danh gia', 'muc tieu cong viec',
  'van hoa', 'gia tri cot loi', 'tin tam tri toc tinh nhan',
  'du lieu ca nhan', 'bao ve du lieu',
  'vingroup', 'vin group',
  'chinh sach', 'quy trinh', 'noi quy', 'hr portal', 'phong hr', 'nhan su', 'tai lieu',
];

function hasSupportedHrTopic(value) {
  const text = normalizeText(value);
  return supportedHrTopicAliases.some((alias) => {
    const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`(^|\\W)${escaped}(?=\\W|$)`).test(text);
  });
}

function detectLeaveRequestIntent(value) {
  const text = normalizeText(value);
  const mentionsLeave = /nghi phep|nghi om|xin nghi|don xin nghi|nghi viec rieng|nghi khong luong|nghi thai san/.test(text);
  const asksForForm = /(tao|lap|lam|dien|gui|nop|mo).{0,24}(don|form|mau)/.test(text);
  const asksToTakeLeave = /(toi|em|minh|tui|muon|can).{0,30}(xin nghi|nghi phep|nghi om|nghi viec rieng|nghi khong luong|nghi thai san)/.test(text);
  const mentionsLeaveForm = /(don|form|mau).{0,24}(nghi|xin nghi)|nghi.{0,24}(don|form|mau)/.test(text);
  return mentionsLeave && (asksForForm || asksToTakeLeave || mentionsLeaveForm);
}

function isGreetingQuery(value) {
  const text = normalizeText(value).replace(/\s+/g, ' ').trim();
  return /^(xin chao|chao ban|chao bot|chao|hello|hi|hey|alo|good morning|good afternoon|good evening)(\b|[!?.\s])/.test(text);
}

function greetingReply(currentUser) {
  const name = currentUser?.name?.trim() || 'bạn';
  return `Chào ${name}, mình là trợ lý HR. Mình có thể hỗ trợ về nghỉ phép, nghỉ việc, bảo hiểm, lương thưởng, phúc lợi và các thủ tục nội bộ. Bạn cứ hỏi tự nhiên như đang chat với HR nhé.`;
}

function isLightConversationQuery(value) {
  const text = normalizeText(value).replace(/\s+/g, ' ').trim();
  return [
    /^(cam on|cam on ban|thanks|thank you|tks|thank|ok|oke|okay|okela|duoc|duoc roi|hieu roi|biet roi|ro roi|toi hieu roi|minh hieu roi|tam on|on roi|uh|u|um|vang|da|yes|yep|khong can|khong can nua|ko can|ko can nua|k can|k can nua|thoi duoc roi)[!?.\s]*$/,
    /^(ban la ai|ai day|ban ten gi|gioi thieu ve ban)(\b|[!?.\s])/,
    /^(ban ho tro gi|ban giup duoc gi|ban lam duoc gi|co the giup gi|giup toi voi|minh muon hoi chut)(\b|[!?.\s])/,
    /^(ban khoe khong|hom nay the nao|noi chuyen chut)(\b|[!?.\s])/,
  ].some((pattern) => pattern.test(text));
}

function lightConversationReply(currentUser, value) {
  const text = normalizeText(value).replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  const name = currentUser?.name?.trim() || 'bạn';

  if (/^(cam on|cam on ban|thanks|thank you|tks|thank)$/.test(text)) {
    return 'Không có gì nhé. Khi nào cần hỏi thêm, bạn cứ nhắn mình.';
  }

  if (/^(khong can|khong can nua|ko can|ko can nua|k can|k can nua|thoi duoc roi)$/.test(text)) {
    return 'Ok, mình dừng tại đây nhé. Khi nào cần hỗ trợ thêm, bạn cứ nhắn mình.';
  }

  if (/^(ok|oke|okay|okela|duoc|duoc roi|hieu roi|biet roi|ro roi|toi hieu roi|minh hieu roi|tam on|on roi|uh|u|um|vang|da|yes|yep)$/.test(text)) {
    return 'Ok nhé. Nếu cần làm rõ thêm phần vừa trao đổi, bạn cứ nhắn tiếp mình.';
  }

  if (/ban la ai|ai day|ban ten gi|gioi thieu ve ban/.test(text)) {
    return 'Mình là trợ lý HR nội bộ. Mình hỗ trợ giải đáp chính sách, thủ tục nhân sự, hướng dẫn xin nghỉ và giúp bạn chuẩn bị thông tin trước khi làm việc với HR.';
  }

  if (/ban khoe khong|hom nay the nao|noi chuyen chut/.test(text)) {
    return `Mình vẫn sẵn sàng hỗ trợ đây ${name}. Nếu bạn có câu hỏi về HR, cứ nói tự nhiên như đang nhắn với nhân sự nhé.`;
  }

  return 'Mình có thể hỗ trợ về nghỉ phép, nghỉ việc, bảo hiểm, lương thưởng, phúc lợi, hồ sơ nhân sự và các thủ tục nội bộ. Bạn muốn bắt đầu từ nội dung nào, mình đi cùng bạn luôn.';
}

function isCancelMessage(value) {
  const text = normalizeText(value)
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const exactCommands = new Set([
    'huy', 'huy don', 'dung', 'dung lai', 'thoi', 'bo qua', 'bo don',
    'cancel', 'khong can', 'khong can nua', 'ko can', 'ko can nua',
    'k can', 'k can nua',
  ]);
  if (exactCommands.has(text)) return true;

  const optionalPrefix = '(?:ok|oke|okay)?\\s*(?:t|toi|minh|em)?\\s*';
  const cancelPatterns = [
    new RegExp(`^${optionalPrefix}(?:khong|ko|k)\\s+(?:muon|can)(?:\\s+(?:lam|tao|dien|gui)(?:\\s+don)?)?\\s+nua$`),
    new RegExp(`^${optionalPrefix}(?:huy|dung|bo)(?:\\s+lai)?(?:\\s+(?:tao\\s+)?don)?$`),
    new RegExp(`^${optionalPrefix}thoi(?:\\s+(?:khong|ko|k)\\s+(?:lam|tao|dien|gui)(?:\\s+don)?\\s+nua)?$`),
  ];

  return cancelPatterns.some((pattern) => pattern.test(text));
}

function isCasualPersonalActivityQuery(value) {
  const text = normalizeText(value);
  return /buon ia|mac ia|muon ia|di ia|di i|di cau|di ngoai|di dai tien|di dai|di tieu|di te|buon di ve sinh|mac di ve sinh|di ve sinh|di toilet|di wc|vao wc|nha ve sinh|restroom/.test(text);
}

function isAmbiguousContextQuery(value) {
  const text = normalizeText(value).replace(/\s+/g, ' ').trim();
  const referencesMissingContext = /\b(truong hop nay|truong hop do|truong hop tren|viec nay|cai nay|cai do|van de nay|nhu vay|nhu the|the nay|the do|case nay)\b/.test(text);
  const asksDecision = /\b(co can|can khong|co phai|phai khong|nen|xu ly|chuyen tiep|bao ai|hoi ai|duoc khong|co duoc)\b/.test(text);
  const hasConcreteDetail = /\b(nghi phep|nghi om|nghi viec|bao hiem|bhxh|bhyt|cham cong|di muon|ot|lam them|luong|thuong|hop dong|thu viec|cong tac|dao tao|ky luat|khieu nai|phuc loi|ngay|tu ngay|\d{1,2}[\/.-]\d{1,2}|\d+\s*(ngay|gio|thang))\b/.test(text);
  return referencesMissingContext && asksDecision && !hasConcreteDetail;
}

function refusalReply() {
  return 'Mình hiện chỉ hỗ trợ các câu hỏi liên quan đến chính sách, thủ tục và nghiệp vụ HR nội bộ. Bạn thử hỏi lại theo hướng nhân sự nhé.';
}

function clarificationReply() {
  return [
    'Mình cần thêm một chút thông tin để trả lời đúng trường hợp của bạn.',
    '',
    'Bạn giúp mình bổ sung ngắn gọn các ý sau nhé:',
    '- Bạn đang hỏi về nhóm nào: nghỉ phép, nghỉ ốm, chấm công, OT, lương thưởng, bảo hiểm, hợp đồng, phúc lợi hay khiếu nại?',
    '- Tình huống cụ thể đang xảy ra là gì?',
    '- Có mốc thời gian, số ngày, số giờ hoặc giấy tờ liên quan không?',
    '- Bạn muốn hỏi thủ tục cần làm, quyền lợi áp dụng hay có cần chuyển tiếp HR không?',
  ].join('\n');
}

function inferLeaveType(value) {
  const text = normalizeText(value);
  if (text.includes('nghi om') || text.includes('benh')) return 'Nghỉ ốm';
  if (text.includes('viec rieng')) return 'Nghỉ việc riêng';
  if (text.includes('khong luong')) return 'Nghỉ không lương';
  if (text.includes('thai san') || text.includes('cham soc gia dinh')) return 'Nghỉ thai sản/chăm sóc gia đình';
  return 'Nghỉ phép năm';
}

function normalizeYear(year) {
  if (!year) return new Date().getFullYear();
  const parsed = Number(year);
  if (parsed < 100) return 2000 + parsed;
  return parsed;
}

function toDateInput(day, month, year) {
  const date = new Date(normalizeYear(year), Number(month) - 1, Number(day));
  if (
    date.getFullYear() !== normalizeYear(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    return '';
  }

  const yyyy = String(date.getFullYear());
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function inclusiveDays(startDate, endDate) {
  if (!startDate || !endDate) return '';
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  if (end < start) return '';
  const diffMs = end.getTime() - start.getTime();
  return String(Math.round(diffMs / (1000 * 60 * 60 * 24)) + 1);
}

function parseLeaveDateRange(value) {
  const text = normalizeText(value).replace(/\s+/g, ' ');

  let match = text.match(/(?:tu ngay|tu)?\s*(\d{1,2})[\/.-](\d{1,2})(?:[\/.-](\d{2,4}))?\s*(?:-|den|toi|qua)\s*(?:ngay)?\s*(\d{1,2})(?:[\/.-](\d{1,2}))?(?:[\/.-](\d{2,4}))?/);
  if (match) {
    const [, startDay, startMonth, startYear, endDay, endMonth, endYear] = match;
    const finalEndMonth = endMonth || startMonth;
    const finalStartYear = normalizeYear(startYear || endYear);
    let finalEndYear = normalizeYear(endYear || startYear || finalStartYear);
    const startDate = toDateInput(startDay, startMonth, finalStartYear);
    let endDate = toDateInput(endDay, finalEndMonth, finalEndYear);
    if (startDate && endDate && endDate < startDate && !endYear) {
      finalEndYear += 1;
      endDate = toDateInput(endDay, finalEndMonth, finalEndYear);
    }
    const totalDays = inclusiveDays(startDate, endDate);
    return totalDays ? { startDate, endDate, totalDays } : {};
  }

  match = text.match(/(?:tu ngay|tu)?\s*(\d{1,2})\s*-\s*(\d{1,2})[\/.-](\d{1,2})(?:[\/.-](\d{2,4}))?/);
  if (match) {
    const [, startDay, endDay, month, year] = match;
    const finalYear = normalizeYear(year);
    const startDate = toDateInput(startDay, month, finalYear);
    const endDate = toDateInput(endDay, month, finalYear);
    const totalDays = inclusiveDays(startDate, endDate);
    return totalDays ? { startDate, endDate, totalDays } : {};
  }

  match = text.match(/(?:ngay|hom)?\s*(\d{1,2})[\/.-](\d{1,2})(?:[\/.-](\d{2,4}))?/);
  if (match) {
    const [, day, month, year] = match;
    const date = toDateInput(day, month, normalizeYear(year));
    return date ? { startDate: date, endDate: date, totalDays: '1' } : {};
  }

  return {};
}

function parseLeaveDuration(value) {
  const text = normalizeText(value);
  const match = text.match(/(\d+(?:[.,]\d+)?)\s*(ngay|buoi)/);
  if (!match) return '';
  const amount = match[1].replace(',', '.');
  return match[2] === 'buoi' ? String(Number(amount) * 0.5) : amount;
}

function parseLeaveReason(value) {
  const match = value.match(/\b(?:vì|do|bởi vì)\b(.+)/i);
  return match ? match[1].trim().replace(/^[,:-]\s*/, '') : '';
}

function parseHandoverNote(value) {
  const match = value.match(/\b(?:bàn giao|ban giao)\b(.+)/i);
  return match ? match[1].trim().replace(/^[,:-]\s*/, '') : '';
}

function hasExplicitNoHandover(value) {
  return /^(khong|khong co|khong can|khong co ban giao|khong ban giao|no|none)$/i.test(normalizeText(value).trim());
}

function createLeaveDraft(query, currentUser) {
  const dateRange = parseLeaveDateRange(query);
  const totalDays = dateRange.totalDays || parseLeaveDuration(query) || initialLeaveRequestForm.totalDays;
  return {
    ...initialLeaveRequestForm,
    ...dateRange,
    totalDays,
    leaveType: inferLeaveType(query),
    reason: parseLeaveReason(query),
    contactDuringLeave: currentUser?.email || '',
    handoverNote: parseHandoverNote(query),
  };
}

function buildLeaveSummary(draft) {
  const parts = [
    `Loại nghỉ: ${draft.leaveType}`,
    draft.startDate && draft.endDate ? `Thời gian: ${draft.startDate} đến ${draft.endDate}` : null,
    draft.totalDays ? `Số ngày: ${draft.totalDays}` : null,
    draft.reason ? `Lý do: ${draft.reason}` : null,
    draft.handoverNote ? `Bàn giao: ${draft.handoverNote}` : null,
  ].filter(Boolean);
  return parts.join('\n');
}

function createLeaveIntake(query, currentUser) {
  return {
    draft: createLeaveDraft(query, currentUser),
    askedHandover: Boolean(parseHandoverNote(query)),
    pendingStep: null,
  };
}

function nextLeavePrompt(intake) {
  const { draft } = intake;
  if (!draft.startDate || !draft.endDate) {
    return {
      state: { ...intake, pendingStep: 'dates' },
      message: 'Mình sẽ tạo đơn nghỉ giúp bạn. Trước hết, bạn cho mình xin khoảng thời gian nghỉ theo dạng `dd/mm` hoặc `dd/mm/yyyy - dd/mm/yyyy` nhé.',
      ready: false,
    };
  }

  if (!draft.reason.trim()) {
    return {
      state: { ...intake, pendingStep: 'reason' },
      message: 'Mình đã có thời gian nghỉ rồi. Bạn muốn ghi lý do nghỉ là gì?',
      ready: false,
    };
  }

  if (!intake.askedHandover) {
    return {
      state: { ...intake, askedHandover: true, pendingStep: 'handover' },
      message: 'Bạn có cần ghi chú bàn giao công việc không? Bạn có thể trả lời ngắn gọn, hoặc nhập `không có`.',
      ready: false,
    };
  }

  return {
    state: { ...intake, pendingStep: 'ready' },
    message: [
      'Mình đã gom thông tin và tạo sẵn form đơn nghỉ cho bạn.',
      '',
      buildLeaveSummary(draft),
      '',
      'Bạn xem lại, chỉnh nếu cần rồi bấm gửi HR nhé.',
    ].join('\n'),
    ready: true,
  };
}

function applyLeaveReply(intake, reply) {
  const trimmed = reply.trim();
  const nextDraft = { ...intake.draft };

  if (intake.pendingStep === 'dates') {
    const range = parseLeaveDateRange(trimmed);
    if (!range.startDate || !range.endDate) {
      return {
        state: intake,
        message: 'Mình chưa đọc được khoảng ngày nghỉ. Bạn giúp mình nhập lại theo dạng `10/07 - 11/07` hoặc `10/07/2026 - 11/07/2026` nhé.',
        ready: false,
      };
    }
    Object.assign(nextDraft, range);
  } else if (intake.pendingStep === 'reason') {
    if (trimmed.length < 3) {
      return {
        state: intake,
        message: 'Bạn giúp mình ghi lý do nghỉ rõ hơn một chút để mình điền vào đơn nhé.',
        ready: false,
      };
    }
    nextDraft.reason = trimmed;
  } else if (intake.pendingStep === 'handover') {
    nextDraft.handoverNote = hasExplicitNoHandover(trimmed) ? '' : trimmed;
  }

  return nextLeavePrompt({ ...intake, draft: nextDraft });
}

function ChatBubbleIcon({ className = 'w-6 h-6' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 10h10" />
      <path d="M7 14h6" />
      <path d="M21 12c0 4.418-4.03 8-9 8a9.94 9.94 0 0 1-4.088-.874L3 20l1.12-3.733A7.73 7.73 0 0 1 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z" />
    </svg>
  );
}

function SparkIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />
    </svg>
  );
}

function SendIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m5 12 7-7 7 7" />
      <path d="M12 19V5" />
    </svg>
  );
}

function CopyIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect width="14" height="14" x="8" y="8" rx="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  );
}

function renderInlineMarkdown(text) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function MarkdownMessage({ content }) {
  const lines = String(content || '').replace(/\r\n/g, '\n').split('\n');
  const blocks = [];
  let codeLines = [];
  let listItems = [];
  let ordered = false;
  let inCodeBlock = false;

  function flushList() {
    if (!listItems.length) return;
    const ListTag = ordered ? 'ol' : 'ul';
    blocks.push(
      <ListTag className={ordered ? 'list-decimal' : 'list-disc'} key={`list-${blocks.length}`}>
        {listItems.map((item, index) => <li key={`${item}-${index}`}>{renderInlineMarkdown(item)}</li>)}
      </ListTag>,
    );
    listItems = [];
  }

  function flushCode() {
    if (!codeLines.length) return;
    blocks.push(<pre key={`code-${blocks.length}`}><code>{codeLines.join('\n')}</code></pre>);
    codeLines = [];
  }

  lines.forEach((line) => {
    if (line.trim().startsWith('```')) {
      flushList();
      if (inCodeBlock) flushCode();
      inCodeBlock = !inCodeBlock;
      return;
    }
    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    const unorderedMatch = line.match(/^\s*[-*]\s+(.+)/);
    const orderedMatch = line.match(/^\s*\d+[.)]\s+(.+)/);
    if (unorderedMatch || orderedMatch) {
      const nextOrdered = Boolean(orderedMatch);
      if (listItems.length && ordered !== nextOrdered) flushList();
      ordered = nextOrdered;
      listItems.push((orderedMatch || unorderedMatch)[1]);
      return;
    }
    flushList();

    const headingMatch = line.match(/^\s*(#{1,3})\s+(.+)/);
    if (headingMatch) {
      const HeadingTag = headingMatch[1].length === 1 ? 'h2' : 'h3';
      blocks.push(<HeadingTag key={`heading-${blocks.length}`}>{renderInlineMarkdown(headingMatch[2])}</HeadingTag>);
      return;
    }
    if (!line.trim()) {
      blocks.push(<div className="h-2" key={`space-${blocks.length}`} />);
      return;
    }
    blocks.push(<p key={`paragraph-${blocks.length}`}>{renderInlineMarkdown(line)}</p>);
  });

  flushList();
  flushCode();
  return <div className="hr-chat-markdown">{blocks}</div>;
}

const INITIAL_CHAT_MESSAGE = {
  role: 'assistant',
  content: 'Chào bạn, mình có thể hỗ trợ về nghỉ phép, nghỉ việc, bảo hiểm, lương thưởng, phúc lợi và các thủ tục nội bộ. Nếu cần làm đơn nghỉ, bạn cứ nói tự nhiên, mình sẽ hỏi dần rồi tạo form sẵn cho bạn.',
};

function chatSessionKey(currentUser) {
  const identity = currentUser?.id || currentUser?.email || 'anonymous';
  return `hr_assistant_session:${identity}`;
}

function readChatSession(currentUser) {
  const fallback = {
    messages: [INITIAL_CHAT_MESSAGE],
    leaveForm: createLeaveDraft('', currentUser),
    leaveIntake: null,
    showLeaveForm: false,
  };

  try {
    const saved = JSON.parse(sessionStorage.getItem(chatSessionKey(currentUser)) || 'null');
    if (!saved || !Array.isArray(saved.messages) || !saved.messages.length) return fallback;
    const messages = saved.messages
      .filter((message) => ['user', 'assistant'].includes(message?.role) && typeof message?.content === 'string')
      .slice(-40);
    if (!messages.length) return fallback;
    return {
      messages,
      leaveForm: saved.leaveForm && typeof saved.leaveForm === 'object'
        ? { ...createLeaveDraft('', currentUser), ...saved.leaveForm }
        : fallback.leaveForm,
      leaveIntake: saved.leaveIntake && typeof saved.leaveIntake === 'object' ? saved.leaveIntake : null,
      showLeaveForm: Boolean(saved.showLeaveForm),
    };
  } catch {
    return fallback;
  }
}

export default function HrPolicyChatPanel({ currentUser, variant = 'full' }) {
  const isCompact = variant === 'compact';
  const isWidget = variant === 'widget';
  const isSmallLayout = isCompact || isWidget;
  const widgetPanelRef = useRef(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const initialSessionRef = useRef(null);
  if (!initialSessionRef.current) initialSessionRef.current = readChatSession(currentUser);
  const initialSession = initialSessionRef.current;
  const [isOpen, setIsOpen] = useState(() => !isWidget);
  const [messages, setMessages] = useState(initialSession.messages);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [leaveForm, setLeaveForm] = useState(initialSession.leaveForm);
  const [leaveFiles, setLeaveFiles] = useState([]);
  const [showLeaveForm, setShowLeaveForm] = useState(initialSession.showLeaveForm);
  const [leaveLoading, setLeaveLoading] = useState(false);
  const [leaveSuccess, setLeaveSuccess] = useState('');
  const [leaveIntake, setLeaveIntake] = useState(initialSession.leaveIntake);

  useEffect(() => {
    sessionStorage.setItem(chatSessionKey(currentUser), JSON.stringify({
      messages: messages.slice(-40),
      leaveForm,
      leaveIntake,
      showLeaveForm,
    }));
  }, [currentUser, leaveForm, leaveIntake, messages, showLeaveForm]);

  function appendAssistantMessage(content) {
    setMessages((current) => [...current, { role: 'assistant', content }]);
  }

  function handleQueryKeyDown(event) {
    if (event.key !== 'Enter' || event.shiftKey) return;
    event.preventDefault();
    if (loading || !query.trim()) return;
    event.currentTarget.form?.requestSubmit();
  }

  async function submit(event) {
    event.preventDefault();
    if (!query.trim()) return;

    const submittedQuery = query.trim();
    const effectiveQuery = submittedQuery;
    const shouldStartLeaveFlow = detectLeaveRequestIntent(submittedQuery);

    setMessages((current) => [...current, { role: 'user', content: submittedQuery }]);
    setQuery('');
    setLeaveSuccess('');
    setError('');

    if (leaveIntake) {
      if (isCancelMessage(submittedQuery)) {
        setLeaveIntake(null);
        setShowLeaveForm(false);
        setLeaveFiles([]);
        appendAssistantMessage('Mình đã dừng luồng tạo đơn nghỉ. Khi nào cần làm lại, bạn chỉ cần nhắn mình là được.');
        return;
      }

      const next = applyLeaveReply(leaveIntake, submittedQuery);
      setLeaveIntake(next.ready ? null : next.state);
      if (next.ready) {
        setLeaveForm(next.state.draft);
        setShowLeaveForm(true);
        setLeaveFiles([]);
      }
      appendAssistantMessage(next.message);
      return;
    }

    if (isGreetingQuery(submittedQuery)) {
      appendAssistantMessage(greetingReply(currentUser));
      return;
    }

    if (isLightConversationQuery(submittedQuery)) {
      appendAssistantMessage(lightConversationReply(currentUser, submittedQuery));
      return;
    }

    if (isCasualPersonalActivityQuery(submittedQuery)) {
      appendAssistantMessage(refusalReply());
      return;
    }

    if (shouldStartLeaveFlow) {
      const intake = createLeaveIntake(submittedQuery, currentUser);
      const next = nextLeavePrompt(intake);
      setLeaveIntake(next.ready ? null : next.state);
      if (next.ready) {
        setLeaveForm(next.state.draft);
        setShowLeaveForm(true);
        setLeaveFiles([]);
      } else {
        setShowLeaveForm(false);
        setLeaveFiles([]);
      }
      appendAssistantMessage(next.message);
      return;
    }

    setLoading(true);

    try {
      const response = await chat({
        query: effectiveQuery,
        topK: 8,
        threshold: 0.2,
        searchMode: 'Hybrid',
        useHyDE: false,
        history: messages.slice(-10).map(({ role, content }) => ({ role, content })),
      });
      appendAssistantMessage(response.answer);
      if (response.handoffRecommended) {
        appendAssistantMessage('Đây là tình huống nhạy cảm cần HR xác minh. Bạn nên mở mục Hỗ trợ trực tiếp để tạo phiên trao đổi riêng với HR.');
      }
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  function updateLeaveForm(name, value) {
    setLeaveForm((current) => {
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

  async function submitLeaveRequest(event) {
    event.preventDefault();
    setLeaveLoading(true);
    setError('');
    setLeaveSuccess('');

    try {
      await createLeaveRequest({
        ...leaveForm,
        totalDays: Number(leaveForm.totalDays),
        attachments: leaveFiles,
      });
      setLeaveSuccess('Đơn nghỉ của bạn đã được gửi đến HR.');
      toast.success('Đơn nghỉ của bạn đã được gửi đến HR.');
      setShowLeaveForm(false);
      setLeaveIntake(null);
      setLeaveForm(createLeaveDraft('', currentUser));
      setLeaveFiles([]);
      appendAssistantMessage('Đơn của bạn đã được gửi thành công. Bạn có thể theo dõi trạng thái trong màn Đơn từ HR.');
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLeaveLoading(false);
    }
  }

useEffect(() => {
  const container = messagesContainerRef.current;

  if (!container) return;

  container.scrollTo({
    top: container.scrollHeight,
    behavior: 'smooth',
  });
}, [messages, loading, showLeaveForm, leaveIntake]);

  useEffect(() => {
    if (!isWidget || !isOpen) return undefined;

    const isMobile = window.matchMedia('(max-width: 767px)').matches;
    if (!isMobile) return undefined;

    const scrollY = window.scrollY;
    const previousOverflow = document.body.style.overflow;
    const previousPosition = document.body.style.position;
    const previousTop = document.body.style.top;
    const previousWidth = document.body.style.width;

    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = '100%';

    function preventTouchOutside(event) {
      if (widgetPanelRef.current?.contains(event.target)) return;
      event.preventDefault();
    }

    document.addEventListener('touchmove', preventTouchOutside, { passive: false });

    return () => {
      document.removeEventListener('touchmove', preventTouchOutside);
      document.body.style.overflow = previousOverflow;
      document.body.style.position = previousPosition;
      document.body.style.top = previousTop;
      document.body.style.width = previousWidth;
      window.scrollTo(0, scrollY);
    };
  }, [isOpen, isWidget]);

  if (isWidget && !isOpen) {
    return (
      <button
        type="button"
        aria-label="Mở chatbot HR"
        className="fixed bottom-5 right-5 z-50 h-14 w-14 rounded-full bg-linear-to-br from-vinuni-blue via-vinuni-light-blue to-sky-500 text-white shadow-xl shadow-vinuni-blue/30 flex items-center justify-center hover:scale-105 transition-all cursor-pointer"
        onClick={() => setIsOpen(true)}
      >
        <ChatBubbleIcon />
      </button>
    );
  }

  const panelClass = isWidget
    ? 'hr-chat-widget-panel fixed inset-x-3 top-3 bottom-3 z-50 rounded-[28px] border border-slate-200/80 bg-white/95 p-4 shadow-2xl shadow-slate-300/35 backdrop-blur-sm flex flex-col gap-4 overflow-hidden [overscroll-behavior:contain] sm:inset-x-auto sm:top-auto sm:right-5 sm:bottom-5 sm:w-[min(430px,calc(100vw-1.5rem))] sm:max-h-[min(760px,calc(100dvh-2.5rem))]'
    : isCompact
      ? 'rounded-[26px] border border-slate-200/70 bg-white p-4 md:p-5 shadow-lg shadow-slate-200/50 flex flex-col gap-4'
      : 'hr-chat-full-panel rounded-[28px] border border-slate-200/70 bg-white p-4 md:p-8 shadow-lg shadow-slate-200/50 flex flex-col gap-5';

  const chatCardClass = isWidget
    ? 'h-full'
    : isCompact
      ? 'h-[min(560px,70dvh)] min-h-[420px]'
      : 'hr-chat-card-full h-[clamp(460px,65dvh,720px)]';

  return (
    <div className={panelClass} ref={isWidget ? widgetPanelRef : undefined}>
      {isWidget ? (
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="h-10 w-10 rounded-2xl border border-vinuni-blue/10 bg-linear-to-br from-vinuni-blue/15 via-white to-vinuni-gold/20 text-vinuni-blue flex items-center justify-center shrink-0 shadow-sm shadow-vinuni-blue/10">
              <ChatBubbleIcon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-extrabold text-vinuni-blue truncate">Trợ lý HR</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">Chat tự nhiên, hỏi chính sách nhanh</p>
            </div>
          </div>
          <button
            type="button"
            className="h-9 w-9 rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-all cursor-pointer shrink-0"
            onClick={() => setIsOpen(false)}
            aria-label="Đóng chatbot HR"
          >
            ×
          </button>
        </div>
      ) : isCompact ? (
        <div className="rounded-3xl border border-vinuni-blue/10 bg-linear-to-br from-vinuni-blue/6 via-white to-vinuni-gold/10 p-4">
          <span className="inline-flex items-center gap-1 rounded-full border border-vinuni-blue/10 bg-white/80 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-vinuni-blue">
            <SparkIcon className="w-3.5 h-3.5" />
            HR Mini Bot
          </span>
          <h3 className="mt-3 text-sm md:text-base font-extrabold text-vinuni-blue">Hỏi nhanh như đang chat với HR</h3>
          <p className="text-xs text-slate-500 leading-relaxed mt-1">Bot sẽ trả lời tự nhiên hơn, hỏi tiếp khi thiếu dữ liệu và hỗ trợ tạo đơn nghỉ ngay trong cuộc trò chuyện.</p>
        </div>
      ) : (
        <div className="hr-chat-full-title">
          <PageTitle eyebrow="HR Chat" title="Trợ lý HR cho câu hỏi nội bộ hằng ngày">
            Hỏi theo cách tự nhiên, nhận câu trả lời dễ đọc hơn và để bot hỗ trợ điền dần đơn nghỉ khi bạn cần xử lý nhanh.
          </PageTitle>
        </div>
      )}

      <div className="flex flex-1 min-h-0 flex-col overflow-hidden">

  {/* Card Chat */}
  <div className={`flex min-h-0 flex-col rounded-[26px] border border-slate-200/80 bg-white overflow-hidden shadow-inner shadow-slate-100 ${chatCardClass}`}>

    {leaveIntake && (
      <div className="border-b border-slate-200 bg-sky-50/80 px-4 py-3">
        <div className="flex items-center gap-2 font-bold text-vinuni-blue">
          <SparkIcon className="w-4 h-4" />
          Đang tạo đơn nghỉ
        </div>

        <p className="mt-1 text-xs text-slate-600">
          Bot sẽ hỏi lần lượt các thông tin còn thiếu rồi dựng sẵn form để bạn chỉ việc rà lại và gửi.
        </p>

        <pre className="mt-3 whitespace-pre-wrap break-words rounded-xl bg-white px-3 py-3 text-xs">
          {buildLeaveSummary(leaveIntake.draft) ||
            'Đang chờ bổ sung thông tin...'}
        </pre>
      </div>
    )}

    {/* Messages */}
    <div ref={messagesContainerRef} className="hr-chat-thread flex-1 min-h-0 overflow-y-auto scroll-smooth overscroll-contain">

      {messages.map((message, index) => (
        <article key={`${message.role}-${index}`} className={`hr-chat-message ${message.role}`}>
          {message.role === 'assistant' && (
            <div className="hr-chat-avatar" aria-hidden="true"><SparkIcon className="h-4 w-4" /></div>
          )}
          <div className="hr-chat-message-body">
            {message.role === 'assistant' && <b className="hr-chat-author">Trợ lý HR</b>}
            <div className={isSmallLayout ? 'text-xs' : 'text-sm'}>
              <MarkdownMessage content={message.content} />
            </div>
            {message.role === 'assistant' && (
              <button
                type="button"
                className="hr-chat-copy"
                onClick={async () => {
                  await navigator.clipboard.writeText(message.content);
                  toast.success('Đã sao chép câu trả lời.');
                }}
                title="Sao chép câu trả lời"
              >
                <CopyIcon />
                <span>Sao chép</span>
              </button>
            )}
          </div>
        </article>
      ))}

      {loading && (
        <article className="hr-chat-message assistant">
          <div className="hr-chat-avatar" aria-hidden="true"><SparkIcon className="h-4 w-4" /></div>
          <div className="hr-chat-message-body">
            <b className="hr-chat-author">Trợ lý HR</b>
            <div className="hr-chat-typing" aria-label="Đang trả lời"><span /><span /><span /></div>
          </div>
        </article>
      )}

      <div ref={messagesEndRef} />
    </div>

    {/* Input */}
  <form onSubmit={submit} className="hr-chat-composer-wrap z-20 shrink-0">
    <div className="hr-chat-composer-box">
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleQueryKeyDown}
        placeholder="Nhắn tin cho Trợ lý HR..."
        rows={1}
        className={`hr-chat-input ${isSmallLayout ? 'text-xs' : 'text-sm'}`}
      />

      <button
        type="submit"
        disabled={loading || !query.trim()}
        className="hr-chat-send"
        aria-label={leaveIntake ? 'Tiếp tục' : 'Gửi tin nhắn'}
      >
        <SendIcon />
      </button>
    </div>
    <p className="hr-chat-disclaimer">AI có thể mắc lỗi. Hãy kiểm tra lại thông tin quan trọng với phòng HR.</p>
    </form>

  </div>

  {showLeaveForm && (
    <div className="mt-4 border border-vinuni-light-blue/25 bg-white rounded-[26px] p-4">
      {/* giữ nguyên LeaveRequestForm */}
    </div>
  )}

  {leaveSuccess && (
    <div className="mt-4 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl p-3 text-center">
      {leaveSuccess}
    </div>
  )}

  {error && (
    <div className="mt-4 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 text-center">
      {error}
    </div>
  )}

</div>
    </div>
  );
}
