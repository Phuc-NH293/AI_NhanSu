import { useState } from 'react';
import { uploadDocument } from '../config/api';
import { toast } from '../lib/toast';

export function InlineUpload() {
  const [status, setStatus] = useState('Chưa nạp file nào trong phiên này.');
  const [loading, setLoading] = useState(false);

  async function onFileChange(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    setLoading(true);
    setStatus(`Đang nạp ${files.length} file...`);
    const messages = [];

    for (const file of files) {
      try {
        const response = await uploadDocument(file);
        messages.push(`OK: ${response.fileName} -> ${response.markdownPath}`);
        toast.success(`Đã nạp ${response.fileName}`);
      } catch (err) {
        toast.error(`${file.name}: ${err.message}`);
        messages.push(`Lỗi: ${file.name} -> ${err.message}`);
      }
    }

    setStatus(messages.join('\n'));
    setLoading(false);
    event.target.value = '';
  }

  return (
    <div className="bg-linear-to-br from-slate-50 to-slate-100/60 border border-slate-200/60 rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1 min-w-0 flex flex-col gap-0.5">
          <span className="text-[10px] font-extrabold uppercase tracking-wider text-vinuni-light-blue">Tài liệu đầu vào</span>
          <b className="text-xs font-bold text-slate-800 leading-normal block mt-0.5">Nạp chính sách, quy trình, biểu mẫu, FAQ hoặc slide đào tạo HR</b>
          <small className="text-[10px] text-slate-400 leading-relaxed block mt-0.5">File được tách chữ thành markdown, index vào RAG và dùng làm nguồn khi trả lời.</small>
        </div>
        <label className="shrink-0 bg-linear-to-r from-vinuni-blue to-vinuni-light-blue text-white font-semibold rounded-xl py-2.5 px-5 text-xs shadow-xs hover:opacity-95 transition-all disabled:opacity-50 cursor-pointer text-center flex items-center justify-center">
          <input type="file" className="hidden" multiple accept=".pdf,.ppt,.pptx,.doc,.docx,.txt,.md,.html,.htm,.json" onChange={onFileChange} disabled={loading} />
          {loading ? 'Đang nạp...' : 'Tải file lên'}
        </label>
      </div>
      <pre className="w-full font-mono text-[10px] text-slate-500 bg-white border border-slate-200/30 rounded-xl p-3 max-h-32 overflow-y-auto whitespace-pre-wrap leading-relaxed">{status}</pre>
    </div>
  );
}
