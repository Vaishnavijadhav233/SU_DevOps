#!/usr/bin/env bash
# Terraform -> Ansible handshake: turns Terraform outputs into an Ansible inventory.
set -euo pipefail
cd "$(dirname "$0")/../terraform"

IP=$(terraform output -raw app_server_public_ip)
ENV_NAME=$(terraform workspace show)
KEY="${SSH_KEY:-$HOME/.ssh/student-aws-key}"

cat > ../ansible/inventory/hosts.ini <<INV
[student_servers:children]
${ENV_NAME}

[${ENV_NAME}]
student-host ansible_host=${IP} ansible_user=ubuntu ansible_ssh_private_key_file=${KEY}
INV

echo "Inventory written for workspace '${ENV_NAME}' -> ${IP}"
cat ../ansible/inventory/hosts.ini
