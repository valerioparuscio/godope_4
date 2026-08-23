$ErrorActionPreference = "Stop"

$SERVER = "dope"
#$SERVER = "ubuntu@192.168.1.209"
$REMOTE_ROOT = "/home/ubuntu/DOPE"

Write-Host ""
Write-Host "=== DOPE DEPLOY ==="
Write-Host ""

# ------------------------------------------------------------
# 1. Build frontend
# ------------------------------------------------------------

Write-Host "1/6 - Build frontend..."

Push-Location ".\frontend"

npm run build

if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Frontend build failed"
}

Pop-Location


# ------------------------------------------------------------
# 2. Backend
# ------------------------------------------------------------

Write-Host "2/6 - Upload backend..."

scp -r ".\backend\src" "${SERVER}:${REMOTE_ROOT}/backend/"

if ($LASTEXITCODE -ne 0) {
    throw "Backend upload failed"
}

scp ".\backend\pyproject.toml" "${SERVER}:${REMOTE_ROOT}/backend/"

if ($LASTEXITCODE -ne 0) {
    throw "pyproject.toml upload failed"
}


# ------------------------------------------------------------
# 3. Data
# ------------------------------------------------------------

Write-Host "3/6 - Upload game data..."

scp -r ".\data" "${SERVER}:${REMOTE_ROOT}/"

if ($LASTEXITCODE -ne 0) {
    throw "Data upload failed"
}


# ------------------------------------------------------------
# 4. Frontend
# ------------------------------------------------------------

Write-Host "4/6 - Upload frontend..."

ssh $SERVER "rm -rf ${REMOTE_ROOT}/frontend/dist"

if ($LASTEXITCODE -ne 0) {
    throw "Could not remove old frontend"
}

scp -r ".\frontend\dist" "${SERVER}:${REMOTE_ROOT}/frontend/"

if ($LASTEXITCODE -ne 0) {
    throw "Frontend upload failed"
}


# ------------------------------------------------------------
# 5. Restart services
# ------------------------------------------------------------

Write-Host "5/6 - Restart services..."

ssh $SERVER "sudo systemctl restart dope-backend && sudo systemctl restart dope-frontend"

if ($LASTEXITCODE -ne 0) {
    throw "Service restart failed"
}


# ------------------------------------------------------------
# 6. Status
# ------------------------------------------------------------

Write-Host "6/6 - Check services..."

ssh $SERVER "systemctl is-active dope-backend && systemctl is-active dope-frontend"

Write-Host ""
Write-Host "=== DEPLOY COMPLETATO ==="
Write-Host ""
Write-Host "DOPE:"
Write-Host "http://192.168.1.209:8080"
Write-Host ""