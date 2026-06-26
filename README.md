# DeepSteg

Steganography automation CLI for CTF challenges.

## Installation

```bash
git clone https://github.com/OnurDemir1/DeepSteg.git
cd DeepSteg
sudo ./install.sh
```

This scripts installs Python dependencies, missing tools (strings, exiftool, binwalk, steghide, outguess, foremost, zsteg), and adds a global `deepsteg` command.

## Usage

```bash
deepsteg <file>
```

By default, DeepSteg uses its **Smart Auto Scan** mode. It searches for 25 common CTF flag formats (like `SiberVatan{`, `CTF{`, `FLAG{`) simultaneously and runs in an escalating, interactive loop:

1. **Fast Analysis:** Runs lightweight tools (`strings`, `zsteg`, `exiftool`, `binwalk`). If a flag is found, it pauses and asks if you want to continue deeper.
2. **Auto Brute-Force:** Runs `steghide` and `outguess` using a built-in list of ~150 common stego passwords.
3. **Deep Recursion:** Re-analyzes extracted nested files automatically (default depth 3).

### Options

If you want to customize the behavior:

```bash
deepsteg <file> -f "CUSTOM{" -w rockyou.txt -d 5
```

- `-f, --flag-format` — Search for a specific flag prefix only
- `-w, --wordlist` — Use a custom wordlist file for bruteforce attacks
- `-d, --depth` — Max recursion depth for nested file analysis (default 3, hard-limit 10)
- `-b, --auto-brute` — Explicitly enable brute-force (Already active in smart mode by default!)

## What it does

Runs and orchestrates standard tools against the target.
- Tools: `strings`, `zsteg`, `exiftool`, `binwalk`, `steghide`, `outguess`, `foremost`.
- Extracts files recursively into `deepsteg_output_<file>/` and re-analyzes them (nested stego support).
- Defends against infinite loops (via SHA-256 caching) and zip-bombs.

## Disclaimer

Use only on authorized targets.
