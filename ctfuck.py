#!/usr/bin/env python3

import argparse
import subprocess
import re
import shutil
import base64
import binascii
import tempfile
import os
import math
import urllib.parse
import codecs
import zipfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich import box

console = Console()

BANNER = "CTFuck - Steganography Automation Tool"

class ToolChecker:
    REQUIRED_TOOLS = {
        'strings': 'binutils',
        'zsteg': 'zsteg (gem install zsteg)',
        'exiftool': 'libimage-exiftool-perl',
        'binwalk': 'binwalk',
        'steghide': 'steghide',
        'outguess': 'outguess',
        'foremost': 'foremost'
    }
    
    @staticmethod
    def check_tool(tool_name):
        return shutil.which(tool_name) is not None
    
    @classmethod
    def check_all_tools(cls):
        status = {}
        for tool, package in cls.REQUIRED_TOOLS.items():
            status[tool] = cls.check_tool(tool)
        return status

class CTFuck:
    def __init__(self, file_path, flag_format, wordlist=None, skip_fast=False, skip_deep=False):
        self.file_path = Path(file_path)
        self.flag_format = flag_format.strip()
        self.flag_patterns = self._build_flag_patterns(self.flag_format)
        self.found_flags = []
        self.interesting_strings = []
        self.suspicious_patterns = []
        self.metadata_findings = []
        self.tool_status = ToolChecker.check_all_tools()
        self.skip_fast = skip_fast
        self.skip_deep = skip_deep
        self.wordlist = self._load_wordlist(wordlist)
        
        if not self.file_path.exists():
            console.print(f"[bold red]✗ Error:[/bold red] File not found: {file_path}")
            exit(1)

    def _build_flag_patterns(self, flag_format):
        patterns = []

        escaped_prefix = re.escape(flag_format)
        patterns.append(re.compile(rf"{escaped_prefix}[^\r\n\t ]{{0,300}}}}"))
        patterns.append(re.compile(rf"{escaped_prefix}.{{0,300}}?}}", re.DOTALL))

        regex_like_tokens = (".*", ".+", "[", "(", "\\d", "\\w", "\\s", "|")
        if any(token in flag_format for token in regex_like_tokens):
            try:
                patterns.append(re.compile(flag_format))
            except re.error:
                pass

        return patterns
    
    def _load_wordlist(self, wordlist_path):
        """Load wordlist from file or use default common passwords"""
        default_passwords = [
            '', 'password', '123456', '12345678', 'qwerty', 'abc123',
            'admin', 'root', 'user', 'test', 'guest', 'pass',
            'flag', 'ctf', 'challenge', 'steghide', 'steg',
            'hidden', 'secret', 'key', 'password123', 'admin123',
            '1234', '12345', '123456789', 'password1', 'letmein',
            'welcome', 'monkey', 'dragon', 'master', 'sunshine'
        ]
        
        if wordlist_path:
            try:
                with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                    passwords = [line.strip() for line in f if line.strip()]
                console.print(f"[green]✓ Loaded {len(passwords)} passwords from wordlist[/green]")
                return passwords
            except Exception as e:
                console.print(f"[yellow]⚠ Could not load wordlist: {e}. Using default passwords.[/yellow]")
                return default_passwords
        
        return default_passwords
    
    def show_banner(self):
        console.print(f"\n[bold cyan]{BANNER}[/bold cyan]")
        console.print(f"[dim]Target:[/dim] {self.file_path} | [dim]Flag:[/dim] {self.flag_format}\n")
    
    def show_tool_status(self):
        available = [tool for tool, status in self.tool_status.items() if status]
        missing = [tool for tool, status in self.tool_status.items() if not status]
        
        if available:
            console.print(f"[dim]Tools:[/dim] [green]{', '.join(available)}[/green]")
        if missing:
            console.print(f"[dim]Missing:[/dim] [red]{', '.join(missing)}[/red]")
        console.print()
    
    def run_command(self, cmd, description, shell=False, silent=False):
        try:
            if not silent:
                console.print(f"[dim]→ {description}[/dim]")
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                errors='ignore',
                timeout=60
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            if not silent:
                console.print(f"[red]✗ Timeout: {description}[/red]")
            return "", "Timeout", -1
        except Exception as e:
            if not silent:
                console.print(f"[red]✗ Error: {str(e)}[/red]")
            return "", str(e), -1
    
    def search_flags(self, text, source="unknown"):
        found = []
        for pattern in self.flag_patterns:
            for match in pattern.findall(text):
                if isinstance(match, tuple):
                    match = "".join(match)
                cleaned = re.sub(r"[\r\n\t]+", "", match).strip()
                if cleaned:
                    found.append((cleaned, source))
        return found

    def calculate_entropy(self, data: bytes):
        if not data:
            return 0
        
        # Count byte frequencies efficiently
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        entropy = 0
        data_len = len(data)
        for count in byte_counts:
            if count > 0:
                p_x = count / data_len
                entropy += - p_x * math.log(p_x, 2)
        return entropy

    def find_encoded_flags(self, text, source="unknown"):
        found = []
        interesting = []
        
        # 1. Base64 Detection (multiple patterns)
        b64_patterns = [
            re.compile(r'(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?'),
            re.compile(r'(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)')  # Shorter base64
        ]
        
        for pattern in b64_patterns:
            for b64_match in pattern.findall(text):
                if len(b64_match) < 8:  # Too short
                    continue
                try:
                    decoded = base64.b64decode(b64_match).decode('utf-8', errors='ignore')
                    if decoded.strip():
                        flags = self.search_flags(decoded, source)
                        if flags:
                            found.extend(flags)
                        # Recursive decode - maybe it's double encoded
                        recursive_flags, recursive_interesting = self.find_encoded_flags(decoded, source)
                        found.extend(recursive_flags)
                        interesting.extend(recursive_interesting)
                        
                        # Check for interesting content
                        self._check_interesting_content(decoded, f"[Base64] {b64_match[:50]}...", source, interesting)
                except Exception:
                    pass
        
        # 2. Hex Detection
        hex_patterns = [
            re.compile(r'\b(?:[0-9a-fA-F]{2}){8,}\b'),  # Standard hex
            re.compile(r'(?:0x[0-9a-fA-F]{2}\s*){4,}'),  # 0x prefixed
            re.compile(r'(?:[0-9a-fA-F]{2}\s+){4,}')     # Space separated
        ]
        
        for pattern in hex_patterns:
            for hex_match in pattern.findall(text):
                cleaned_hex = re.sub(r'[^0-9a-fA-F]', '', hex_match)
                if len(cleaned_hex) < 8 or len(cleaned_hex) % 2 != 0:
                    continue
                try:
                    decoded = binascii.unhexlify(cleaned_hex).decode('utf-8', errors='ignore')
                    if decoded.strip():
                        flags = self.search_flags(decoded, source)
                        if flags:
                            found.extend(flags)
                        self._check_interesting_content(decoded, f"[Hex] {hex_match[:50]}...", source, interesting)
                except Exception:
                    pass
        
        # 3. URL Encoding
        url_pattern = re.compile(r'(?:%[0-9a-fA-F]{2}){3,}')
        for url_match in url_pattern.findall(text):
            try:
                decoded = urllib.parse.unquote(url_match)
                if decoded != url_match and decoded.strip():
                    flags = self.search_flags(decoded, source)
                    if flags:
                        found.extend(flags)
                    self._check_interesting_content(decoded, f"[URL] {url_match[:50]}...", source, interesting)
            except Exception:
                pass
        
        # 4. ROT13
        try:
            rot13_decoded = codecs.decode(text, 'rot_13')
            if rot13_decoded != text:
                flags = self.search_flags(rot13_decoded, source)
                if flags:
                    for flag in flags:
                        found.append((flag[0], f"{source} (ROT13)"))
        except Exception:
            pass
        
        # 5. Binary (01 sequences)
        binary_pattern = re.compile(r'\b[01]{8,}\b')
        for binary_match in binary_pattern.findall(text):
            if len(binary_match) % 8 != 0:
                continue
            try:
                decoded = ''.join(chr(int(binary_match[i:i+8], 2)) for i in range(0, len(binary_match), 8))
                if decoded.strip():
                    flags = self.search_flags(decoded, source)
                    if flags:
                        found.extend(flags)
                    self._check_interesting_content(decoded, f"[Binary] {binary_match[:50]}...", source, interesting)
            except Exception:
                pass
        
        # 6. Octal
        octal_pattern = re.compile(r'(?:\\[0-7]{3}){3,}')
        for octal_match in octal_pattern.findall(text):
            try:
                decoded = codecs.decode(octal_match, 'unicode_escape')
                if decoded.strip():
                    flags = self.search_flags(decoded, source)
                    if flags:
                        found.extend(flags)
                    self._check_interesting_content(decoded, f"[Octal] {octal_match[:50]}...", source, interesting)
            except Exception:
                pass
        
        # 7. ASCII decimal codes (space or comma separated)
        ascii_pattern = re.compile(r'\b(?:\d{2,3}[,\s]+){4,}\d{2,3}\b')
        for ascii_match in ascii_pattern.findall(text):
            try:
                numbers = re.findall(r'\d+', ascii_match)
                decoded = ''.join(chr(int(n)) for n in numbers if 0 <= int(n) <= 127)
                if decoded.strip() and len(decoded) > 3:
                    flags = self.search_flags(decoded, source)
                    if flags:
                        found.extend(flags)
                    self._check_interesting_content(decoded, f"[ASCII] {ascii_match[:50]}...", source, interesting)
            except Exception:
                pass
        
        # 8. Base32
        base32_pattern = re.compile(r'\b[A-Z2-7]{8,}={0,6}\b')
        for b32_match in base32_pattern.findall(text):
            if len(b32_match) < 8:
                continue
            try:
                decoded = base64.b32decode(b32_match).decode('utf-8', errors='ignore')
                if decoded.strip():
                    flags = self.search_flags(decoded, source)
                    if flags:
                        found.extend(flags)
                    self._check_interesting_content(decoded, f"[Base32] {b32_match[:50]}...", source, interesting)
            except Exception:
                pass
        
        # 9. Reversed strings (look for common patterns reversed)
        reversed_text = text[::-1]
        reversed_flags = self.search_flags(reversed_text, source)
        if reversed_flags:
            for flag in reversed_flags:
                found.append((flag[0], f"{source} (Reversed)"))
        
        return found, interesting
    
    def _check_interesting_content(self, decoded, encoding_info, source, interesting_list):
        """Enhanced interesting content detection with multiple categories"""
        if not decoded or len(decoded) < 3:
            return
        
        decoded_lower = decoded.lower()
        is_printable = all(32 <= ord(c) < 127 or c in '\n\r\t' for c in decoded)
        
        if not is_printable:
            return
        
        # Category 1: CTF Keywords
        ctf_keywords = ['flag', 'ctf', 'challenge', 'solve', 'answer']
        if any(kw in decoded_lower for kw in ctf_keywords):
            interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [CTF Keyword]"))
            return
        
        # Category 2: Credentials/Secrets
        secret_keywords = ['password', 'passwd', 'pwd', 'secret', 'key', 'token', 'api', 'auth']
        if any(kw in decoded_lower for kw in secret_keywords):
            interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [Credentials]"))
            return
        
        # Category 3: Admin/Access
        admin_keywords = ['admin', 'root', 'user', 'login', 'username']
        if any(kw in decoded_lower for kw in admin_keywords):
            interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [Access Info]"))
            return
        
        # Category 4: URLs and Paths
        if any(pattern in decoded_lower for pattern in ['http://', 'https://', 'ftp://', '://']):
            interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [URL]"))
            return
        
        if decoded.startswith('/') or ':\\\\' in decoded or re.search(r'[A-Z]:\\\\', decoded):
            interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [File Path]"))
            return
        
        # Category 5: Code/Commands
        code_patterns = ['import ', 'function ', 'def ', 'class ', 'echo ', 'cat ', 'ls ', 'grep ']
        if any(pattern in decoded_lower for pattern in code_patterns):
            interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [Code/Command]"))
            return
        
        # Category 6: Long readable strings (might be hidden messages)
        if len(decoded) > 20 and decoded.count(' ') > 2:
            words = decoded.split()
            if len(words) > 3:
                interesting_list.append((f"{encoding_info} -> {decoded[:150]}", f"{source} [Long Text]"))
    
    def _detect_suspicious_patterns(self, text, source):
        """Detect suspicious patterns that might indicate hidden data"""
        # Detect repeated patterns
        repeated_pattern = re.compile(r'(\b\w{4,}\b)(?:\s+\1){2,}')
        for match in repeated_pattern.finditer(text):
            self.suspicious_patterns.append((f"Repeated word: '{match.group(1)}'", source))
        
        # Detect unusual character frequencies
        if len(text) > 100:
            char_freq = {}
            for char in text:
                if char.isalnum():
                    char_freq[char] = char_freq.get(char, 0) + 1
            
            # Check if any character appears more than 30% of the time
            total_alnum = sum(char_freq.values())
            if total_alnum > 0:
                for char, count in char_freq.items():
                    if count / total_alnum > 0.3:
                        self.suspicious_patterns.append((f"High frequency character: '{char}' ({count/total_alnum*100:.1f}%)", source))
                        break
        
        # Detect potential steganography markers
        stego_markers = ['BEGIN', 'END', 'HIDDEN', 'EMBEDDED', 'STEALTH', 'COVERT']
        for marker in stego_markers:
            if marker in text.upper():
                context_start = max(0, text.upper().find(marker) - 20)
                context_end = min(len(text), text.upper().find(marker) + len(marker) + 20)
                context = text[context_start:context_end]
                self.suspicious_patterns.append((f"Steganography marker '{marker}': {context}", source))

    def _scan_extracted_files(self, extract_dir, tool_name, max_depth=3, current_depth=0):
        flags_found = []
        has_strings = self.tool_status.get('strings', False)
        
        if current_depth >= max_depth:
            return flags_found
        
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_source = f"{tool_name} -> {os.path.relpath(file_path, extract_dir)}"
                
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        continue
                    
                    # Skip very large files (> 50MB) to avoid memory issues
                    if file_size > 50 * 1024 * 1024:
                        continue
                    
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                    
                    # Check if it's a nested archive/image that binwalk can extract
                    file_ext = os.path.splitext(file_path)[1].lower()
                    nested_extractable = file_ext in ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.png', '.jpg', '.jpeg', '.bmp', '.gif']
                    
                    if nested_extractable and self.tool_status.get('binwalk', False) and current_depth < max_depth - 1:
                        # Try to extract nested files
                        with tempfile.TemporaryDirectory() as nested_temp:
                            try:
                                nested_stdout, nested_stderr, nested_code = self.run_command(
                                    ['binwalk', '-e', '-C', nested_temp, file_path],
                                    f"Extracting nested file: {file}"
                                )
                                
                                # Scan the nested extraction
                                nested_flags = self._scan_extracted_files(nested_temp, f"{tool_name}/{file}", max_depth, current_depth + 1)
                                if nested_flags:
                                    flags_found.extend(nested_flags)
                            except Exception:
                                pass
                    
                    # Scan file content with strings or direct read
                    if has_strings:
                        try:
                            stdout, stderr, code = self.run_command(
                                ['strings', str(file_path)],
                                f"Scanning: {os.path.basename(file_path)}"
                            )
                            flags = self.search_flags_from_outputs(stdout, stderr, file_source)
                            if flags:
                                flags_found.extend(flags)
                        except Exception:
                            pass
                    
                    # Always try direct content read for better encoding detection
                    try:
                        content = raw_data.decode('utf-8', errors='ignore')
                        if content.strip():
                            # Direct flag search
                            flags = self.search_flags(content, file_source)
                            if flags:
                                flags_found.extend(flags)
                            
                            # Encoded flag search
                            encoded_flags, interesting = self.find_encoded_flags(content, file_source)
                            if encoded_flags:
                                flags_found.extend(encoded_flags)
                            if interesting:
                                self.interesting_strings.extend(interesting)
                    except Exception:
                        pass
                    
                except Exception:
                    pass
        
        return flags_found

    def _extract_metadata_info(self, metadata_output, source):
        """Extract interesting information from metadata"""
        interesting_fields = [
            'comment', 'description', 'author', 'creator', 'software', 
            'user comment', 'artist', 'copyright', 'keywords', 'subject'
        ]
        
        for line in metadata_output.split('\n'):
            line_lower = line.lower()
            for field in interesting_fields:
                if field in line_lower and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        value = parts[1].strip()
                        if value and len(value) > 3:
                            self.metadata_findings.append((f"{parts[0].strip()}: {value}", source))
    
    def search_flags_from_outputs(self, stdout, stderr, source="unknown"):
        combined = f"{stdout}\n{stderr}"
        flags = self.search_flags(combined, source)
        
        encoded_flags, interesting = self.find_encoded_flags(combined, source)
        flags.extend(encoded_flags)
        
        if interesting:
            self.interesting_strings.extend(interesting)
            
        return flags
    
    def fast_scan(self):
        console.print("[bold yellow]⚡ Fast Scan[/bold yellow]")
        
        flags_found = []
        
        if self.tool_status['strings']:
            stdout, stderr, code = self.run_command(
                ['strings', str(self.file_path)],
                "Running strings"
            )
            flags = self.search_flags_from_outputs(stdout, stderr, "fast scan (strings)")
            if flags:
                flags_found.extend(flags)
                console.print(f"[green]✓ strings: {len(flags)} flag(s)[/green]")
        
        if self.tool_status['zsteg'] and self.file_path.suffix.lower() in ['.png', '.bmp']:
            stdout, stderr, code = self.run_command(
                ['zsteg', '-a', str(self.file_path)],
                "Running zsteg"
            )
            flags = self.search_flags_from_outputs(stdout, stderr, "fast scan (zsteg)")
            if flags:
                flags_found.extend(flags)
                console.print(f"[green]✓ zsteg: {len(flags)} flag(s)[/green]")
        
        # Remove duplicates while preserving tuple structure
        unique_flags = []
        seen = set()
        for flag in flags_found:
            flag_text = flag[0] if isinstance(flag, tuple) else flag
            if flag_text not in seen:
                seen.add(flag_text)
                unique_flags.append(flag)
        
        if unique_flags:
            console.print("\n[bold green]🎯 Flags Found:[/bold green]")
            for flag in unique_flags:
                console.print(f"  [green]•[/green] {flag[0]} [dim]({flag[1]})[/dim]")
            self.found_flags.extend(unique_flags)
            
            if not Confirm.ask("\n[yellow]Continue with deep analysis?[/yellow]", default=False):
                return True
        else:
            console.print("[dim]No flags found, starting deep analysis...[/dim]")
        
        console.print()
        return False
    
    
    def deep_analysis(self):
        console.print("\n[bold magenta]🔍 Deep Analysis[/bold magenta]")
        
        self.run_exiftool()
        self.run_binwalk()
        self.run_steghide()
        self.run_outguess()
        self.run_foremost()
        self.run_zsteg_deep()
        self.bruteforce_archives()
    
    def run_exiftool(self):
        if not self.tool_status['exiftool']:
            return
        stdout, stderr, code = self.run_command(
            ['exiftool', str(self.file_path)],
            "Extracting metadata"
        )
        
        if code == 0:
            flags = self.search_flags_from_outputs(stdout, stderr, "exiftool metadata")
            if flags:
                console.print(f"[green]✓ exiftool: {len(flags)} flag(s)[/green]")
                self.found_flags.extend(flags)
            
            # Extract interesting metadata
            self._extract_metadata_info(stdout, "exiftool")
    
    def run_binwalk(self):
        if not self.tool_status['binwalk']:
            return
        
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout, stderr, code = self.run_command(
                ['binwalk', '-e', '-C', temp_dir, str(self.file_path)],
                "Scanning and extracting embedded files"
            )
            
            flags = self.search_flags_from_outputs(stdout, stderr, "binwalk mapping")
            if flags:
                console.print(f"[green]✓ binwalk: {len(flags)} flag(s)[/green]")
                self.found_flags.extend(flags)
                
            extracted_flags = self._scan_extracted_files(temp_dir, "binwalk")
            if extracted_flags:
                console.print(f"[green]✓ binwalk extracted: {len(extracted_flags)} flag(s)[/green]")
                self.found_flags.extend(extracted_flags)
    
    def run_steghide(self):
        if not self.tool_status['steghide']:
            return
        
        if self.file_path.suffix.lower() not in ['.jpg', '.jpeg', '.bmp', '.wav', '.au']:
            return
        
        # First check if there's embedded data
        stdout, stderr, code = self.run_command(
            f'steghide info "{self.file_path}" -p ""',
            "Checking steghide info",
            shell=True
        )
        
        flags = self.search_flags_from_outputs(stdout, stderr, "steghide info")
        if flags:
            console.print(f"[green]✓ steghide: {len(flags)} flag(s)[/green]")
            self.found_flags.extend(flags)
        
        # Check if embedded file is detected
        if 'embedded' in stdout.lower() or 'embedded' in stderr.lower():
            console.print(f"[yellow]→ Bruteforcing steghide ({len(self.wordlist)} passwords)...[/yellow]")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                for idx, password in enumerate(self.wordlist, 1):
                    output_file = os.path.join(temp_dir, 'steghide_extracted.bin')
                    extract_cmd = f'steghide extract -sf "{self.file_path}" -xf "{output_file}" -p "{password}" -f'
                    
                    stdout_ex, stderr_ex, code_ex = self.run_command(
                        extract_cmd,
                        f"[{idx}/{len(self.wordlist)}] Trying: {'(empty)' if not password else password}",
                        shell=True,
                        silent=True
                    )
                    
                    if code_ex == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        console.print(f"[green]✓ steghide extracted with password: {'(empty)' if not password else password}[/green]")
                        
                        # Read and scan extracted content
                        try:
                            with open(output_file, 'rb') as f:
                                content = f.read()
                            
                            # Try to decode as text
                            text_content = content.decode('utf-8', errors='ignore')
                            flags_ex = self.search_flags(text_content, "steghide extracted")
                            if flags_ex:
                                console.print(f"[green]✓ steghide extracted: {len(flags_ex)} flag(s)[/green]")
                                self.found_flags.extend(flags_ex)
                            
                            # Also check for encoded flags
                            encoded_flags, interesting = self.find_encoded_flags(text_content, "steghide extracted")
                            if encoded_flags:
                                self.found_flags.extend(encoded_flags)
                            if interesting:
                                self.interesting_strings.extend(interesting)
                        except Exception:
                            pass
                        
                        break
                else:
                    console.print("[red]✗ Steghide bruteforce failed - try custom wordlist with -w[/red]")

    def run_outguess(self):
        if not self.tool_status['outguess']:
            return

        if self.file_path.suffix.lower() not in ['.jpg', '.jpeg']:
            return

        stdout, stderr, code = self.run_command(
            ['outguess', '-r', str(self.file_path), '/dev/stdout'],
            "Scanning with outguess"
        )

        flags = self.search_flags_from_outputs(stdout, stderr, "outguess output")
        if flags:
            console.print(f"[green]✓ outguess: {len(flags)} flag(s)[/green]")
            self.found_flags.extend(flags)
    
    def run_foremost(self):
        if not self.tool_status['foremost']:
            return
        
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout, stderr, code = self.run_command(
                ['foremost', '-i', str(self.file_path), '-o', temp_dir],
                "Extracting files with foremost"
            )
            
            extracted_flags = self._scan_extracted_files(temp_dir, "foremost")
            if extracted_flags:
                console.print(f"[green]✓ foremost: {len(extracted_flags)} flag(s)[/green]")
                self.found_flags.extend(extracted_flags)
    
    def run_zsteg_deep(self):
        if not self.tool_status['zsteg']:
            return
        
        if self.file_path.suffix.lower() not in ['.png', '.bmp']:
            return
        
        stdout, stderr, code = self.run_command(
            ['zsteg', '-a', str(self.file_path)],
            "Running comprehensive analysis"
        )
        
        if code == 0:
            flags = self.search_flags_from_outputs(stdout, stderr, "zsteg deep analysis")
            if flags:
                console.print(f"[green]✓ zsteg deep: {len(flags)} flag(s)[/green]")
                self.found_flags.extend(flags)
    
    def bruteforce_archives(self):
        """Bruteforce password-protected archives (zip, rar)"""
        file_ext = self.file_path.suffix.lower()
        
        if file_ext == '.zip':
            self._bruteforce_zip()
    
    def _bruteforce_zip(self):
        """Bruteforce ZIP file passwords"""
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                # Check if password protected
                for info in zf.infolist():
                    if info.flag_bits & 0x1:  # Password protected
                        console.print(f"[yellow]→ Bruteforcing ZIP ({len(self.wordlist)} passwords)...[/yellow]")
                        
                        for idx, password in enumerate(self.wordlist, 1):
                            try:
                                pwd_bytes = password.encode('utf-8')
                                zf.extractall(pwd=pwd_bytes, path=tempfile.gettempdir())
                                console.print(f"[green]✓ ZIP password found: {password if password else '(empty)'}[/green]")
                                
                                # Extract and scan contents
                                with tempfile.TemporaryDirectory() as temp_dir:
                                    zf.extractall(pwd=pwd_bytes, path=temp_dir)
                                    extracted_flags = self._scan_extracted_files(temp_dir, "zip")
                                    if extracted_flags:
                                        console.print(f"[green]✓ zip: {len(extracted_flags)} flag(s)[/green]")
                                        self.found_flags.extend(extracted_flags)
                                return
                            except (RuntimeError, zipfile.BadZipFile):
                                continue
                            except Exception:
                                continue
                        
                        console.print("[red]✗ ZIP bruteforce failed - try custom wordlist with -w[/red]")
                        break
        except zipfile.BadZipFile:
            pass
        except Exception:
            pass
    
    def scan_output_for_flags(self):
        pass
    
    def show_results(self):
        console.print("\n[bold cyan]═══ Results ═══[/bold cyan]")
        
        # Remove duplicates while preserving tuple structure
        seen_flags = set()
        unique_flags = []
        for item in self.found_flags:
            flag_text = item[0] if isinstance(item, tuple) else item
            if flag_text not in seen_flags:
                seen_flags.add(flag_text)
                unique_flags.append(item)
        
        seen_interesting = set()
        unique_interesting = []
        for item in self.interesting_strings:
            data_text = item[0] if isinstance(item, tuple) else item
            if data_text not in seen_interesting:
                seen_interesting.add(data_text)
                unique_interesting.append(item)

        actionable_interesting = []
        actionable_tags = (
            "[CTF Keyword]",
            "[Credentials]",
            "[Access Info]",
            "[URL]",
            "[File Path]",
            "[Code/Command]",
        )
        for item in unique_interesting:
            source_text = item[1] if isinstance(item, tuple) else "unknown"
            if any(tag in source_text for tag in actionable_tags):
                actionable_interesting.append(item)
        
        seen_metadata = set()
        unique_metadata = []
        for item in self.metadata_findings:
            data_text = item[0] if isinstance(item, tuple) else item
            if data_text not in seen_metadata:
                seen_metadata.add(data_text)
                unique_metadata.append(item)
        
        if unique_flags:
            console.print(f"\n[bold green]🎯 Flags ({len(unique_flags)}):[/bold green]")
            for item in unique_flags:
                flag_text = item[0] if isinstance(item, tuple) else item
                source_text = item[1] if isinstance(item, tuple) else "unknown"
                console.print(f"  [green]•[/green] {flag_text} [dim]({source_text})[/dim]")
        else:
            console.print("\n[yellow]No flags found[/yellow]")
            
        if actionable_interesting:
            console.print(f"\n[bold yellow]🔍 Interesting ({len(actionable_interesting)}):[/bold yellow]")
            for item in actionable_interesting[:5]:
                data_text = item[0] if isinstance(item, tuple) else item
                source_text = item[1] if isinstance(item, tuple) else "unknown"
                console.print(f"  [yellow]•[/yellow] {data_text[:80]}... [dim]({source_text})[/dim]")
            if len(actionable_interesting) > 5:
                console.print(f"  [dim]... and {len(actionable_interesting) - 5} more[/dim]")
        
        if unique_metadata:
            console.print(f"\n[bold magenta]📋 Metadata ({len(unique_metadata)}):[/bold magenta]")
            for item in unique_metadata[:3]:  # Show max 3
                field_text = item[0] if isinstance(item, tuple) else item
                source_text = item[1] if isinstance(item, tuple) else "unknown"
                console.print(f"  [magenta]•[/magenta] {field_text[:80]} [dim]({source_text})[/dim]")
            if len(unique_metadata) > 3:
                console.print(f"  [dim]... and {len(unique_metadata) - 3} more[/dim]")
        
        console.print()
    
    def run(self):
        self.show_banner()
        self.show_tool_status()
        
        fast_done = False
        if not self.skip_fast:
            fast_done = self.fast_scan()
        else:
            console.print("[yellow]⊘[/yellow] Fast scan skipped")
        
        if fast_done or self.skip_deep:
            if self.skip_deep:
                console.print("[yellow]⊘[/yellow] Deep analysis skipped")
            self.show_results()
            return
        
        self.deep_analysis()
        self.show_results()

