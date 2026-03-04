# CTFuck

Steganography automation CLI for CTF challenges.

## Installation 

```bash
git clone https://github.com/OnurDemir1/CTFuck.git
cd CTFuck
sudo ./install.sh
```

This is the only supported install flow. It installs Python dependencies and registers a global `ctfuck` command.

## Usage

```bash
ctfuck <file> -f <flag_format> [options]
```

Required:
- `-f, --flag-format` Flag prefix to search (example: `FLAG{`, `CTF{`)

Optional:
- `-o, --output-dir` Custom output directory
- `--skip-fast` Skip fast scan phase
- `--skip-deep` Skip deep analysis phase

## Examples

```bash
ctfuck test.png -f "FLAG{"
ctfuck image.jpg -f "CTF{" -o ./output
ctfuck challenge.png -f "flag{" --skip-fast
```

## What it does

1. Fast scan: `strings` and `zsteg`
2. Deep analysis: `exiftool`, `binwalk`, `zsteg`, `steghide`, `outguess`, `foremost`
3. Scans all generated files for matching flags

Output is saved under `ctfuck_output_<filename>/` unless `-o` is provided.

## Notes

- Built for Linux environments.
- If some external tools are missing, CTFuck skips them and continues.

## Disclaimer

Use only on authorized targets.
