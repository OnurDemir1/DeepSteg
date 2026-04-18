# CTFuck

Steganography automation CLI for CTF challenges.

## Installation

```bash
git clone https://github.com/OnurDemir1/CTFuck.git
cd CTFuck
sudo ./install.sh
```

This installs Python dependencies, auto-installs missing external tools (strings, exiftool, binwalk, steghide, outguess, foremost, zsteg), and registers a global `ctfuck` command.

## Usage

```bash
ctfuck <file> -f <flag_format> [options]
```

**Required:**
- `-f, --flag-format` — Flag prefix to search (e.g. `FLAG{`, `CTF{`)

**Optional:**
- `-w, --wordlist` — Custom wordlist file for bruteforce attacks (e.g. rockyou.txt)
- `-b, --auto-brute` — Auto brute-force steghide & outguess using the built-in ~150-password wordlist (or `-w` if provided)
- `-d, --depth` — Maximum recursion depth for nested file analysis (default: `3`)

## Examples

```bash
# Basic scan
ctfuck test.png -f "FLAG{"

# With custom wordlist
ctfuck image.jpg -f "CTF{" -w /usr/share/wordlists/rockyou.txt

# Auto brute-force with built-in wordlist
ctfuck image.jpg -f "CTF{" -b

# Full attack: custom wordlist + auto-brute + deeper recursion
ctfuck image.jpg -f "CTF{" -w /usr/share/wordlists/rockyou.txt -b -d 5

# Archive
ctfuck archive.zip -f "flag{"
```

## What it does

Runs all available tools against the target file and reports every matching flag with its source:

- `strings` · `zsteg` · `exiftool` · `binwalk` · `steghide` · `outguess` · `foremost`
- Encoded flag detection (Base64, Hex, ROT13, URL, Binary, Base32, Octal, ASCII, etc.)
- **Recursive extraction**: files extracted by binwalk / foremost / steghide / outguess are automatically re-analyzed with all tools (nested stego support, configurable depth)
- **Auto brute-force** (`-b`): tries ~150 common CTF/stego passwords against steghide and outguess with a Rich progress bar
- Steghide & ZIP bruteforce with custom wordlist support via `-w`
- Duplicate detection via SHA-256 prevents infinite loops in circular archives
- Extracted files saved to `ctfuck_output_<stem>/` for manual inspection

## Disclaimer

Use only on authorized targets.
