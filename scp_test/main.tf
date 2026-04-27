terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

# Variables
variable "do_token" {
  description = "DigitalOcean API token"
  sensitive   = true
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key for provisioner access"
  default     = "~/.ssh/id_ed25519"
}

variable "auxiliary_ip" {
  description = "IP of the auxiliary droplet to receive results"
  default     = "167.99.128.200"
}

variable "auxiliary_password" {
  description = "Password for auxiliary droplet"
  default     = "scpTesting@410RTH"
  sensitive   = true
}

variable "repo_url" {
  description = "GitHub repository URL"
  default     = "https://github.com/ANRGUSC/file-xfer-experiments"
}

variable "repo_branch" {
  description = "Branch to checkout"
  default     = "secondary1"
}

variable "run_timestamp" {
  description = "Timestamp for this run (YYYYMMDD_HHMMSS), used to namespace results on the auxiliary node"
  default     = "unknown"
}

# Generate SSH key for inter-droplet communication
resource "tls_private_key" "inter_droplet" {
  algorithm = "ED25519"
}

# Look up existing SSH key on DigitalOcean
data "digitalocean_ssh_key" "default" {
  name = "terraform-runner-key"
}

# User data script template
locals {
  user_data_script = <<EOF
#!/bin/bash
set -ex
exec > /var/log/cloud-init-script.log 2>&1

echo "=== Droplet setup starting ==="
date

# Install dependencies
apt-get update -y
apt-get install -y python3 python3-pip git sshpass iperf3

# Set up SSH key for inter-droplet communication
mkdir -p /root/.ssh
chmod 700 /root/.ssh

cat > /root/.ssh/inter_droplet << 'KEYEOF'
${tls_private_key.inter_droplet.private_key_openssh}
KEYEOF
chmod 600 /root/.ssh/inter_droplet

echo '${tls_private_key.inter_droplet.public_key_openssh}' >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Configure SSH to use the inter-droplet key by default
cat > /root/.ssh/config << 'SSHCONFIG'
Host *
  IdentityFile /root/.ssh/inter_droplet
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
SSHCONFIG
chmod 600 /root/.ssh/config

# Clone repo
git clone ${var.repo_url} /root/repo
cd /root/repo && git checkout ${var.repo_branch}

# Generate test files
cd /root/repo && python3 generate_test_files.py

# Write iperf measurement script
cat > /root/run_iperf.py << 'PYEOF'
import subprocess, json, sys, statistics, os

target_ip = sys.argv[1]
out_file = sys.argv[2]
port = int(sys.argv[3]) if len(sys.argv) > 3 else 5201

bw_values = []
for i in range(10):
    try:
        r = subprocess.run(
            ["iperf3", "-c", target_ip, "-J", "-t", "5", "-p", str(port)],
            capture_output=True, text=True, timeout=30
        )
        d = json.loads(r.stdout)
        bw = d["end"]["sum_received"]["bits_per_second"]
        bw_values.append(bw)
        print("Run {}: {:.2f} Mbps".format(i + 1, bw / 1e6))
    except Exception as e:
        print("Run {} failed: {}".format(i + 1, e))

if bw_values:
    med = statistics.median(bw_values)
    result = {
        "iperf_runs_bps": bw_values,
        "iperf_median_bps": med,
        "iperf_median_mbps": round(med / 1e6, 4)
    }
    out_dir = os.path.dirname(out_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print("Median: {:.2f} Mbps -> {}".format(med / 1e6, out_file))
else:
    print("No iperf data collected")
PYEOF

echo "=== Setup complete ==="
touch /root/ready
date
EOF
}

# Create all 4 droplets
resource "digitalocean_droplet" "london" {
  name      = "scp-test-london"
  region    = "lon1"
  size      = "s-1vcpu-1gb"
  image     = "ubuntu-22-04-x64"
  ssh_keys  = [data.digitalocean_ssh_key.default.fingerprint]
  user_data = local.user_data_script
}

resource "digitalocean_droplet" "amsterdam" {
  name      = "scp-test-amsterdam"
  region    = "ams3"
  size      = "s-1vcpu-1gb"
  image     = "ubuntu-22-04-x64"
  ssh_keys  = [data.digitalocean_ssh_key.default.fingerprint]
  user_data = local.user_data_script
}

resource "digitalocean_droplet" "nyc" {
  name      = "scp-test-nyc"
  region    = "nyc3"
  size      = "s-1vcpu-1gb"
  image     = "ubuntu-22-04-x64"
  ssh_keys  = [data.digitalocean_ssh_key.default.fingerprint]
  user_data = local.user_data_script
}

resource "digitalocean_droplet" "toronto" {
  name      = "scp-test-toronto"
  region    = "tor1"
  size      = "s-1vcpu-1gb"
  image     = "ubuntu-22-04-x64"
  ssh_keys  = [data.digitalocean_ssh_key.default.fingerprint]
  user_data = local.user_data_script
}


# London → Amsterdam, Toronto, NYC  (sequential on London droplet)
resource "null_resource" "scp_from_london" {
  depends_on = [
    digitalocean_droplet.london,
    digitalocean_droplet.amsterdam,
    digitalocean_droplet.nyc,
    digitalocean_droplet.toronto
  ]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = digitalocean_droplet.london.ipv4_address
    timeout     = "10m"
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /root/ready ]; do sleep 5; done",

      # London → Amsterdam
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.amsterdam.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for amsterdam...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.amsterdam.ipv4_address} 'fuser -k 5201/tcp 2>/dev/null || true; nohup iperf3 -s -p 5201 > /tmp/iperf3_5201.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.amsterdam.ipv4_address} /root/repo/results/iperf_results.json 5201",
      "ssh root@${digitalocean_droplet.amsterdam.ipv4_address} 'fuser -k 5201/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.amsterdam.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/london_to_amsterdam/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/london_to_amsterdam/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # London → Toronto
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.toronto.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for toronto...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.toronto.ipv4_address} 'fuser -k 5201/tcp 2>/dev/null || true; nohup iperf3 -s -p 5201 > /tmp/iperf3_5201.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.toronto.ipv4_address} /root/repo/results/iperf_results.json 5201",
      "ssh root@${digitalocean_droplet.toronto.ipv4_address} 'fuser -k 5201/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.toronto.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/london_to_toronto/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/london_to_toronto/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # London → NYC
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.nyc.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for nyc...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.nyc.ipv4_address} 'fuser -k 5201/tcp 2>/dev/null || true; nohup iperf3 -s -p 5201 > /tmp/iperf3_5201.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.nyc.ipv4_address} /root/repo/results/iperf_results.json 5201",
      "ssh root@${digitalocean_droplet.nyc.ipv4_address} 'fuser -k 5201/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.nyc.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/london_to_nyc/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/london_to_nyc/${var.run_timestamp}/",
      "rm -f /root/repo/results/*"
    ]
  }
}

