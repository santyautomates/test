provider "google" {
  project = "aimlexplore"
  region  = "us-central1"
}

resource "google_storage_bucket" "secure_bucket" {
  name                        = "my-secure-bucket-12345"
  location                    = "US"
  uniform_bucket_level_access = true
  force_destroy               = false
}

resource "google_storage_bucket_iam_member" "private_access" {
  bucket = google_storage_bucket.secure_bucket.name
  role   = "roles/storage.objectViewer"
  member = "user:admin@example.com"
}
