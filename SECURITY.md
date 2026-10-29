# Security

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately
through GitHub's **Security → Report a vulnerability** flow, or contact the
maintainer through the repository profile. Include a short reproduction, the
affected version or commit, and the impact you observed.

## Deployment notes

This project is a demonstration application. It supports an optional shared
API key (`APP_API_KEY`), but it does not implement user accounts or
multi-tenant authorization. Before exposing it to real users, add an identity
layer, run it behind TLS, and restrict access to the Ollama and Hindsight
services.

- When `APP_API_KEY` is set, every `/api` route except the health probes
  requires `X-API-Key`, compared with `secrets.compare_digest`. Health probes
  stay public for orchestrators. The key is a deployment guard, not a
  substitute for per-user authorization.
- The bundled frontend reads `VITE_API_KEY` at build time. That value is
  embedded in the JavaScript bundle, so treat it as a low-privilege access
  token and serve the app over TLS.
- Customer memory is isolated per customer by a random bank key, but the API
  itself has no per-user ownership checks.
- SQLite is used for simplicity. Use a production database and backups for
  real deployments.
- Uploaded files are limited by extension and size, but should also be
  scanned or sandboxed in a production support workflow.
- Never commit `.env` files, API keys, database files, or uploaded customer
  data. `.gitignore` already excludes them.
