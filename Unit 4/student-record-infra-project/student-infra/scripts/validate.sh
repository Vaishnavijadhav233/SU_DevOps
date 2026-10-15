#!/usr/bin/env bash
# Four-gate post-deployment validation. Usage: ./scripts/validate.sh <EC2_PUBLIC_IP>
set -u
EC2_IP="${1:?Usage: $0 <EC2_PUBLIC_IP>}"
KEY="${SSH_KEY:-$HOME/.ssh/student-aws-key}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$EC2_IP"
BODY='{"student_id":1,"subject":"DevOps","marks":88}'
FAIL=0

check() {  # usage: check "<description>" <command...>
  local desc="$1"; shift
  if "$@" >/tmp/gate.out 2>&1; then
    echo "  [PASS] $desc"
  else
    echo "  [FAIL] $desc"; cat /tmp/gate.out; FAIL=1
  fi
}

api_health()   { curl -s -f "http://$EC2_IP/api/health" | jq -e '.status == "UP"'; }
api_students() { curl -s -f "http://$EC2_IP/api/students" | jq -e '.count >= 2'; }
api_marks()    { [ "$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://$EC2_IP/api/marks" -H 'Content-Type: application/json' -d "$BODY")" = 201 ]; }

if [ -z "${SKIP_INFRA_GATES:-}" ]; then
  echo "=== Gate 1: Network & OS ==="
  check "SSH port 22 reachable" nc -zv -w 5 "$EC2_IP" 22
  check "Ubuntu host responds (uptime)" $SSH uptime

  echo "=== Gate 2: Daemons & Ports ==="
  check "Docker daemon active" $SSH "systemctl is-active docker"
  check "Nginx service active" $SSH "systemctl is-active nginx"
  check "Port 80 reachable" nc -zv -w 5 "$EC2_IP" 80

  echo "=== Gate 3: App Container ==="
  check "Container student-app is Up" $SSH "docker ps --filter name=student-app --format '{{.Status}}' | grep -q Up"
  check "SQLite database file exists" $SSH "ls /opt/student-app/data/students.db"
fi

echo "=== Gate 4: API Smoke Tests (through Nginx on port 80) ==="
check "GET /api/health returns UP" api_health
check "GET /api/students count >= 2" api_students
check "POST /api/marks returns 201" api_marks

echo
if [ "$FAIL" -eq 0 ]; then echo "RESULT: ALL GATES PASSED"; else echo "RESULT: SOME GATES FAILED"; exit 1; fi
