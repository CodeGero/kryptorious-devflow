# devflow

> One tool for scaffolding, auditing, fixing, shipping, and CI/CD.

[![PyPI](https://img.shields.io/pypi/v/kryptorious-devflow)](https://pypi.org/project/kryptorious-devflow/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Part of the [Kryptorious developer toolkit](https://kryptorious.gumroad.com/l/jbvet) — 31 open-source tools, one $9 lifetime license.

## Install

```bash
pip install kryptorious-devflow
```

## Quickstart

```bash
devflow init my-api --template api
devflow ship --bump patch
```

## Commands

| Command | Description |
|---------|-------------|
| `devflow init my-api --template api` | Scaffold a project (9 templates: python, node, fullstack, cli, api, lib, go, rust, react). |
| `devflow audit` | Comprehensive codebase health check. |
| `devflow fix` | Auto-fix common code issues. |
| `devflow ship --bump patch` | Version bump, changelog, tag, build, publish. |
| `devflow premium -p .` | DevFlow Premium: multi-env CI, approval gates, Docker + Terraform (needs $9 license). |


DevFlow Premium (included with the $9 lifetime license) generates a multi-environment GitHub Actions workflow (staging auto-deploy / production manual approval gate), Dockerfile, docker-compose.yml, and per-environment Terraform stubs. Activate with `devflow activate <KEY>`.


## License

MIT — free for personal and commercial use. The $9 lifetime license adds DevFlow Premium (multi-environment CI/CD, approval gates, infrastructure-as-code). Get it at [kryptorious.gumroad.com/l/jbvet](https://kryptorious.gumroad.com/l/jbvet).
