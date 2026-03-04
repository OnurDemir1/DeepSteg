# CTFuck

**Steganography Automation Tool for CTF Challenges**

A Python-based CLI tool that automates steganography analysis for CTF competitions. Combines multiple forensics tools into a streamlined workflow with intelligent flag detection.

## Features

### ⚡ Fast Scan
- Quick flag detection using `strings` and `zsteg`
- Instant results with option to continue deep analysis

### 🔍 Deep Analysis
- **exiftool** - Metadata extraction
- **binwalk** - Embedded file detection and extraction
- **steghide** - Password-less extraction attempts
- **foremost** - File carving
- **zsteg** - Comprehensive LSB analysis

### 📁 Organized Output
- All results saved to `ctfuck_output_<filename>/`
- Automatic flag scanning across all extracted files

### 🎨 Modern UI
- Rich terminal interface with colored output
- Progress indicators and formatted tables

### 🛡️ Robust
- Automatic tool availability checking
- Graceful degradation when tools are missing
- Timeout protection and error handling

## Installation

### Quick Install (Linux)
```bash
sudo ./install.sh
```

This installs dependencies and creates a global `ctfuck` command.

### Clone and Manual Setup
```bash
git clone https://github.com/OnurDemir1/CTFuck.git
cd CTFuck
pip install -r requirements.txt
chmod +x ctfuck.py
```

### Manual Install
```bash
pip install -r requirements.txt
chmod +x ctfuck.py
```

### System Tools

For full functionality, install these tools:

**Ubuntu/Debian:**
```bash
sudo apt install -y binutils exiftool binwalk steghide foremost ruby
sudo gem install zsteg
```

**Arch Linux:**
```bash
sudo pacman -S binutils perl-image-exiftool binwalk steghide foremost ruby
sudo gem install zsteg
```

**Note:** CTFuck works with partial tool availability, using only what's installed.

## Usage

### Basic Usage
```bash
ctfuck image.png -f "FLAG{"
ctfuck image.png -f "CTF{" -o /tmp/output
```

**Note:** Flag format (`-f`) is required.

### Options
```bash
ctfuck <file> -f <flag_format> [options]

Required:
  -f, --flag-format    Flag format to search (e.g., "FLAG{", "CTF{")

Optional:
  -o, --output-dir     Custom output directory
  --skip-fast          Skip fast scan phase
  --skip-deep          Skip deep analysis phase
```

## Workflow

1. **Fast Scan** - Quick flag detection with `strings` and `zsteg`
2. **Deep Analysis** (if no flags found or user continues):
   - ExifTool metadata extraction
   - Binwalk embedded file extraction
   - Steghide password-less extraction
   - Foremost file carving
   - Zsteg comprehensive analysis
3. **Flag Scanning** - All output files scanned for flag patterns

## Output Structure

```
ctfuck_output_<filename>/
├── exiftool_output.txt
├── zsteg_deep_output.txt
├── steghide_extracted_<file>.txt
├── binwalk_extracted/
│   └── [extracted files]
└── foremost_carved/
    ├── audit.txt
    ├── jpg/
    ├── png/
    └── [other file types]
```

## Examples

### PNG Analysis
```bash
ctfuck stego.png -f "FLAG{"
```

### JPEG with Custom Output
```bash
ctfuck photo.jpg -f "CTF{" -o ./results
```

### Skip Fast Scan
```bash
ctfuck image.png -f "flag{" --skip-fast
```

## Troubleshooting

**Missing tools:** Install using commands above. CTFuck continues with available tools.

**Permission denied:**
```bash
chmod +x ctfuck.py
```

**Zsteg issues:**
```bash
sudo gem update --system
sudo gem install zsteg
```

## Technical Details

- **Regex-based flag detection** with customizable patterns
- **Duplicate filtering** for clean results
- **Automatic scanning** of all output files
- **Timeout protection** (60s per tool)
- **Graceful error handling** with detailed logging

## License

Developed for educational purposes and CTF competitions. Use responsibly.

## Contributing

Pull requests welcome!

## Disclaimer

For authorized use only. Do not use on systems or files without permission.

---

**CTFuck** - Steganography automation for CTF 🚀
