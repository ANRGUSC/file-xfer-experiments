output "droplet_ip" {
  description = "Public IP address of the droplet"
  value       = digitalocean_droplet.runner.ipv4_address
}

output "droplet_id" {
  description = "ID of the created droplet"
  value       = digitalocean_droplet.runner.id
}
