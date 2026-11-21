# Workload Identity Federation (DEC-086 item 7): GitHub Actions proves who it is with its own
# short-lived OIDC token; Google swaps it for short-lived credentials. No key files exist.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "mks-github"
  display_name              = "GitHub Actions"
  description               = "Keyless deploys from ${var.github_repo}"
  depends_on                = [google_project_service.api]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Only tokens from this repository's main branch are accepted at all.
  attribute_condition = "assertion.repository == \"${var.github_repo}\" && assertion.ref == \"refs/heads/main\""
}

resource "google_service_account" "github_deploy" {
  account_id   = "mks-github-deploy"
  display_name = "GitHub Actions deploy (Madhya Kanoon Saathi)"
  depends_on   = [google_project_service.api]
}

# Let identities from the repository (already limited to main above) act as the deploy account.
resource "google_service_account_iam_member" "github_wif" {
  service_account_id = google_service_account.github_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# Project roles for deploys. No Owner, Editor, billing or IAM-admin roles. No Firestore or
# Secret Manager roles: the database and secret boxes live in bootstrap, and
# secretmanager.admin would let a workflow read secret values.
locals {
  deploy_roles = toset([
    "roles/run.admin",               # deploy the two Cloud Run services
    "roles/artifactregistry.writer", # push the container image
    "roles/iam.serviceAccountUser",  # run services as their own narrow accounts
    "roles/pubsub.admin",            # queue + dead-letter topic
    "roles/cloudscheduler.admin",    # law-watch and cost-summary schedules
  ])
}

resource "google_project_iam_member" "github_deploy" {
  for_each = local.deploy_roles
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.github_deploy.email}"
}

# Read/write Terraform state, on the state bucket only.
resource "google_storage_bucket_iam_member" "github_deploy_state" {
  bucket = var.state_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_deploy.email}"
}
