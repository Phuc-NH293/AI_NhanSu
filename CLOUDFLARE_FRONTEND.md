# Deploy frontend len Cloudflare Pages

Cloudflare Pages chi host frontend React/Vite. Backend FastAPI van can deploy rieng tren Render/Railway/Fly/VPS va cung cap URL API public.

## Cau hinh Cloudflare Pages

- Framework preset: `Vite`
- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `dist`
- Node version: `22`

## Environment variable

Khi backend da co URL public, them bien nay trong Cloudflare Pages:

```env
VITE_API_BASE=https://your-backend-domain.com/api
```

Neu chua co backend public, frontend van deploy duoc nhung cac chuc nang login/chat/upload se bao loi API.

## SPA fallback

File `frontend/public/_redirects` duoc copy vao `dist/_redirects` khi build de Cloudflare tra `index.html` cho moi route React.
