# Natural-Language-to-Infrastructure Generator

I built this project as a local-first infrastructure generation and verification system, not an unrestricted text-to-HCL demo. It converts an English request into a validated resource specification, renders a complete multi-file Terraform project, applies security checks, executes Terraform formatting, initialization, validation, and LocalStack planning, attempts one safe correction pass, and returns a downloadable ZIP.

## Architecture

```text
English request
   ├─ Ollama JSON parser (optional)
   └─ deterministic parser (offline fallback)
            ↓
validated ResourceSpec
            ↓
secure multi-file Terraform renderer
            ↓
security scan → terraform fmt → init → validate → LocalStack plan
            ↓
one safe correction pass → files, logs, status, downloadable ZIP
```

Supported resources are intentionally scoped: S3, Lambda, DynamoDB, IAM execution roles, and S3-to-Lambda notifications. Generated S3 buckets use encryption, versioning, and public-access blocking. DynamoDB uses on-demand billing, encryption, and point-in-time recovery. Lambda roles receive log permissions rather than administrator access.

## One-command run

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000`. LocalStack is health-checked before the API starts. Terraform runs inside the API container, so no host installation or AWS credentials are required.

The optional local parser uses Ollama:

```bash
docker compose --profile llm up -d ollama
docker compose --profile llm exec ollama ollama pull qwen2.5-coder:3b
docker compose up --build
```

If Ollama is unavailable and `parser=auto`, the deterministic parser takes over. Selecting `parser=ollama` makes parser availability mandatory.

## API

```bash
curl -X POST http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{"request":"S3 bucket, Lambda on upload, and DynamoDB","project_name":"upload-demo","parser":"deterministic","run_plan":true}'
```

The response contains the structured specification, parser used, every generated file, validation steps and logs, security findings, correction state, and base64 ZIP bundle. `GET /health` reports Terraform availability and supported resources.

## Tests

```bash
pip install -r requirements.txt
pytest
```

Tests cover parameter extraction, dependency inference, modular output, security controls, broken-HCL rejection, API bundles, and real Terraform `fmt/init/validate` when the binary is installed.

## Boundaries

The system never applies infrastructure. It supports a reviewed subset rather than arbitrary AWS resources. LocalStack planning checks provider graph and configuration behavior but is not identical to AWS. A production version needs OPA/Checkov policies, cost estimates, organization modules, remote state, authenticated users, isolated execution workers, request quotas, approval gates, and real-cloud integration tests.

## Suggested commits

1. `set up typed infrastructure schemas`
2. `add deterministic request planner`
3. `integrate schema-constrained Ollama parsing`
4. `render modular Terraform projects`
5. `add secure S3 and DynamoDB defaults`
6. `add least-privilege Lambda roles`
7. `run Terraform format init and validate`
8. `add LocalStack planning`
9. `implement safe correction pass`
10. `add downloadable project bundles`
11. `build validation studio frontend`
12. `add unit and Terraform integration tests`

```bash
git init -b main
git add app/models.py app/parser.py && git commit -m "add typed infrastructure planning"
git add app/generator.py && git commit -m "render secure modular Terraform projects"
git add app/validator.py && git commit -m "run Terraform validation and LocalStack planning"
git add app/main.py app/static && git commit -m "add generation API and validation studio"
git add tests && git commit -m "add unit and Terraform integration tests"
git add Dockerfile docker-compose.yml && git commit -m "add reproducible LocalStack runtime"
git add README.md && git commit -m "document architecture and safety boundaries"
gh repo create nl-to-infra-generator --public --source=. --remote=origin
git push -u origin main
```

MIT licensed.
