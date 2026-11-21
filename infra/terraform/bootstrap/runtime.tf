# Step 11 (DEC-084, DEC-086): image store, the accounts the services run as, and their grants.
# Kept in bootstrap so the GitHub deploy account never needs IAM-admin rights.

# --- Image store: one Docker repository, keep only the newest image ---
resource "google_artifact_registry_repository" "images" {
  repository_id = "mks"
  location      = var.region
  format        = "DOCKER"
  description   = "Answer/ingress images: code + int8 models + indexes"

  # KEEP wins over DELETE: everything older than a day is removed except the most recent image.
  cleanup_policies {
    id     = "delete-older-than-1-day"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "86400s"
    }
  }
  cleanup_policies {
    id     = "keep-newest"
    action = "KEEP"
    most_recent_versions {
      keep_count = 1
    }
  }

  depends_on = [google_project_service.api]
}

# --- Secret boxes; Malik adds the values (never in code or state) ---
locals {
  app_secrets = toset(["TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET", "SARVAM_API_KEY"])
}

resource "google_secret_manager_secret" "app" {
  for_each  = local.app_secrets
  secret_id = each.value

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.api]
}

# --- Runtime service accounts ---
resource "google_service_account" "ingress" {
  account_id   = "mks-ingress"
  display_name = "Ingress service (webhook check, dedup, enqueue)"
}

resource "google_service_account" "answer" {
  account_id   = "mks-answer"
  display_name = "Answer service (pipeline, Telegram reply)"
}

resource "google_service_account" "pubsub_push" {
  account_id   = "mks-pubsub-push"
  display_name = "Pub/Sub push identity (calls the answer service)"
}

# Firestore access cannot be narrowed per collection: both services get datastore.user.
resource "google_project_iam_member" "firestore_user" {
  for_each = {
    ingress = google_service_account.ingress.email
    answer  = google_service_account.answer.email
  }
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${each.value}"
}

# TODO(narrow): project-wide until the topic and the answer service exist in the app stack;
# then grant on the topic / service only and remove these two.
resource "google_project_iam_member" "ingress_publish" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.ingress.email}"
}

resource "google_project_iam_member" "push_invoke" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.pubsub_push.email}"
}

# Each service may read only its own secrets.
locals {
  secret_readers = {
    "ingress-webhook" = { secret = "TELEGRAM_WEBHOOK_SECRET", sa = google_service_account.ingress.email }
    "answer-bot"      = { secret = "TELEGRAM_BOT_TOKEN", sa = google_service_account.answer.email }
    "answer-sarvam"   = { secret = "SARVAM_API_KEY", sa = google_service_account.answer.email }
    "answer-chathash" = { secret = "MKS_CHAT_HASH_KEY", sa = google_service_account.answer.email }
  }
}

resource "google_secret_manager_secret_iam_member" "reader" {
  for_each   = local.secret_readers
  secret_id  = each.value.secret
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${each.value.sa}"
  depends_on = [google_secret_manager_secret.app, google_secret_manager_secret.chat_hash_key]
}
