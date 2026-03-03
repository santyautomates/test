terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "my-test-gcp-project-123"
  region  = "us-central1"
}

# A basic GCS bucket with several intentional missing best practices
resource "google_storage_bucket" "app_data" {
  name          = "company-app-data-bucket-test-001"
  location      = "US"
  
  # AI should flag this: force_destroy is highly dangerous for production data
  force_destroy = true 

  # AI should notice these are missing:
  # - uniform_bucket_level_access
  # - public_access_prevention
  # - versioning block
}

# Intentional critical security flaw: Granting public read access
resource "google_sorage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.app_data.name
  role   = "roles/stoage.objectViewer"
  member = "allUsers"
