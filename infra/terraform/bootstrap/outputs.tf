# Values GitHub Actions needs (google-github-actions/auth). Neither is secret.
output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account" {
  value = google_service_account.github_deploy.email
}
