# App stack (DEC-086, DEC-088, DEC-089): queue, dead-letter queue, the two Cloud Run services and
# the resource-level grants between them. Identities, secrets and the database live in bootstrap.
terraform {
  required_version = "= 1.17.2"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 8.11.0" # same pin and lock file as bootstrap
    }
  }

  backend "gcs" {
    bucket = "mks-prod-515410-tfstate"
    prefix = "app"
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id

  default_labels = {
    project = "madhya-kanoon-saathi"
  }
}
