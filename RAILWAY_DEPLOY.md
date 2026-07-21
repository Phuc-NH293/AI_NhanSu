# Deploy Railway

Repo da co `Dockerfile` va `railway.json`.

Railway se build bang Dockerfile o root, container nghe port qua bien `PORT`, va health check tai `/health`.

## Auth

Backend dung JWT bearer token chuan HS256:

- Login/register tra ve `token`.
- Frontend gui `Authorization: Bearer <token>`.
- Token duoc ky bang `AUTH_SECRET`.
- Doi `AUTH_SECRET` se lam cac phien dang nhap cu het hieu luc.

## Variables

Dat toi thieu cac bien sau tren Railway:

```env
AUTH_SECRET=long-random-secret
AUTH_TOKEN_TTL_SECONDS=604800
ADMIN_EMAIL=admin@your-company.com
ADMIN_PASSWORD=strong-password
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
ALLOW_PUBLIC_REGISTRATION=0
```

Neu dung SMTP reset password that, them:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SENDER=your-email@gmail.com
```

## Data Persistence

App ghi user, chat, don HR, upload va index vao `/app/data`.

Neu chi demo ngan han thi co the chay khong volume. Neu can giu user moi tao, chat, don HR, upload va index sau restart/redeploy, bat buoc tao Railway Volume va mount vao:

```text
/app/data
```

Co the them variable nay de noi ro noi backend ghi du lieu:

```env
DATA_DIR=/app/data
```

## Deploy Steps

1. Backup `data/` neu dang co du lieu that.
2. Push code len GitHub.
3. Tao Railway project tu GitHub repo.
4. Dat variables o tren.
5. Them volume mount `/app/data` neu can persistence.
6. Deploy.

Kiem tra sau deploy:

```text
https://<your-railway-domain>/health
https://<your-railway-domain>
```
