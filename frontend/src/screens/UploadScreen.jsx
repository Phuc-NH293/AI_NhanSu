import { useState } from 'react';
import { uploadDocument } from '../config/api';
import { PageTitle } from '../components/common';
import { toast } from '../lib/toast';

export default function UploadScreen() {
  const [logs, setLogs] = useState([]);
  const [uploaded, setUploaded] = useState([]);
  const [loading, setLoading] = useState(false);
  const [metadata, setMetadata] = useState({
    version: '1.0', status: 'active', effectiveFrom: '', effectiveTo: '',
    allowedRoles: 'employee,hr,admin', departments: 'all', confidentiality: 'internal',
  });

  async function onFileChange(event) {
    const files = Array.from(event.target.files || []);
    setLoading(true);
    for (const file of files) {
      setLogs((current) => [...current, `> Đang upload ${file.name}...`]);
      try {
        const response = await uploadDocument(file, metadata);
        setUploaded((current) => [...current, response]);
        toast.success(`Đã nạp ${response.fileName}`);
        setLogs((current) => [...current, ...response.logs.map((line) => `> ${line}`), `> OK: ${response.message}`]);
      } catch (err) {
        toast.error(`${file.name}: ${err.message}`);
        setLogs((current) => [...current, `> LỖI: ${err.message}`]);
      }
    }
    setLoading(false);
    event.target.value = '';
  }

  return (
    <section className="bg-white border border-slate-200/60 rounded-2xl p-4 md:p-8 shadow-xs flex flex-col gap-6">
      <PageTitle eyebrow="Knowledge Base" title="Nạp tài liệu chính sách nhân sự">
        Upload PDF, PPTX, DOCX, markdown, biểu mẫu hoặc FAQ. Hệ thống tách chữ sang markdown trong <code>data/standardized/news/</code> rồi index vào RAG.
      </PageTitle>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
        <label className="flex flex-col items-center justify-center p-6 sm:p-8 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 hover:bg-slate-100/50 hover:border-vinuni-light-blue transition-all cursor-pointer text-center relative group">
          <input type="file" className="hidden" multiple accept=".pdf,.ppt,.pptx,.doc,.docx,.txt,.md,.html,.htm,.json" onChange={onFileChange} disabled={loading} />
          <span className="text-3xl text-slate-400 group-hover:text-vinuni-blue font-bold mb-2">+</span>
          <b className="text-sm font-bold text-slate-700 group-hover:text-slate-800">{loading ? 'Đang xử lý...' : 'Chọn file chính sách HR'}</b>
          <small className="text-[10px] text-slate-400 mt-1">PDF, PPTX, DOCX, TXT, MD, HTML, JSON</small>
        </label>

        <div className="bg-slate-50 border border-slate-200/60 rounded-2xl p-5 flex flex-col gap-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-vinuni-blue mb-1">Đường dẫn lưu trữ</h3>
          <p className="text-xs text-slate-600 font-medium">File gốc: <code className="font-mono bg-slate-200/50 px-1.5 py-0.5 rounded text-amber-800">data/landing/uploads/</code></p>
          <p className="text-xs text-slate-600 font-medium">Bản markdown: <code className="font-mono bg-slate-200/50 px-1.5 py-0.5 rounded text-amber-800">data/standardized/news/</code></p>
          <p className="text-[11px] text-slate-400 leading-relaxed mt-2 border-t border-slate-200/50 pt-2.5">Nên nạp sổ tay nhân viên, chính sách nghỉ phép, bảo hiểm, hợp đồng, quy trình phúc lợi, biểu mẫu và FAQ nội bộ.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        {[
          ['version', 'Phiên bản', '1.0'], ['status', 'Trạng thái', 'active'],
          ['effectiveFrom', 'Hiệu lực từ', 'YYYY-MM-DD'], ['effectiveTo', 'Hiệu lực đến', 'YYYY-MM-DD'],
          ['allowedRoles', 'Role được xem', 'employee,hr,admin'], ['departments', 'Phòng ban', 'all'],
          ['confidentiality', 'Bảo mật', 'internal'],
        ].map(([name, label, placeholder]) => (
          <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600" key={name}>
            {label}
            <input
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-normal outline-none focus:border-vinuni-light-blue"
              value={metadata[name]}
              placeholder={placeholder}
              onChange={(event) => setMetadata((current) => ({ ...current, [name]: event.target.value }))}
            />
          </label>
        ))}
      </div>

      {uploaded.length > 0 && (
        <div className="flex flex-col gap-3 mt-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">File vừa nạp</h3>
          <div className="flex flex-col gap-2">
            {uploaded.map((item, index) => (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 p-3.5 border border-slate-200/60 rounded-xl bg-slate-50/50 text-xs" key={`${item.fileName}-${index}`}>
                <b className="font-bold text-slate-800 break-all sm:break-normal sm:truncate flex-1">{item.fileName}</b>
                <span className="text-slate-500 shrink-0">{(item.size / 1024).toFixed(2)} KB</span>
                <code className="font-mono bg-slate-100 text-[10px] text-slate-600 px-2 py-1 rounded-lg break-all sm:truncate sm:max-w-xs">{item.markdownPath}</code>
              </div>
            ))}
          </div>
        </div>
      )}

      <pre className="bg-slate-900 border border-slate-800 text-emerald-400 font-mono text-[11px] leading-relaxed p-4 rounded-xl max-h-[300px] overflow-y-auto mt-2 whitespace-pre-wrap">{logs.length ? logs.join('\n') : 'Đang chờ file chính sách nhân sự...'}</pre>
    </section>
  );
}
