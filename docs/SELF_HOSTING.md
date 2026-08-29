# Self-Hosting Guide

Use this guide when you need full control over infrastructure — data residency, private networks, or compliance requirements that rule out FastAPI Cloud.

## When to self-host vs FastAPI Cloud

| | FastAPI Cloud | Self-hosted |
|--|---------------|-------------|
| Setup time | Minutes | Hours |
| HTTPS / scaling | Managed | You configure |
| Secrets | Dashboard + CLI | Your vault / env files |
| Best for | Quick client automations | Regulated / isolated workloads |

---

## Linux (Ubuntu/Debian VM)

### 1. Install dependencies

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv nginx certbot python3-certbot-nginx git

curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### 2. Deploy the app

```bash
sudo adduser --disabled-password --gecos "" fastapi
sudo mkdir -p /opt/fastapi-automation
sudo chown fastapi:fastapi /opt/fastapi-automation

sudo -u fastapi git clone https://github.com/your-org/fastapi-cloud-base-template.git /opt/fastapi-automation
cd /opt/fastapi-automation
sudo -u fastapi uv sync --frozen --extra all
```

### 3. Environment file

```bash
sudo -u fastapi cp .env.example .env
sudo -u fastapi nano .env   # set production values
sudo chmod 600 /opt/fastapi-automation/.env
sudo chown fastapi:fastapi /opt/fastapi-automation/.env
```

Prefer mounting secrets from `/etc/fastapi-automation/env` or injecting via your secrets manager instead of committing `.env`.

### 4. systemd service

Create `/etc/systemd/system/fastapi-automation.service`:

```ini
[Unit]
Description=FastAPI Automation API
After=network.target

[Service]
User=fastapi
Group=fastapi
WorkingDirectory=/opt/fastapi-automation
EnvironmentFile=/opt/fastapi-automation/.env
ExecStart=/home/fastapi/.local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fastapi-automation
sudo systemctl status fastapi-automation
```

### 5. nginx reverse proxy

Create `/etc/nginx/sites-available/fastapi-automation`:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/fastapi-automation /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.yourdomain.com
```

### 6. Firewall (optional)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 7. Updates

```bash
cd /opt/fastapi-automation
sudo -u fastapi git pull
sudo -u fastapi uv sync --frozen --extra all
sudo systemctl restart fastapi-automation
```

---

## Azure App Service (Linux)

Best for managed Python hosting without managing a VM.

### 1. Create resources

```bash
az group create --name rg-fastapi --location eastus
az appservice plan create --name plan-fastapi --resource-group rg-fastapi --sku B1 --is-linux
az webapp create \
  --resource-group rg-fastapi \
  --plan plan-fastapi \
  --name your-fastapi-automation \
  --runtime "PYTHON:3.12"
```

### 2. Configure startup

```bash
az webapp config set \
  --resource-group rg-fastapi \
  --name your-fastapi-automation \
  --startup-file "uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

### 3. Application settings (secrets)

Set each env var in the Azure portal under **Configuration → Application settings**, or via CLI:

```bash
az webapp config appsettings set \
  --resource-group rg-fastapi \
  --name your-fastapi-automation \
  --settings API_KEY="..." ENVIRONMENT=production LLM_PROVIDER=openai
```

Mark sensitive values as **Deployment slot setting** if using slots. For production, prefer **Azure Key Vault references**:

```
@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/API-KEY/)
```

### 4. Deploy code

Option A — GitHub Actions (recommended):

```yaml
# .github/workflows/azure-deploy.yml (example)
- uses: azure/webapps-deploy@v3
  with:
    app-name: your-fastapi-automation
    publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

Option B — ZIP deploy from local:

```bash
uv sync --extra all
zip -r deploy.zip . -x ".git/*" ".venv/*"
az webapp deployment source config-zip \
  --resource-group rg-fastapi \
  --name your-fastapi-automation \
  --src deploy.zip
```

### 5. Custom domain + HTTPS

In Azure portal: **Custom domains** → add domain → enable **Managed certificate**.

Health check path: `/health`

---

## Azure VM (alternative)

Use the **Linux VM section** above on an Azure Ubuntu VM. Additional Azure-specific steps:

1. **NSG rules**: allow inbound 443 (and 22 for SSH from your IP only)
2. **Key Vault**: store secrets in Key Vault; fetch at boot via managed identity
3. **Azure Monitor**: enable VM insights or App Service diagnostics for logs

Example Key Vault secret injection at service start (systemd `ExecStartPre`):

```bash
export API_KEY=$(az keyvault secret show --vault-name myvault --name API-KEY --query value -o tsv)
```

Requires the VM's managed identity to have `Key Vault Secrets User` role.

---

## Security checklist

- [ ] `API_KEY` is a strong random value (`openssl rand -hex 32`)
- [ ] `.env` file permissions are `600`
- [ ] Service account / app user is non-root
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Stripe webhook secret configured and signature verified
- [ ] Supabase service role key never exposed to clients
- [ ] Firewall limits SSH to known IPs
- [ ] Logs do not print secret values

---

## Docker (optional)

Not required for v1, but if you prefer containers:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --frozen --extra all
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Run with env file: `docker run --env-file .env -p 8000:8000 your-image`
