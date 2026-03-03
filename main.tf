terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = aimlexplore"
  region  = "us-central1"
}

resource "google_storage_bucket" "secure_bucket" {
  name                        = "my-secure-bucket-001-unique"
  location                    = "US"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }

  encryption {
    default_kms_key_name = null
  }
}
