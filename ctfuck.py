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
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich import box

console = Console()

BANNER = """
   ██████╗████████╗███████╗██╗   ██╗ ██████╗██╗  ██╗
  ██╔════╝╚══██╔══╝██╔════╝██║   ██║██╔════╝██║ ██╔╝
  ██║        ██║   █████╗  ██║   ██║██║     █████╔╝ 
  ██║        ██║   ██╔══╝  ██║   ██║██║     ██╔═██╗ 
  ╚██████╗   ██║   ██║     ╚██████╔╝╚██████╗██║  ██╗
   ╚═════╝   ╚═╝   ╚═╝      ╚═════╝  ╚═════╝╚═╝  ╚═╝

      Steganography Automation Tool for CTF
"""

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
    def __init__(self, file_path, flag_format, skip_fast=False, skip_deep=False):
        self.file_path = Path(file_path)
        self.flag_format = flag_format.strip()
        self.flag_patterns = self._build_flag_patterns(self.flag_format)
        self.found_flags = []
        self.interesting_strings = []
        self.tool_status = ToolChecker.check_all_tools()
        self.skip_fast = skip_fast
        self.skip_deep = skip_deep
        
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
    
    def show_banner(self):
        console.print(Panel(
            f"[bold cyan]{BANNER}[/bold cyan]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan", width=20)
        table.add_column("Value", style="yellow")
        
        table.add_row("Target File", str(self.file_path))
        table.add_row("Flag Format", self.flag_format)
        
        console.print(table)
        console.print()
    
    def show_tool_status(self):
        table = Table(title="[bold]Tool Availability[/bold]", box=box.ROUNDED)
        table.add_column("Tool", style="cyan", width=15)
        table.add_column("Status", width=10)
        table.add_column("Package", style="dim")
        
        for tool, package in ToolChecker.REQUIRED_TOOLS.items():
            status = "✓" if self.tool_status[tool] else "✗"
            status_style = "green" if self.tool_status[tool] else "red"
            table.add_row(tool, f"[{status_style}]{status}[/{status_style}]", package)
        
        console.print(table)
        console.print()
        
        missing_tools = [tool for tool, available in self.tool_status.items() if not available]
        if missing_tools:
            console.print(f"[yellow]⚠ Warning:[/yellow] Missing tools. Install for full functionality.")
            console.print()
    
    def run_command(self, cmd, description, shell=False):
        try:
            console.print(f"[bold blue]→[/bold blue] {description}...")
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
            console.print(f"[bold red]✗[/bold red] Timeout: {description}")
            return "", "Timeout", -1
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Error: {str(e)}")
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
        entropy = 0
        for x in range(256):
            p_x = data.count(x) / len(data)
            if p_x > 0:
                entropy += - p_x * math.log(p_x, 2)
        return entropy

    def find_encoded_flags(self, text, source="unknown"):
        # Look for Base64 strings (length >= 16 to reduce false positives)
        b64_pattern = re.compile(r'(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?')
        # Look for Hex strings (length >= 16)
        hex_pattern = re.compile(r'\b(?:[0-9a-fA-F]{2}){8,}\b')

        found = []
        interesting = []

        # Check Base64
        for b64_match in b64_pattern.findall(text):
            if len(b64_match) % 4 != 0:
                continue
            try:
                decoded = base64.b64decode(b64_match).decode('utf-8', errors='ignore')
                flags = self.search_flags(decoded, source)
                if flags:
                    found.extend(flags)
                elif any(keyword in decoded.lower() for keyword in ['flag', 'key', 'password', 'secret', 'admin']):
                    # It's an interesting decoded string
                    is_printable = all(32 <= ord(c) < 127 for c in decoded)
                    if is_printable and len(decoded) > 3:
                        interesting.append((f"[Base64] {b64_match} -> {decoded}", source))
            except Exception:
                pass

        # Check Hex
        for hex_match in hex_pattern.findall(text):
            try:
                decoded = binascii.unhexlify(hex_match).decode('utf-8', errors='ignore')
                flags = self.search_flags(decoded, source)
                if flags:
                    found.extend(flags)
                elif any(keyword in decoded.lower() for keyword in ['flag', 'key', 'password', 'secret', 'admin']):
                    is_printable = all(32 <= ord(c) < 127 for c in decoded)
                    if is_printable and len(decoded) > 3:
                        interesting.append((f"[Hex] {hex_match} -> {decoded}", source))
            except Exception:
                pass

        return found, interesting

    def _scan_extracted_files(self, extract_dir, tool_name):
        flags_found = []
        # strings tool status check
        has_strings = self.tool_status.get('strings', False)
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_source = f"{tool_name} -> {file}"
                
                # Entropy Check
                try:
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        entropy = self.calculate_entropy(raw_data)
                        if entropy > 7.5:
                            self.interesting_strings.append((f"High Entropy Data ({entropy:.2f}) - Encrypted/Compressed?", file_source))
                except Exception:
                    pass

                if has_strings:
                    stdout, stderr, code = self.run_command(
                        ['strings', str(file_path)],
                        f"Scanning extracted file: {file}"
                    )
                    flags = self.search_flags_from_outputs(stdout, stderr, file_source)
                    if flags:
                        flags_found.extend(flags)
                else:
                    # Fallback to direct read if no strings tool
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            flags = self.search_flags(content, file_source)
                            encoded_flags, interesting = self.find_encoded_flags(content, file_source)
                            flags.extend(encoded_flags)
                            if interesting:
                                self.interesting_strings.extend(interesting)
                            if flags:
                                flags_found.extend(flags)
                    except Exception:
                        pass
        return flags_found

    def search_flags_from_outputs(self, stdout, stderr, source="unknown"):
        combined = f"{stdout}\n{stderr}"
        flags = self.search_flags(combined, source)
        
        encoded_flags, interesting = self.find_encoded_flags(combined, source)
        flags.extend(encoded_flags)
        
        if interesting:
            self.interesting_strings.extend(interesting)
            
        return flags
    
    def fast_scan(self):
        console.print(Panel(
            "[bold yellow]⚡ FAST SCAN - Quick Flag Hunter[/bold yellow]",
            border_style="yellow"
        ))
        
        flags_found = []
        
        if self.tool_status['strings']:
            stdout, stderr, code = self.run_command(
                ['strings', str(self.file_path)],
                "Running strings"
            )
            flags = self.search_flags_from_outputs(stdout, stderr, "fast scan (strings)")
            if flags:
                flags_found.extend(flags)
                console.print(f"[bold green]✓[/bold green] Found {len(flags)} flag(s) with strings")
        else:
            console.print("[yellow]⊘[/yellow] strings not available")
        
        if self.tool_status['zsteg'] and self.file_path.suffix.lower() in ['.png', '.bmp']:
            stdout, stderr, code = self.run_command(
                ['zsteg', '-a', str(self.file_path)],
                "Running zsteg"
            )
            flags = self.search_flags_from_outputs(stdout, stderr, "fast scan (zsteg)")
            if flags:
                flags_found.extend(flags)
                console.print(f"[bold green]✓[/bold green] Found {len(flags)} flag(s) with zsteg")
        else:
            if not self.tool_status['zsteg']:
                console.print("[yellow]⊘[/yellow] zsteg not available")
        
        flags_found = list(set(flags_found))
        
        if flags_found:
            console.print()
            console.print(Panel(
                "\n".join([f"[bold green]{flag[0]}[/bold green] (Source: {flag[1]})" for flag in flags_found]),
                title="[bold green]🎯 FLAGS FOUND[/bold green]",
                border_style="green",
                box=box.DOUBLE
            ))
            self.found_flags.extend(flags_found)
            
            if not Confirm.ask("\n[bold yellow]Continue with deep analysis?[/bold yellow]", default=False):
                return True
        else:
            console.print("[yellow]⊘[/yellow] No flags in fast scan. Starting deep analysis...")
        
        console.print()
        return False
    
    
    def deep_analysis(self):
        console.print(Panel(
            "[bold magenta]🔍 DEEP ANALYSIS - Full Steganography Scan[/bold magenta]",
            border_style="magenta"
        ))
        
        self.run_exiftool()
        self.run_binwalk()
        self.run_steghide()
        self.run_outguess()
        self.run_foremost()
        self.run_zsteg_deep()
    
    def run_exiftool(self):
        if not self.tool_status['exiftool']:
            console.print("[yellow]⊘[/yellow] exiftool not available")
            return
        
        console.print("\n[bold cyan]═══ ExifTool ═══[/bold cyan]")
        stdout, stderr, code = self.run_command(
            ['exiftool', str(self.file_path)],
            "Extracting metadata"
        )
        
        if code == 0:
            flags = self.search_flags_from_outputs(stdout, stderr, "exiftool metadata")
            if flags:
                console.print(f"[bold green]🎯 Found {len(flags)} flag(s) in metadata[/bold green]")
                self.found_flags.extend(flags)
    
    def run_binwalk(self):
        if not self.tool_status['binwalk']:
            console.print("[yellow]⊘[/yellow] binwalk not available")
            return
        
        console.print("\n[bold cyan]═══ Binwalk ═══[/bold cyan]")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout, stderr, code = self.run_command(
                ['binwalk', '-e', '-M', '--matryoshka-limit=3', '-C', temp_dir, str(self.file_path)],
                "Scanning and recursively extracting embedded files (Depth 3)"
            )
            
            flags = self.search_flags_from_outputs(stdout, stderr, "binwalk mapping")
            if flags:
                console.print(f"[bold green]🎯 Found {len(flags)} flag(s) in binwalk output[/bold green]")
                self.found_flags.extend(flags)
                
            extracted_flags = self._scan_extracted_files(temp_dir, "binwalk")
            if extracted_flags:
                console.print(f"[bold green]🎯 Found {len(extracted_flags)} flag(s) inside binwalk extracted files[/bold green]")
                self.found_flags.extend(extracted_flags)
    
    def run_steghide(self):
        if not self.tool_status['steghide']:
            console.print("[yellow]⊘[/yellow] steghide not available")
            return
        
        if self.file_path.suffix.lower() not in ['.jpg', '.jpeg', '.bmp', '.wav', '.au']:
            console.print("[yellow]⊘[/yellow] File type not supported by steghide")
            return
        
        console.print("\n[bold cyan]═══ Steghide ═══[/bold cyan]")
        
        stdout, stderr, code = self.run_command(
            f'steghide info "{self.file_path}" -p ""',
            "Checking steghide info",
            shell=True
        )
        
        flags = self.search_flags_from_outputs(stdout, stderr, "steghide info")
        if flags:
            console.print(f"[bold green]🎯 Found {len(flags)} flag(s)[/bold green]")
            self.found_flags.extend(flags)

    def run_outguess(self):
        if not self.tool_status['outguess']:
            console.print("[yellow]⊘[/yellow] outguess not available")
            return

        if self.file_path.suffix.lower() not in ['.jpg', '.jpeg']:
            console.print("[yellow]⊘[/yellow] File type not supported by outguess")
            return

        console.print("\n[bold cyan]═══ Outguess ═══[/bold cyan]")

        stdout, stderr, code = self.run_command(
            ['outguess', '-r', str(self.file_path), '/dev/stdout'],
            "Scanning with outguess"
        )

        flags = self.search_flags_from_outputs(stdout, stderr, "outguess output")
        if flags:
            console.print(f"[bold green]🎯 Found {len(flags)} flag(s)[/bold green]")
            self.found_flags.extend(flags)
    
    def run_foremost(self):
        if not self.tool_status['foremost']:
            console.print("[yellow]⊘[/yellow] foremost not available")
            return
        
        console.print("\n[bold cyan]═══ Foremost ═══[/bold cyan]")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout, stderr, code = self.run_command(
                ['foremost', '-i', str(self.file_path), '-o', temp_dir],
                "Extracting files with foremost"
            )
            
            extracted_flags = self._scan_extracted_files(temp_dir, "foremost")
            if extracted_flags:
                console.print(f"[bold green]🎯 Found {len(extracted_flags)} flag(s) inside foremost extracted files[/bold green]")
                self.found_flags.extend(extracted_flags)
    
    def run_zsteg_deep(self):
        if not self.tool_status['zsteg']:
            console.print("[yellow]⊘[/yellow] zsteg not available")
            return
        
        if self.file_path.suffix.lower() not in ['.png', '.bmp']:
            console.print("[yellow]⊘[/yellow] File type not supported by zsteg")
            return
        
        console.print("\n[bold cyan]═══ Zsteg Deep ═══[/bold cyan]")
        
        stdout, stderr, code = self.run_command(
            ['zsteg', '-a', str(self.file_path)],
            "Running comprehensive analysis"
        )
        
        if code == 0:
            flags = self.search_flags_from_outputs(stdout, stderr, "zsteg deep analysis")
            if flags:
                console.print(f"[bold green]🎯 Found {len(flags)} flag(s)[/bold green]")
                self.found_flags.extend(flags)
    
    def scan_output_for_flags(self):
        pass
    
    def show_results(self):
        console.print("\n")
        console.print(Panel(
            "[bold cyan]═══ ANALYSIS COMPLETE ═══[/bold cyan]",
            border_style="cyan"
        ))
        
        unique_flags = list(set(self.found_flags))
        unique_interesting = list(set(self.interesting_strings))
        
        if unique_flags:
            table = Table(title="[bold green]🎯 FLAGS FOUND[/bold green]", box=box.DOUBLE, border_style="green")
            table.add_column("#", style="cyan", width=5)
            table.add_column("Flag", style="bold green")
            table.add_column("Source", style="dim cyan")
            
            for idx, item in enumerate(unique_flags, 1):
                flag_text = item[0] if isinstance(item, tuple) else item
                source_text = item[1] if isinstance(item, tuple) else "unknown"
                table.add_row(str(idx), flag_text, source_text)
            
            console.print(table)
            console.print(f"\n[bold green]Total: {len(unique_flags)} unique flag(s)[/bold green]")
        else:
            console.print("[yellow]⊘ No flags found[/yellow]")
            
        if unique_interesting:
            console.print()
            table = Table(title="[bold yellow]🔍 INTERESTING DATA (Decoded & High Entropy)[/bold yellow]", box=box.ROUNDED, border_style="yellow")
            table.add_column("#", style="cyan", width=5)
            table.add_column("Details", style="yellow")
            table.add_column("Source", style="dim cyan")
            
            for idx, item in enumerate(unique_interesting, 1):
                data_text = item[0] if isinstance(item, tuple) else item
                source_text = item[1] if isinstance(item, tuple) else "unknown"
                table.add_row(str(idx), data_text, source_text)
                
            console.print(table)
            console.print(f"\n[bold yellow]Total: {len(unique_interesting)} interesting item(s)[/bold yellow]")
        
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
  ctfuck image.png -f "CTF{"
  ctfuck image.png -f "flag{" --skip-fast
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
