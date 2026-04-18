#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════╗
# ║         CTFuck Smart Auto Scanner                ║
# ║  Akıllı, sıralı, flag formatı otomatik tespit   ║
# ╚══════════════════════════════════════════════════╝
#
# Kullanım:
#   ./ctfuck-smart.sh <dosya>               → Dahili 25 formatı dene
#   ./ctfuck-smart.sh <dosya> -f "CTF{"     → Sadece bu formatı dene
#   ./ctfuck-smart.sh <dosya> -w liste.txt  → Custom wordlist ekle

set -euo pipefail

# ── Renkler ───────────────────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'
R='\033[0;31m'; B='\033[1m';    N='\033[0m'

# ── Dahili flag formatları (25 adet) ──────────────────────────────────────────
DEFAULT_FLAGS=(
    "SiberVatan{"   # TR ulusal CTF
    "CTF{"          # Generic
    "FLAG{"
    "flag{"
    "ctf{"
    "picoCTF{"      # picoCTF
    "DUCTF{"        # DownUnderCTF
    "HTB{"          # HackTheBox
    "THM{"          # TryHackMe
    "CSAW{"         # CSAW CTF
    "DarkCTF{"
    "RITSEC{"
    "TUCTF{"
    "nactf{"
    "zer0pts{"
    "BCACTF{"
    "DCTF{"         # DragonCTF
    "wectf{"
    "zh3r0{"
    "justCTF{"
    "X-MAS{"
    "cybrics{"
    "SquareCTF{"
    "WPICTF{"
    "BYUCTF{"
)

# ── Argüman ayrıştırma ────────────────────────────────────────────────────────
FILE=""
CUSTOM_FLAG=""
EXTRA_WORDLIST=""

usage() {
    echo -e "Kullanım: $0 <dosya> [-f flag_format] [-w wordlist]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--flag-format) CUSTOM_FLAG="$2"; shift 2 ;;
        -w|--wordlist)    EXTRA_WORDLIST="$2"; shift 2 ;;
        -h|--help)        usage ;;
        *)
            if [ -z "$FILE" ]; then FILE="$1"; shift
            else echo "Bilinmeyen argüman: $1"; usage; fi ;;
    esac
done

[ -z "$FILE" ] && usage
[ ! -f "$FILE" ] && echo -e "${R}Dosya bulunamadı: $FILE${N}" && exit 1

# Kullanılacak format listesi
if [ -n "$CUSTOM_FLAG" ]; then
    ACTIVE_FLAGS=("$CUSTOM_FLAG")
else
    ACTIVE_FLAGS=("${DEFAULT_FLAGS[@]}")
fi

# Rockyou yolu
ROCKYOU="${EXTRA_WORDLIST:-/usr/share/wordlists/rockyou.txt}"

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${C}${B}"
echo "╔══════════════════════════════════════════════════╗"
echo "║         CTFuck Smart Auto Scanner                ║"
echo "╚══════════════════════════════════════════════════╝${N}"
echo -e "Hedef  : ${B}$FILE${N}"
if [ -n "$CUSTOM_FLAG" ]; then
    echo -e "Format : ${B}$CUSTOM_FLAG${N}"
else
    echo -e "Formatlar: ${B}${#ACTIVE_FLAGS[@]} dahili format${N}"
fi
echo ""

# ── Global durum ──────────────────────────────────────────────────────────────
FOUND_OUTPUT=""
CONFIRMED_FMT=""   # Flag bulununca sadece bu formatla devam et

# ── Flag bulundu → göster ve sor ─────────────────────────────────────────────
on_found() {
    local output="$1"
    local fmt="$2"

    echo ""
    echo -e "${G}${B}┌─────────────────────────────────────────┐${N}"
    echo -e "${G}${B}│  🎯  FLAG BULUNDU!                       │${N}"
    echo -e "${G}${B}└─────────────────────────────────────────┘${N}"
    echo -e "${G}$(echo "$output" | grep -A 10 "🎯 Flags" || true)${N}"
    echo ""
    echo -e "${Y}${B}Kalan işlemlere devam etmek istiyor musun? [y/N]${N} "
    read -r ans < /dev/tty
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        CONFIRMED_FMT="$fmt"   # sonraki seviyelerde sadece bu formatı kullan
        ACTIVE_FLAGS=("$fmt")
        return 0   # devam
    fi
    echo -e "${G}İyi CTF'ler! 🚀${N}"
    exit 0
}

# ── Tek bir ctfuck çağrısı ────────────────────────────────────────────────────
# stdin'e "n" gönderiyoruz → "raw çıktı göster?" sorusunu otomatik geçer
run_ctfuck() {
    local fmt="$1"; shift
    local args=("$@")
    echo "$fmt" | ctfuck "$FILE" -f "$fmt" "${args[@]}" <<< "n" 2>&1 || true
}

