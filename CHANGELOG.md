# Changelog

## 1.5.0 - 2026-07-09
- Added `devflow premium` — generates real multi-environment CI/CD (staging
  auto-deploy / production manual approval gate), Dockerfile, docker-compose.yml,
  and per-environment Terraform stubs. Gated behind a license key.
- Added `devflow activate <KEY>` — persist a premium license locally.
- Offline license verification (CRC32 self-checksummed key format).
- Removed non-functional premium upsell prints; premium is now real.

## 1.4.0
- Base `pipeline` command: GitHub Actions / GitLab CI generation.

## 1.0.0
- Initial public release: init, audit, fix, ship, pipeline, doctor.
