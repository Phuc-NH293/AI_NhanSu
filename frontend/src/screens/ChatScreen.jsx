import HrPolicyChatPanel from '../components/HrPolicyChatPanel';

const guardrails = [
  'Ưu tiên trả lời theo chính sách nội bộ đã có căn cứ.',
  'Thiếu dữ liệu thì hỏi lại hoặc hướng người dùng kiểm tra thêm, không đoán.',
  'Ca nhạy cảm hoặc cần xác minh hồ sơ sẽ được định hướng chuyển tiếp HR.',
  'Luồng xin nghỉ có thể hỏi nhiều lượt rồi dựng sẵn form cho người dùng.',
];

export default function ChatScreen({ currentUser }) {
  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 items-start">
      <div className="lg:col-span-8">
        <HrPolicyChatPanel currentUser={currentUser} variant="full" />
      </div>

      <aside className="lg:col-span-4 rounded-[28px] border border-slate-200/70 bg-white p-4 md:p-6 shadow-lg shadow-slate-200/45 flex flex-col gap-4">
        <div className="rounded-[24px] border border-vinuni-blue/10 bg-linear-to-br from-vinuni-blue/8 via-white to-vinuni-gold/12 p-4">
          <span className="inline-flex rounded-full border border-vinuni-blue/10 bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-vinuni-blue">
            Guardrail HR
          </span>
          <h3 className="mt-3 text-base font-extrabold text-slate-900">Câu trả lời hướng người dùng cuối</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-600">
            Màn chat này ưu tiên văn phong tự nhiên, giảm cảm giác “log hệ thống”, nhưng vẫn giữ nguyên các giới hạn an toàn cần có cho nghiệp vụ HR.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-slate-200/70 bg-slate-50/70 px-4 py-3">
            <b className="block text-sm text-slate-900">Chào hỏi</b>
            <span className="mt-1 block text-xs text-slate-500">Phản hồi mềm hơn, không còn quá máy móc.</span>
          </div>
          <div className="rounded-2xl border border-slate-200/70 bg-slate-50/70 px-4 py-3">
            <b className="block text-sm text-slate-900">Xin nghỉ phép</b>
            <span className="mt-1 block text-xs text-slate-500">Hỏi nhiều lượt rồi tạo form sẵn.</span>
          </div>
        </div>

        <div className="rounded-[24px] border border-slate-200/70 bg-white p-4">
          <h4 className="text-xs font-extrabold text-vinuni-blue uppercase tracking-wider">Nguyên tắc trả lời</h4>
          <ul className="mt-3 space-y-2.5 text-xs text-slate-600 leading-relaxed">
            {guardrails.map((item) => (
              <li className="flex gap-2" key={item}>
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-vinuni-light-blue shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[11px] text-slate-400 leading-relaxed">
          AI giúp giảm tải câu hỏi lặp lại. Quyết định cuối cùng vẫn thuộc phòng HR hoặc đơn vị có thẩm quyền.
        </p>
      </aside>
    </section>
  );
}
