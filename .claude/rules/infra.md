---
paths:
  - "infra/**"
  - "docker/**"
  - ".github/workflows/**"
  - "src/madhya_kanoon_saathi/handlers/**"
---

# Infra rules

- Google Cloud, region **asia-south1** (DEC-086, supersedes the AWS plan). Always-free allowances first; any new
  service or paid feature is a major decision.
- Never run `terraform apply`, or gcloud commands that create/change/delete resources, without Malik's OK.
  Explain each cloud step before running it, one step at a time. `terraform plan` output is shown and explained
  before asking. `terraform destroy` is never run.
- Two stacks: `infra/terraform/bootstrap` (APIs, identities, IAM, Firestore database, secret names; applied by Malik
  from the laptop) and the app stack (applied from GitHub Actions). IAM grants live only in bootstrap, so the
  deploy account never needs IAM-admin rights.
- No VPC / VPC connector (DEC-029). One least-privilege service account per service; no primitive roles
  (Owner/Editor) and no wildcards unless justified.
- Secrets: Secret Manager secret *names* only in code/Terraform; values are added by Malik with gcloud and never
  appear in code, state, outputs or logs.
- CI deploys via Workload Identity Federation (repo + `main` only); no service-account key files anywhere.
- The answer image contains only the `serve` dependency group + models + index; tag = corpus manifest hash;
  Artifact Registry keeps one image (DEC-084, DEC-086).
- Handlers stay thin: parse request → call package code → return. Logic lives in the packages and is unit-tested.
- Firestore layout per DEC-087 (`docs/specs/firestore.md`).
- Every resource that supports labels gets `project=madhya-kanoon-saathi` (provider `default_labels`); names use
  the `mks-` prefix where the resource allows it.
- Pin versions: Terraform 1.17.2, google provider 8.11.0 (lock file committed).
