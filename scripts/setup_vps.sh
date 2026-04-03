#!/usr/bin/env bash
set -euo pipefail

# Ubuntu 22.04+ hardening and deploy bootstrap for Omini.

DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_HOME="/home/${DEPLOY_USER}"
REPO_URL="${REPO_URL:-git@github.com:your-org/omini.git}"
REPO_DIR="${REPO_DIR:-${DEPLOY_HOME}/project}"
DEPLOY_PUBKEY="${DEPLOY_PUBKEY:-}"

sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git ufw

if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh

if ! id -u "${DEPLOY_USER}" >/dev/null 2>&1; then
  sudo adduser --disabled-password --gecos "" "${DEPLOY_USER}"
fi

sudo usermod -aG docker "${DEPLOY_USER}"

sudo -u "${DEPLOY_USER}" mkdir -p "${DEPLOY_HOME}/.ssh"
sudo chmod 700 "${DEPLOY_HOME}/.ssh"

if [[ -n "${DEPLOY_PUBKEY}" ]]; then
  echo "${DEPLOY_PUBKEY}" | sudo tee -a "${DEPLOY_HOME}/.ssh/authorized_keys" >/dev/null
  sudo chmod 600 "${DEPLOY_HOME}/.ssh/authorized_keys"
  sudo chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_HOME}/.ssh"
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  sudo -u "${DEPLOY_USER}" git clone "${REPO_URL}" "${REPO_DIR}"
else
  sudo -u "${DEPLOY_USER}" git -C "${REPO_DIR}" pull --ff-only
fi

if [[ ! -f "${REPO_DIR}/.env" ]]; then
  sudo -u "${DEPLOY_USER}" cp "${REPO_DIR}/.env.example" "${REPO_DIR}/.env"
fi

echo "Servidor preparado. Ajuste ${REPO_DIR}/.env e rode: docker compose up -d --build"
