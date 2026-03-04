#!/usr/bin/env python3

import argparse
import subprocess
import re
import shutil
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
    def __init__(self, file_path, flag_format, output_dir=None, skip_fast=False, skip_deep=False):
        self.file_path = Path(file_path)
        self.flag_format = flag_format.strip()
        self.flag_patterns = self._build_flag_patterns(self.flag_format)
        self.output_dir = Path(output_dir) if output_dir else Path(f"ctfuck_output_{self.file_path.stem}")
        self.found_flags = []
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
        table.add_row("Output Directory", str(self.output_dir))
        
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
    
    def search_flags(self, text):
        found = set()
        for pattern in self.flag_patterns:
            for match in pattern.findall(text):
                if isinstance(match, tuple):
                    match = "".join(match)
                cleaned = re.sub(r"[\r\n\t]+", "", match).strip()
                if cleaned:
                    found.add(cleaned)
        return list(found)

    def search_flags_from_outputs(self, stdout, stderr):
        combined = f"{stdout}\n{stderr}"
        return self.search_flags(combined)
    
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
            flags = self.search_flags_from_outputs(stdout, stderr)
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
            flags = self.search_flags_from_outputs(stdout, stderr)
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
                "\n".join([f"[bold green]{flag}[/bold green]" for flag in flags_found]),
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
    
    def setup_output_dir(self):
        pass
    
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
            flags = self.search_flags_from_outputs(stdout, stderr)
            if flags:
                console.print(f"[bold green]🎯 Found {len(flags)} flag(s) in metadata[/bold green]")
                self.found_flags.extend(flags)
    
    def run_binwalk(self):
        if not self.tool_status['binwalk']:
            console.print("[yellow]⊘[/yellow] binwalk not available")
            return
        
        console.print("\n[bold cyan]═══ Binwalk ═══[/bold cyan]")
        
        stdout, stderr, code = self.run_command(
            ['binwalk', str(self.file_path)],
            "Scanning for embedded files"
        )
        
        if code == 0:
            flags = self.search_flags_from_outputs(stdout, stderr)
            if flags:
                console.print(f"[bold green]🎯 Found {len(flags)} flag(s) in binwalk output[/bold green]")
                self.found_flags.extend(flags)
    
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
        
        flags = self.search_flags_from_outputs(stdout, stderr)
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

        flags = self.search_flags_from_outputs(stdout, stderr)
        if flags:
            console.print(f"[bold green]🎯 Found {len(flags)} flag(s)[/bold green]")
            self.found_flags.extend(flags)
    
    def run_foremost(self):
        if not self.tool_status['foremost']:
            console.print("[yellow]⊘[/yellow] foremost not available")
            return
        
        console.print("\n[bold cyan]═══ Foremost ═══[/bold cyan]")
        console.print("[yellow]⊘[/yellow] Foremost skipped (no file saving mode)")
    
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
            flags = self.search_flags_from_outputs(stdout, stderr)
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
        
        if unique_flags:
            table = Table(title="[bold green]🎯 FLAGS FOUND[/bold green]", box=box.DOUBLE, border_style="green")
            table.add_column("#", style="cyan", width=5)
            table.add_column("Flag", style="bold green")
            
            for idx, flag in enumerate(unique_flags, 1):
                table.add_row(str(idx), flag)
            
            console.print(table)
            console.print(f"\n[bold green]Total: {len(unique_flags)} unique flag(s)[/bold green]")
        else:
            console.print("[yellow]⊘ No flags found[/yellow]")
        
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
  ctfuck image.png -f "CTF{" -o /tmp/output
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
        '-o', '--output-dir',
        help='Output directory (default: ctfuck_output_<filename>)'
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
            output_dir=args.output_dir,
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