def main():
    parser = argparse.ArgumentParser(
        description='CTFuck - Steganography Automation Tool for CTF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ctfuck image.png -f "FLAG{"
  ctfuck image.png -f "CTF{" -w /usr/share/wordlists/rockyou.txt
  ctfuck archive.zip -f "flag{" --skip-fast
        """
    )
    
    parser.add_argument(
        'file',
        help='File to analyze'
    )
    
    parser.add_argument(
        '-f', '--flag-format',
        required=True,
        help='Flag format to search (e.g., "FLAG{", "CTF{")'
    )
    
    parser.add_argument(
        '-w', '--wordlist',
        help='Custom wordlist file for bruteforce attacks'
    )

    parser.add_argument(
        '--skip-fast',
        action='store_true',
        help='Skip fast scan (strings/zsteg)'
    )

    parser.add_argument(
        '--skip-deep',
        action='store_true',
        help='Skip deep analysis'
    )
    
    args = parser.parse_args()
    
    try:
        ctfuck = CTFuck(
            file_path=args.file,
            flag_format=args.flag_format,
            wordlist=args.wordlist,
            skip_fast=args.skip_fast,
            skip_deep=args.skip_deep,
        )
        ctfuck.run()
    except KeyboardInterrupt:
        console.print("\n[bold red]✗ Interrupted[/bold red]")
        exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {str(e)}[/bold red]")
        exit(1)

if __name__ == '__main__':
    main()
