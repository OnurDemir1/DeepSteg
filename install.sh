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

info "Checking for missing external tools..."
MISSING_TOOLS=()
for tool in strings exiftool binwalk steghide outguess foremost zsteg; do
  if ! command -v "$tool" &>/dev/null; then
    MISSING_TOOLS+=("$tool")
  fi
done

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
  warn "Missing tools: ${MISSING_TOOLS[*]}"
  info "Attempting to install missing tools..."
  
  if command -v apt &>/dev/null; then
    apt update -qq
    for tool in "${MISSING_TOOLS[@]}"; do
      case "$tool" in
        strings) apt install -y binutils ;;
        exiftool) apt install -y libimage-exiftool-perl ;;
        binwalk) apt install -y binwalk ;;
        steghide) apt install -y steghide ;;
        outguess) apt install -y outguess 2>/dev/null || warn "outguess not available in repos, skipping" ;;
        foremost) apt install -y foremost 2>/dev/null || warn "foremost not available in repos, skipping" ;;
        zsteg) 
          apt install -y ruby ruby-dev 2>/dev/null || true
          gem install zsteg 2>/dev/null || true
          ;;
      esac
    done
  elif command -v pacman &>/dev/null; then
    for tool in "${MISSING_TOOLS[@]}"; do
      case "$tool" in
        strings) pacman -S --noconfirm --needed binutils ;;
        exiftool) pacman -S --noconfirm --needed perl-image-exiftool ;;
        binwalk) pacman -S --noconfirm --needed binwalk ;;
        steghide) pacman -S --noconfirm --needed steghide ;;
        outguess) pacman -S --noconfirm --needed outguess ;;
        foremost) pacman -S --noconfirm --needed foremost ;;
        zsteg) 
          pacman -S --noconfirm --needed ruby
          gem install zsteg 2>/dev/null || true
          ;;
      esac
    done
  else
    warn "Unknown package manager. Please install missing tools manually."
  fi
else
  success "All external tools are already installed"
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

info "Installing ctfuck-smart.sh..."
cp "$ROOT_DIR"/ctfuck-smart.sh /opt/ctfuck/
chmod +x /opt/ctfuck/ctfuck-smart.sh

# Global shortcut for smart scanner
cat > /usr/local/bin/ctfuck-smart << 'EOF'
#!/usr/bin/env bash
exec bash /opt/ctfuck/ctfuck-smart.sh "$@"
EOF
chmod +x /usr/local/bin/ctfuck-smart

success "Installation complete!"
info "Commands:"
info "  ctfuck <file> -f FLAG{                  → Manuel tarama"
info "  ctfuck <file> -f FLAG{ -b               → + brute-force"
info "  ctfuck <file> -f FLAG{ -b -d 5          → + derin analiz"
info "  ctfuck-smart <file>                      → Akıllı otomatik tarama (25 format, 4 seviye)"
info "  ctfuck-smart <file> -f CTF{              → Belirli format ile akıllı tarama"
info "  ctfuck-smart <file> -w rockyou.txt       → Custom wordlist ile akıllı tarama"
