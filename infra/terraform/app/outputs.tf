output "ingress_url" {
  description = "Telegram webhook target (setWebhook url)."
  value       = google_cloud_run_v2_service.ingress.uri
}

output "answer_url" {
  value = google_cloud_run_v2_service.answer.uri
}
