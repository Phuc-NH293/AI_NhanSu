# Deploy production không mất backend/data

Tài liệu này dành cho cách đưa app lên cho người dùng thật mà không sửa logic backend.

## Nguyên tắc giữ nguyên backend

- Không sửa `backend/main.py` khi deploy.
- Frontend production gọi API qua `/api`, backend FastAPI phục vụ cả API và file build trong cùng container.
- Dữ liệu người dùng, chat, đơn HR, upload và corpus nằm trong `data/`.
- Production phải mount persistent disk/volume vào `/app/data`.
- Trước mỗi lần deploy lớn, backup thư mục `data/`.

## Backup trước khi deploy

Chạy trên máy đang có dữ liệu thật:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_data.ps1
```

File backup sẽ nằm trong `backups/data-YYYYMMDD-HHMMSS.zip`.

## Chạy production local bằng Docker

Tạo `.env` từ `.env.example`, sau đó đặt tối thiểu:

```env
AUTH_SECRET=mot-chuoi-bi-mat-dai-ngau-nhien
ADMIN_EMAIL=admin@your-company.com
ADMIN_PASSWORD=doi-mat-khau-manh
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Build và chạy:

```powershell
docker compose up --build -d
```

Mở app:

```text
http://127.0.0.1:8000
```

Kiểm tra backend:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

Tắt app nhưng giữ dữ liệu:

```powershell
docker compose down
```

Không xóa thư mục `data/` nếu muốn giữ user, lịch sử chat, upload và đơn HR.

## Deploy Render

Repo đã có `render.yaml` và `Dockerfile`.

- Service: `hr-helpdesk-ai`
- Runtime: Docker
- Region: Singapore
- Health check: `/health`
- Plan mặc định trong repo: `free`, dùng để demo không cần card.

Lưu ý: Render free không có persistent disk. Dữ liệu tạo lúc app chạy như user mới, chat, đơn HR, file upload và index upload có thể mất sau restart/redeploy. Khi mở cho user thật, đổi lại `plan: starter` và thêm persistent disk mount `/app/data`.

Các bước:

1. Backup `data/` nếu đang có dữ liệu thật.
2. Push code lên GitHub.
3. Vào Render, chọn `New Blueprint`.
4. Chọn repo này.
5. Điền environment variables:
   - `ADMIN_PASSWORD`
   - `LLM_PROVIDER`
   - `GEMINI_API_KEY` hoặc `OPENAI_API_KEY`
   - `AUTH_SECRET` nếu không dùng giá trị Render tự sinh
   - SMTP vars nếu muốn gửi email reset password thật
6. Deploy.

Sau khi deploy xong, Render sẽ cấp URL dạng:

```text
https://hr-helpdesk-ai.onrender.com
```

Kiểm tra:

```text
https://hr-helpdesk-ai.onrender.com/health
https://hr-helpdesk-ai.onrender.com
```

Docker startup sẽ seed dữ liệu mẫu vào `/app/data` khi file chưa tồn tại. Trên Render free, thư mục này chỉ dùng cho demo và không được đảm bảo bền sau restart/redeploy.

## Checklist trước khi mở cho user thật

- Đổi `ADMIN_PASSWORD` khỏi mật khẩu demo.
- Đặt `AUTH_SECRET` đủ dài và không commit vào git.
- Có API key hợp lệ cho provider đang chọn.
- Bật SMTP nếu dùng chức năng quên mật khẩu thật.
- Kiểm tra persistent disk/volume đang gắn vào `/app/data`.
- Test đăng nhập admin, HR, employee.
- Upload thử tài liệu HR và hỏi thử một câu có citation.
- Backup `data/` sau khi nạp tài liệu quan trọng.
