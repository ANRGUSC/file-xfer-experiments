variable "do_token" {
  description = "Your DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "ssh_public_key_path" {
  description = "Path to your SSH public key (e.g. ~/.ssh/id_rsa.pub)"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_private_key_path" {
  description = "Path to your SSH private key (e.g. ~/.ssh/id_rsa)"
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "repo_url" {
  description = "HTTPS URL of the GitHub repo (e.g. https://github.com/youruser/yourrepo)"
  type        = string
}

variable "repo_branch" {
  description = "Branch to check out"
  type        = string
  default     = "main"
}

variable "github_token" {
  description = "GitHub personal access token — required for private repos, leave empty for public repos"
  type        = string
  sensitive   = true
  default     = ""
}

variable "python_script_path" {
  description = "Path to the Python script inside the repo (e.g. scripts/main.py)"
  type        = string
  default     = "main.py"
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc3"
}

variable "droplet_size" {
  description = "Droplet size slug"
  type        = string
  default     = "s-1vcpu-1gb"
}
