#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"
PIP_BIN="pip"
REQ_FILE="$ROOT_DIR/requirements.txt"
BIN_TARGET="/usr/local/bin/ctfuck"

info()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
success(){ printf "\033[1;32m[SUCCESS]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
error() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; }

if [[ "$EUID" -ne 0 ]]; then
  warn "Running with root privileges is recommended (sudo ./install.sh)"
fi

info "Installing Python dependencies (pip --break-system-packages)..."
$PIP_BIN install --break-system-packages -r "$REQ_FILE"

info "Creating /usr/local/bin/ctfuck script..."
cat > "$BIN_TARGET" <<'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="/opt/ctfuck"
exec python3 "$SCRIPT_DIR/ctfuck.py" "$@"
EOF
chmod +x "$BIN_TARGET"

info "Copying files to /opt/ctfuck..."
mkdir -p /opt/ctfuck
cp "$ROOT_DIR"/ctfuck.py /opt/ctfuck/
cp "$ROOT_DIR"/requirements.txt /opt/ctfuck/ 2>/dev/null || true

success "Installation complete: 'ctfuck' command ready"
info "Usage: ctfuck <file> -f FLAG{ [-o output_dir] [--skip-fast] [--skip-deep]"