# ── Seviye çalıştırıcı ────────────────────────────────────────────────────────
run_level() {
    local lnum="$1"
    local ldesc="$2"
    shift 2
    local args=("$@")

    echo -e "${C}${B}━━━ Seviye $lnum: $ldesc ━━━${N}"

    for fmt in "${ACTIVE_FLAGS[@]}"; do
        echo -e "  ${Y}▶ $fmt${N}"
        OUT=$(run_ctfuck "$fmt" "${args[@]}")
        if echo "$OUT" | grep -q "🎯 Flags"; then
            on_found "$OUT" "$fmt"
            return 0   # kullanıcı devam dedi → sonraki seviyeye geç
        fi
    done

    echo -e "  ${R}→ Bu seviyede bulunamadı.${N}"
    echo ""
    return 1
}

# ══════════════════════════════════════════════════════════════════════════════
# AŞAMA 0 — Hızlı ön kontrol: strings ile format tespiti
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${C}${B}[ Ön Kontrol ] strings ile hızlı format tespiti...${N}"

STRINGS_OUT=$(strings "$FILE" 2>/dev/null || true)
PRE_FMT=""

for fmt in "${ACTIVE_FLAGS[@]}"; do
    # Sabit string araması, büyük/küçük harf duyarsız
    if echo "$STRINGS_OUT" | grep -qiF "$fmt"; then
        PRE_FMT="$fmt"
        break
    fi
done

if [ -n "$PRE_FMT" ]; then
    echo -e "${G}  ✓ strings'de doğrudan tespit edildi: ${B}$PRE_FMT${N}"
    HIT=$(echo "$STRINGS_OUT" | grep -iF "$PRE_FMT" | head -5)
    echo -e "${G}$HIT${N}"
    echo ""
    echo -e "${Y}${B}Kalan işlemlere devam etmek istiyor musun? [y/N]${N} "
    read -r ans < /dev/tty
    if [[ ! "$ans" =~ ^[Yy]$ ]]; then
        echo -e "${G}İyi CTF'ler! 🚀${N}"; exit 0
    fi
    # Sonraki seviyelerde sadece tespit edilen formatı dene
    ACTIVE_FLAGS=("$PRE_FMT")
    CONFIRMED_FMT="$PRE_FMT"
else
    echo -e "${Y}  ✗ Yüzeysel kontrol negatif → tam taramaya geçiliyor...${N}"
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# AŞAMA 1 — Tam araç taraması (strings, zsteg, exiftool, binwalk, foremost)
# ══════════════════════════════════════════════════════════════════════════════
run_level 1 "Tam Araç Taraması" || true

# ══════════════════════════════════════════════════════════════════════════════
# AŞAMA 2 — Brute-force (dahili ~150 şifre)
# ══════════════════════════════════════════════════════════════════════════════
run_level 2 "Brute-Force — dahili 150 şifre (steghide + outguess + zip)" -b || true

# ══════════════════════════════════════════════════════════════════════════════
# AŞAMA 3 — Derin özyinelemeli analiz + brute
# ══════════════════════════════════════════════════════════════════════════════
run_level 3 "Derin Analiz — brute + depth 5 (iç içe dosyalar)" -b -d 5 || true

# ══════════════════════════════════════════════════════════════════════════════
# AŞAMA 4 — rockyou (varsa)
# ══════════════════════════════════════════════════════════════════════════════
if [ -f "$ROCKYOU" ]; then
    run_level 4 "Rockyou Brute-Force — depth 5 + rockyou.txt" -b -d 5 -w "$ROCKYOU" || true
else
    echo -e "${Y}⚠  Seviye 4 atlandı: rockyou.txt bulunamadı ($ROCKYOU)${N}"
    echo -e "   Kendi listenizi ekleyin: $0 $FILE -w /yol/liste.txt"
    echo ""
fi

# ── Sonuç ─────────────────────────────────────────────────────────────────────
echo -e "${R}${B}═══════════════════════════════════════════════${N}"
echo -e "${R}${B}  ❌  Tüm seviyeler tamamlandı, flag bulunamadı.${N}"
echo -e "${R}${B}═══════════════════════════════════════════════${N}"
echo ""
echo "Manuel analiz önerileri:"
echo "  • StegOnline / Aperi'Solve / stegsolve"
echo "  • pngcheck '$FILE'"
echo "  • zsteg '$FILE' -a | grep -v '\\.\\.'   (tüm kanallar)"
echo "  • steghide extract -sf '$FILE'           (şifre biliyorsan)"
echo "  • hexdump -C '$FILE' | head -100"
