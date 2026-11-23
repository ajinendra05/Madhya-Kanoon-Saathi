variable "project_id" {
  type    = string
  default = "mks-prod-515410"
}

variable "project_number" {
  description = "Numeric project id (not secret); names Google's service agents."
  type        = string
  default     = "164560503250"
}

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "image_tag" {
  description = "Tag of asia-south1-docker.pkg.dev/<project>/mks/bot built by build-image.yml."
  type        = string
  default     = "m5dd9a6afe7fb-187dea0"
}
