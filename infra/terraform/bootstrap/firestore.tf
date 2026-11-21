# Firestore and the chat-hash secret (DEC-087). In the bootstrap stack because the database
# location can never change and the deploy account should not be able to delete it.

resource "google_firestore_database" "main" {
  name             = "(default)" # the free tier is believed to cover only this one (OPEN_QUESTIONS P16)
  location_id      = var.region  # asia-south1, permanent
  type             = "FIRESTORE_NATIVE"
  database_edition = "STANDARD"

  # Two locks: Google refuses deletion, and Terraform refuses to plan one.
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  deletion_policy         = "PREVENT"

  depends_on = [google_project_service.api]
}

# Auto-delete documents once their expire_at time has passed (TTL policy per collection).
resource "google_firestore_field" "ttl" {
  for_each   = toset(["seen_updates", "queries", "quotas"])
  database   = google_firestore_database.main.name
  collection = each.value
  field      = "expire_at"

  ttl_config {}
}

# Only the empty secret "box"; Malik adds the value with gcloud, so it never enters code or state.
resource "google_secret_manager_secret" "chat_hash_key" {
  secret_id = "MKS_CHAT_HASH_KEY"

  replication {
    user_managed {
      replicas {
        location = var.region # the key stays in India
      }
    }
  }

  depends_on = [google_project_service.api]
}
