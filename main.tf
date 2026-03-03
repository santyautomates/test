terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "aimlexplore"
  region  = "us-central1"
}

# Secure GCS bucket configuration
resource "google_storage_bucket" "app_data" {
  name     = "company-app-data-bucket-test-001"
  location = "US"

  # Prevent accidental deletion of production data
  force_destroy = false

  # Enforce uniform bucket-level access (recommended)
  uniform_bucket_level_access = true

  # Prevent public access at bucket level
  public_access_prevention = "enforced"

  # Enable object versioning for recovery protection
  versioning {
    enabled = true
  }

  # Enable encryption with Google-managed key (default)
  encryption {
    default_kms_key_name = null
  }

  # Optional: Lifecycle rule example (cost optimization)
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = "dev"
    owner       = "platform-team"
  }
}

# Example: Grant access only to a specific service account (NOT public)
resource "google_storage_bucket_iam_member" "app_access" {
  bucket = google_storage_bucket.app_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:app-sa@your-project-id.iam.gserviceaccount.com"
}
