# Security

This is a hackathon prototype. Security scope is deliberately minimal but honest.

## Secrets

- All credentials are read from environment variables via `app/core/config.get_secret()`.
- `.env` is gitignored; `.env.example` and `hackathon/credential_template.env` carry
  **no values**.
- No API key, token or password appears anywhere in the source tree.
- Logs pass through a scrubber (`app/core/security.scrub_secrets`) that redacts
  `sk-...`, `api_key=...`, and `Bearer ...` patterns.
- `Settings.public_summary()` only ever reports `"<set:N chars>"` / `"<unset>"`,
  never the value.

## Input validation

- Image uploads: magic-byte format check (JPEG/PNG/GIF/WebP), size cap
  (`MAX_UPLOAD_MB`, default 8), Pillow integrity `verify()`. A bad image is
  rejected with `ToolInputError`; the agent then continues *without* vision
  rather than crashing.
- All tool inputs are validated by Pydantic models before execution.
- Free text is length-capped and stripped of control characters.

## Error handling

- Provider failures are caught per-provider and recorded on the `ToolCallRecord`;
  they never propagate as raw stack traces to the UI.
- Unexpected exceptions in the reasoning path trigger the fallback ladder, not a
  crash.

## Not in scope for the prototype

- Authentication / authorisation / multi-tenant isolation
- Rate limiting, WAF, CSRF (single-user local Streamlit app)
- Secrets management service integration (use `.env` locally)
- Supply-chain pinning beyond `requirements.txt` version floors

## Reporting

For a suspected vulnerability, describe the class of problem (not a working
exploit) to the project owner.
