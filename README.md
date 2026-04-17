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

Required:
- `-f, --flag-format` Flag prefix to search (example: `FLAG{`, `CTF{`)

Optional:
- `-w, --wordlist` Custom wordlist file for bruteforce attacks

## Examples

```bash
ctfuck test.png -f "FLAG{"
ctfuck image.jpg -f "CTF{" -w /usr/share/wordlists/rockyou.txt
ctfuck archive.zip -f "flag{"
```

## What it does

Runs all available tools against the target file and reports every matching flag with its source:

- `strings` · `zsteg` · `exiftool` · `binwalk` · `steghide` · `outguess` · `foremost`
- Encoded flag detection (Base64, Hex, ROT13, URL, Binary, Base32, etc.)
- Steghide & ZIP bruteforce with custom wordlist support
- Extracted files saved for manual inspection when found 


## Disclaimer

Use only on authorized targets.