# Amsterdam → London, NYC, Toronto  (sequential on Amsterdam droplet)
resource "null_resource" "scp_from_amsterdam" {
  depends_on = [
    digitalocean_droplet.london,
    digitalocean_droplet.amsterdam,
    digitalocean_droplet.nyc,
    digitalocean_droplet.toronto
  ]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = digitalocean_droplet.amsterdam.ipv4_address
    timeout     = "10m"
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /root/ready ]; do sleep 5; done",

      # Amsterdam → London
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.london.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for london...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.london.ipv4_address} 'fuser -k 5202/tcp 2>/dev/null || true; nohup iperf3 -s -p 5202 > /tmp/iperf3_5202.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.london.ipv4_address} /root/repo/results/iperf_results.json 5202",
      "ssh root@${digitalocean_droplet.london.ipv4_address} 'fuser -k 5202/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.london.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/amsterdam_to_london/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/amsterdam_to_london/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # Amsterdam → NYC
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.nyc.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for nyc...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.nyc.ipv4_address} 'fuser -k 5202/tcp 2>/dev/null || true; nohup iperf3 -s -p 5202 > /tmp/iperf3_5202.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.nyc.ipv4_address} /root/repo/results/iperf_results.json 5202",
      "ssh root@${digitalocean_droplet.nyc.ipv4_address} 'fuser -k 5202/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.nyc.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/amsterdam_to_nyc/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/amsterdam_to_nyc/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # Amsterdam → Toronto
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.toronto.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for toronto...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.toronto.ipv4_address} 'fuser -k 5202/tcp 2>/dev/null || true; nohup iperf3 -s -p 5202 > /tmp/iperf3_5202.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.toronto.ipv4_address} /root/repo/results/iperf_results.json 5202",
      "ssh root@${digitalocean_droplet.toronto.ipv4_address} 'fuser -k 5202/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.toronto.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/amsterdam_to_toronto/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/amsterdam_to_toronto/${var.run_timestamp}/",
      "rm -f /root/repo/results/*"
    ]
  }
}

