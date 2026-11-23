variable "project_id" {
  description = "Google Cloud project id (not secret)."
  type        = string
  default     = "mks-prod-515410"
}

variable "region" {
  description = "All resources stay in Mumbai (DEC-086)."
  type        = string
  default     = "asia-south1"
}

variable "github_repo" {
  description = "owner/name of the only repository allowed to deploy."
  type        = string
  default     = "ajinendra05/Madhya-Kanoon-Saathi"
}

variable "state_bucket" {
  description = "Terraform state bucket (created by hand; must match backend.tf)."
  type        = string
  default     = "mks-prod-515410-tfstate"
}

variable "project_number" {
  description = "Numeric project id (not secret); names Google's service agents."
  type        = string
  default     = "164560503250"
}
