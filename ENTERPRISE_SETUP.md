# Enterprise HR Assistant Setup

## Gemini 2.5 Flash

Create a local `.env` from `.env.example` and set:

```env
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-real-key
```

Never commit `.env`. Restart the backend after changing configuration.

## Document Security

Every uploaded policy supports version, lifecycle dates, allowed roles, departments,
and confidentiality. Retrieval rejects expired, inactive, unauthorized, or
department-restricted chunks before generation.

Use department slugs consistently, for example `hr`, `finance`, `academic-affairs`.
Use `all` only for documents intended for every department.

## Integrations

HRM uses `HRM_API_BASE` and `HRM_API_TOKEN`. SharePoint uses Microsoft Graph client
credentials from the `SHAREPOINT_*` variables in `.env.example`. An admin can inspect
configuration readiness through `GET /api/integrations/status`.

## Deployment Checklist

1. Replace `AUTH_SECRET`, admin password, and all example credentials.
2. Disable public registration with `ALLOW_PUBLIC_REGISTRATION=0`.
3. Configure Gemini and optionally OCR.
4. Assign every user a department before restricting documents by department.
5. Re-index after changing metadata or chunk settings: `python -m src.task4_chunking_indexing`.
6. Put the API behind HTTPS and restrict CORS to the production frontend origin.
7. Rotate secrets and back up `DATA_DIR` plus the vector index.
