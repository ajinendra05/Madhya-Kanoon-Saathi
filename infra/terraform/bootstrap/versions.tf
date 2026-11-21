# Bootstrap stack (DEC-086): APIs, GitHub keyless login, deploy service account.
# Applied once by Malik from the laptop; the app stack is applied later from GitHub Actions.
terraform {
  # Terraform 1.17.2 = latest stable on releases.hashicorp.com (checked 2026-11-21).
  required_version = "= 1.17.2"

  required_providers {
    google = {
      source = "hashicorp/google"
      # 8.12.0 was 4 days old on 2026-11-21; 8.11.0 is the previous release
      # (registry.terraform.io/v1/providers/hashicorp/google/versions).
      version = "= 8.11.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  # Laptop runs use Malik's user login (gcloud auth application-default login);
  # bill API quota to this project instead of a gcloud default project.
  user_project_override = true
  billing_project       = var.project_id
}
