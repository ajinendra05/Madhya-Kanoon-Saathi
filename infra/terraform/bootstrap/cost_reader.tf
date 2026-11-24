# W3.2 cost summary (DEC-095): GitHub Actions reads yesterday's Firestore records nightly through the
# same keyless login (Workload Identity Federation, repo + main only) as a read-only account.

resource "google_service_account" "cost_reader" {
  account_id   = "mks-cost-reader"
  display_name = "Nightly cost summary (read-only Firestore)"
}

# Read documents only: no writes, no deletes, no database settings.
resource "google_project_iam_member" "cost_reader_firestore" {
  project = var.project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${google_service_account.cost_reader.email}"
}

resource "google_service_account_iam_member" "cost_reader_wif" {
  service_account_id = google_service_account.cost_reader.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

output "cost_reader_service_account" {
  value = google_service_account.cost_reader.email
}
