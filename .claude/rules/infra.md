---
paths:
  - "infra/**"
  - "docker/**"
  - ".github/workflows/**"
  - "src/madhya_kanoon_saathi/handlers/**"
---

# Infra rules

- Region ap-south-1. Always-free services first (DEC-002). Any new AWS service or paid feature is a major decision.
- Never run `terraform apply`, or AWS CLI commands that create/change/delete resources, without Malik's OK.
  `terraform plan` output is shown before asking. `terraform destroy` is never run.
- No VPC / NAT (DEC-029). Least-privilege IAM role per Lambda; no wildcards on actions or resources unless justified.
- Secrets: SSM Parameter Store SecureString names only in code/Terraform; values never in code, state outputs or logs.
- CI deploys via GitHub OIDC; no long-lived AWS keys in GitHub secrets.
- Answer-Lambda image contains only the `serve` dependency group + models + index; tag = corpus manifest hash;
  ECR keeps the last 3 images (DEC-024).
- Handlers stay thin: parse event → call package code → return. Logic lives in the packages and is unit-tested.
- DynamoDB tables wait for the pending schema decision (OPEN_QUESTIONS D1).
- Tag every resource with `project=madhya-kanoon-saathi` and use the `mks-` name prefix.
