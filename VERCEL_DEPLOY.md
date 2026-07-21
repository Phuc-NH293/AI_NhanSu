# Deploy frontend Vercel + backend Render

Backend cua du an dung FastAPI, sentence-transformers, Chroma local va ghi du lieu runtime. Vercel Serverless khong co persistent filesystem va khong phu hop de chay backend nay. Cau hinh production kha thi la:

```text
Vercel (React/Vite frontend)
    -> VITE_API_BASE=https://<render-service>.onrender.com/api
Render Docker service (FastAPI + RAG)
    -> persistent disk /app/data khi mo cho user that
```

## 1. Backend tren Render

Import GitHub repository bang `New Blueprint`. Render doc `render.yaml` va `Dockerfile`.

Dat cac environment variables bat buoc:

```env
AUTH_SECRET=<chuoi-ngau-nhien-dai>
ADMIN_EMAIL=<email-admin>
ADMIN_PASSWORD=<mat-khau-manh>
ALLOW_PUBLIC_REGISTRATION=0
LLM_PROVIDER=gemini
GEMINI_API_KEY=<gemini-api-key>
GEMINI_MODEL=gemini-2.5-flash
CORS_ORIGINS=https://<vercel-project>.vercel.app
```

Sau khi deploy, kiem tra:

```text
https://<render-service>.onrender.com/health
```

Render free phu hop demo nhung filesystem khong ben. Khi co nguoi dung that, dung plan co persistent disk va mount vao `/app/data`.

## 2. Frontend tren Vercel

Import cung GitHub repository. Vercel su dung `vercel.json` o root.

Dat environment variable cho Production, Preview va Development:

```env
VITE_API_BASE=https://<render-service>.onrender.com/api
```

Redeploy frontend sau khi thay doi environment variable.

## 3. Checklist

- `/health` cua backend tra HTTP 200.
- Vercel build tao `frontend/dist` thanh cong.
- Dang nhap duoc tren URL Vercel.
- Browser Network khong co CORS error.
- Chat tra loi duoc va khong lo API key o frontend bundle.
- Upload thu mot tai lieu va xac minh index con ton tai sau restart neu da gan persistent disk.
