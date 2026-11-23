locals {
  image        = "${var.region}-docker.pkg.dev/${var.project_id}/mks/bot:${var.image_tag}"
  pubsub_agent = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  sa = {
    ingress = "mks-ingress@${var.project_id}.iam.gserviceaccount.com"
    answer  = "mks-answer@${var.project_id}.iam.gserviceaccount.com"
    push    = "mks-pubsub-push@${var.project_id}.iam.gserviceaccount.com"
  }
}

# ---------------- Queue (DEC-010) ----------------
resource "google_pubsub_topic" "questions" {
  name = "mks-questions"
}

resource "google_pubsub_topic" "dead" {
  name = "mks-questions-dead"
}

# Failed deliveries land here for inspection; kept 7 days, then dropped.
resource "google_pubsub_subscription" "dead_inspect" {
  name                       = "mks-questions-dead-inspect"
  topic                      = google_pubsub_topic.dead.id
  message_retention_duration = "604800s"
  expiration_policy {
    ttl = "" # never expire
  }
}

resource "google_pubsub_subscription" "answer_push" {
  name  = "mks-answer-push"
  topic = google_pubsub_topic.questions.id

  # Max allowed; the answer service always acks within one request (DEC-088).
  ack_deadline_seconds = 600
  # 1 day (min 10 min): queued messages carry a raw chat id, so keep them briefly.
  message_retention_duration = "86400s"

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.answer.uri}/"
    oidc_token {
      service_account_email = local.sa.push
      audience              = google_cloud_run_v2_service.answer.uri
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead.id
    max_delivery_attempts = 5 # allowed range 5-100
  }

  expiration_policy {
    ttl = ""
  }
}

# ---------------- Answer service (DEC-089: 4 GiB, 2 vCPU, max 2) ----------------
resource "google_cloud_run_v2_service" "answer" {
  name     = "mks-answer"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL" # reachable by Pub/Sub; IAM below allows only mks-pubsub-push

  template {
    service_account                  = local.sa.answer
    max_instance_request_concurrency = 1      # one CPU-heavy question per container
    timeout                          = "600s" # = ack deadline

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = local.image # default CMD: handlers.answer

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
        cpu_idle          = true # billed only while handling a request
        startup_cpu_boost = true # faster model loading on cold start
      }

      # Port opens only after models + indexes are loaded; allow up to 240 s.
      startup_probe {
        tcp_socket {
          port = 8080
        }
        period_seconds    = 10
        timeout_seconds   = 5
        failure_threshold = 24
      }

      env {
        name  = "MKS_PROJECT"
        value = var.project_id
      }
      dynamic "env" {
        for_each = toset(["TELEGRAM_BOT_TOKEN", "SARVAM_API_KEY", "MKS_CHAT_HASH_KEY"])
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }
}

# Only the push identity may call the answer service.
resource "google_cloud_run_v2_service_iam_member" "answer_invoker" {
  name     = google_cloud_run_v2_service.answer.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.sa.push}"
}

# ---------------- Ingress service (Telegram webhook) ----------------
resource "google_cloud_run_v2_service" "ingress" {
  name     = "mks-ingress"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = local.sa.ingress
    max_instance_request_concurrency = 20
    timeout                          = "30s"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image   = local.image
      command = ["python", "-m", "madhya_kanoon_saathi.handlers.ingress"]

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      env {
        name  = "MKS_PROJECT"
        value = var.project_id
      }
      env {
        name  = "MKS_TOPIC"
        value = google_pubsub_topic.questions.name
      }
      env {
        name = "TELEGRAM_WEBHOOK_SECRET"
        value_source {
          secret_key_ref {
            secret  = "TELEGRAM_WEBHOOK_SECRET"
            version = "latest"
          }
        }
      }
    }
  }
}

# Telegram cannot sign in to Google, so the webhook URL is public; the secret header is the lock.
resource "google_cloud_run_v2_service_iam_member" "ingress_public" {
  name     = google_cloud_run_v2_service.ingress.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------- Resource-level grants ----------------
# Ingress may publish only to the questions topic.
resource "google_pubsub_topic_iam_member" "ingress_publish" {
  topic  = google_pubsub_topic.questions.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${local.sa.ingress}"
}

# Pub/Sub's service agent moves failed messages to the dead-letter topic
# (docs.cloud.google.com/pubsub/docs/handling-failures, read 2026-11-21).
resource "google_pubsub_topic_iam_member" "agent_dead_publish" {
  topic  = google_pubsub_topic.dead.id
  role   = "roles/pubsub.publisher"
  member = local.pubsub_agent
}

resource "google_pubsub_subscription_iam_member" "agent_subscribe" {
  subscription = google_pubsub_subscription.answer_push.id
  role         = "roles/pubsub.subscriber"
  member       = local.pubsub_agent
}
