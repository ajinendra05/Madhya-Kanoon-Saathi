# State lives in the versioned, non-public bucket created by hand in Step 5 (DEC-086 item 6).
# A backend block cannot use variables, so the bucket name is written out.
terraform {
  backend "gcs" {
    bucket = "mks-prod-515410-tfstate"
    prefix = "bootstrap"
  }
}