# NYC → Toronto, London, Amsterdam  (sequential on NYC droplet)
resource "null_resource" "scp_from_nyc" {
  depends_on = [
    digitalocean_droplet.london,
    digitalocean_droplet.amsterdam,
    digitalocean_droplet.nyc,
    digitalocean_droplet.toronto
  ]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = digitalocean_droplet.nyc.ipv4_address
    timeout     = "10m"
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /root/ready ]; do sleep 5; done",

      # NYC → Toronto
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.toronto.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for toronto...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.toronto.ipv4_address} 'fuser -k 5203/tcp 2>/dev/null || true; nohup iperf3 -s -p 5203 > /tmp/iperf3_5203.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.toronto.ipv4_address} /root/repo/results/iperf_results.json 5203",
      "ssh root@${digitalocean_droplet.toronto.ipv4_address} 'fuser -k 5203/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.toronto.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/nyc_to_toronto/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/nyc_to_toronto/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # NYC → London
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.london.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for london...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.london.ipv4_address} 'fuser -k 5203/tcp 2>/dev/null || true; nohup iperf3 -s -p 5203 > /tmp/iperf3_5203.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.london.ipv4_address} /root/repo/results/iperf_results.json 5203",
      "ssh root@${digitalocean_droplet.london.ipv4_address} 'fuser -k 5203/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.london.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/nyc_to_london/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/nyc_to_london/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # NYC → Amsterdam
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.amsterdam.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for amsterdam...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.amsterdam.ipv4_address} 'fuser -k 5203/tcp 2>/dev/null || true; nohup iperf3 -s -p 5203 > /tmp/iperf3_5203.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.amsterdam.ipv4_address} /root/repo/results/iperf_results.json 5203",
      "ssh root@${digitalocean_droplet.amsterdam.ipv4_address} 'fuser -k 5203/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.amsterdam.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/nyc_to_amsterdam/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/nyc_to_amsterdam/${var.run_timestamp}/",
      "rm -f /root/repo/results/*"
    ]
  }
}

# Toronto → NYC, London, Amsterdam  (sequential on Toronto droplet)
resource "null_resource" "scp_from_toronto" {
  depends_on = [
    digitalocean_droplet.london,
    digitalocean_droplet.amsterdam,
    digitalocean_droplet.nyc,
    digitalocean_droplet.toronto
  ]

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = digitalocean_droplet.toronto.ipv4_address
    timeout     = "10m"
  }

  provisioner "remote-exec" {
    inline = [
      "while [ ! -f /root/ready ]; do sleep 5; done",

      # Toronto → NYC
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.nyc.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for nyc...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.nyc.ipv4_address} 'fuser -k 5204/tcp 2>/dev/null || true; nohup iperf3 -s -p 5204 > /tmp/iperf3_5204.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.nyc.ipv4_address} /root/repo/results/iperf_results.json 5204",
      "ssh root@${digitalocean_droplet.nyc.ipv4_address} 'fuser -k 5204/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.nyc.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/toronto_to_nyc/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/toronto_to_nyc/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # Toronto → London
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.london.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for london...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.london.ipv4_address} 'fuser -k 5204/tcp 2>/dev/null || true; nohup iperf3 -s -p 5204 > /tmp/iperf3_5204.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.london.ipv4_address} /root/repo/results/iperf_results.json 5204",
      "ssh root@${digitalocean_droplet.london.ipv4_address} 'fuser -k 5204/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.london.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/toronto_to_london/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/toronto_to_london/${var.run_timestamp}/",
      "rm -f /root/repo/results/*",

      # Toronto → Amsterdam
      "while ! ssh -o ConnectTimeout=5 root@${digitalocean_droplet.amsterdam.ipv4_address} 'test -f /root/ready' 2>/dev/null; do echo 'Waiting for amsterdam...'; sleep 10; done",
      "ssh root@${digitalocean_droplet.amsterdam.ipv4_address} 'fuser -k 5204/tcp 2>/dev/null || true; nohup iperf3 -s -p 5204 > /tmp/iperf3_5204.log 2>&1 &'",
      "sleep 3",
      "python3 /root/run_iperf.py ${digitalocean_droplet.amsterdam.ipv4_address} /root/repo/results/iperf_results.json 5204",
      "ssh root@${digitalocean_droplet.amsterdam.ipv4_address} 'fuser -k 5204/tcp 2>/dev/null || true'",
      "cd /root/repo && python3 scpSpeed.py ${digitalocean_droplet.amsterdam.ipv4_address}",
      "sshpass -p '${var.auxiliary_password}' ssh -o StrictHostKeyChecking=no root@${var.auxiliary_ip} 'mkdir -p /root/toronto_to_amsterdam/${var.run_timestamp}'",
      "sshpass -p '${var.auxiliary_password}' scp -o StrictHostKeyChecking=no /root/repo/results/* root@${var.auxiliary_ip}:/root/toronto_to_amsterdam/${var.run_timestamp}/",
      "rm -f /root/repo/results/*"
    ]
  }
}

# Outputs
output "london_ip" {
  value       = digitalocean_droplet.london.ipv4_address
  description = "London droplet IP"
}

output "amsterdam_ip" {
  value       = digitalocean_droplet.amsterdam.ipv4_address
  description = "Amsterdam droplet IP"
}

output "nyc_ip" {
  value       = digitalocean_droplet.nyc.ipv4_address
  description = "NYC droplet IP"
}

output "toronto_ip" {
  value       = digitalocean_droplet.toronto.ipv4_address
  description = "Toronto droplet IP"
}
