terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

# Upload your SSH key to DigitalOcean
resource "digitalocean_ssh_key" "default" {
  name       = "terraform-runner-key"
  public_key = file(var.ssh_public_key_path)
}

# Create the droplet
resource "digitalocean_droplet" "runner" {
  name     = "python-runner"
  region   = var.region
  size     = var.droplet_size
  image    = "ubuntu-22-04-x64"
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = self.ipv4_address
    timeout     = "2m"
  }

  # 1. Install dependencies
  provisioner "remote-exec" {
    inline = [
      "apt-get update -y",
      "apt-get install -y python3 python3-pip git",
      "python3 --version",
      "git --version"
    ]
  }

  # 2. Clone the GitHub repo
  provisioner "remote-exec" {
    inline = [
      "echo '--- Cloning repository ---'",

      # Private repo: inject token into URL (no SSH key needed on the droplet)
      # Public repo:  leave github_token empty and the plain HTTPS URL is used
      "if [ -n '${var.github_token}' ]; then",
      "  git clone https://${var.github_token}@${trimprefix(var.repo_url, \"https://\")} /root/repo",
      "else",
      "  git clone ${var.repo_url} /root/repo",
      "fi",

      "echo '--- Checking out branch: ${var.repo_branch} ---'",
      "cd /root/repo && git checkout ${var.repo_branch}"
    ]
  }

  # 3. Install Python dependencies if a requirements.txt exists
  provisioner "remote-exec" {
    inline = [
      "if [ -f /root/repo/requirements.txt ]; then",
      "  echo '--- Installing Python dependencies ---'",
      "  pip3 install -r /root/repo/requirements.txt",
      "else",
      "  echo '--- No requirements.txt found, skipping ---'",
      "fi"
    ]
  }

  # 4. Run the target Python script
  provisioner "remote-exec" {
    inline = [
      "echo '--- Running ${var.python_script_path} ---'",
      "cd /root/repo && python3 ${var.python_script_path}",
      "echo '--- Script finished ---'"
    ]
  }
}
