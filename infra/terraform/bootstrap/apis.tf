# The APIs enabled by hand in Step 4, now recorded in code (imported, not re-created).
# disable_on_destroy = false: removing a line here never switches a service off under running resources.
locals {
  apis = toset([
    "run.googleapis.com",                  # Cloud Run: ingress + answer services
    "pubsub.googleapis.com",               # queue between them
    "firestore.googleapis.com",            # dedup, logs, quotas
    "secretmanager.googleapis.com",        # Telegram / Sarvam secrets
    "cloudscheduler.googleapis.com",       # law-watch, cost summary
    "artifactregistry.googleapis.com",     # container image
    "storage.googleapis.com",              # Terraform state bucket
    "iam.googleapis.com",                  # service accounts
    "iamcredentials.googleapis.com",       # short-lived tokens for GitHub
    "sts.googleapis.com",                  # token exchange (Workload Identity Federation)
    "cloudresourcemanager.googleapis.com", # Terraform reads the project
    "serviceusage.googleapis.com",         # Terraform manages these switches
  ])
}

resource "google_project_service" "api" {
  for_each           = local.apis
  service            = each.value
  disable_on_destroy = false
}

# Already enabled by hand (Step 4, 2026-11-21): adopt them into state instead of "creating" them.
import {
  for_each = local.apis
  to       = google_project_service.api[each.value]
  id       = "${var.project_id}/${each.value}"
}
