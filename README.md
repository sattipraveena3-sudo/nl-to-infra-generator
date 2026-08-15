# Natural-Language-to-Infrastructure Generator

I built this project to convert a constrained English infrastructure request into auditable Terraform. It supports S3, Lambda, DynamoDB, IAM roles, and S3 event notifications. The default parser is deterministic and needs no paid model; the configuration shows how a local Ollama parser can be added later.

```text
request → structured resource specification → HCL renderer → terraform init/validate → result
                                                    ↓
                                              LocalStack endpoints
```

## Run

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000`, or run locally with `pip install -r requirements.txt && uvicorn app.main:app --reload`.

## API

`POST /generate` accepts `{"request":"S3 bucket and Lambda triggered on upload"}`. The response contains the parsed specification, Terraform, validation commands, and output.

## Scope and limitations

This deliberately does not claim arbitrary AWS coverage. It renders reviewed templates rather than unrestricted HCL, does not apply infrastructure, and runs `validate` rather than a credentialed cloud deployment. LocalStack supports offline provider endpoints; a production system would add policy-as-code, cost estimation, secure module registries, sandboxed planning, approval gates, and a schema-constrained local model parser.

## Tests

```bash
pytest
```

## Suggested commits

1. `set up project scaffolding`
2. `add structured infrastructure specification`
3. `implement deterministic request parser`
4. `add Terraform HCL renderer`
5. `add Terraform validation runner`
6. `configure LocalStack provider endpoints`
7. `add FastAPI generation endpoint`
8. `build Terraform preview frontend`
9. `add parser and validation tests`
10. `add Docker and LocalStack setup`
11. `document supported resource scope`

## GitHub CLI

```bash
git init -b main
git add app/models.py .gitignore .env.example && git commit -m "set up project scaffolding"
git add app/parser.py && git commit -m "implement deterministic request parser"
git add app/generator.py && git commit -m "add Terraform HCL renderer"
git add app/validator.py && git commit -m "add Terraform validation runner"
git add app/main.py app/static && git commit -m "add API and frontend"
git add tests requirements.txt && git commit -m "add parser and validation tests"
git add Dockerfile docker-compose.yml && git commit -m "add Docker and LocalStack setup"
git add README.md && git commit -m "document supported resource scope"
gh auth login
gh repo create nl-to-infra-generator --public --source=. --remote=origin
git push -u origin main
```

## License

MIT
