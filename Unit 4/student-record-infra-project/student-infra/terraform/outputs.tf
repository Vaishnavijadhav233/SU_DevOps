output "app_server_public_ip" {
  description = "Public IP used by Ansible and for browsing"
  value       = aws_instance.app_server.public_ip
}

output "app_url" {
  value = "http://${aws_instance.app_server.public_ip}"
}

output "backup_bucket_name" {
  value = aws_s3_bucket.backups.bucket
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/${var.key_name} ubuntu@${aws_instance.app_server.public_ip}"
}
