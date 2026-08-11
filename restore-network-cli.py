#!/usr/bin/env python3
"""
Beautiful Wireless Interface Manager - CLI Version
With colorful terminal output and interactive menu
"""

import subprocess
import os
import sys
import time
import re
import shutil
from enum import Enum

class Colors:
    """Terminal colors for beautiful output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    DIM = '\033[2m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'
    BG_YELLOW = '\033[43m'
    BG_GRAY = '\033[100m'

class Mode(Enum):
    MONITOR = "monitor"
    MANAGED = "managed"
    UNKNOWN = "unknown"

class BeautifulWirelessManagerCLI:
    def __init__(self):
        # Check root
        if os.geteuid() != 0:
            print(f"{Colors.RED}❌ Error: Please run as root (sudo){Colors.END}")
            sys.exit(1)
        
        # Get terminal size for centering
        self.term_width = shutil.get_terminal_size().columns
        
        # Get first wireless interface
        self.interface = self.get_first_wireless()
        if not self.interface:
            print(f"{Colors.RED}❌ Error: No wireless interface found!{Colors.END}")
            sys.exit(1)
        
        # Interface pour le mode monitor
        self.monitor_interface = None
        
        # Start the app
        self.clear_screen()
        self.run()

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def center_text(self, text, color=Colors.END, bold=False):
        """Center text in terminal"""
        if bold:
            text = f"{Colors.BOLD}{text}{Colors.END}"
        padding = max(0, (self.term_width - len(text)) // 2)
        return f"{' ' * padding}{color}{text}{Colors.END}"

    def print_header(self):
        """Print application header"""
        print("\n" + "=" * self.term_width)
        print(self.center_text("📶 WiFi Mode Switcher", Colors.CYAN, True))
        print("=" * self.term_width + "\n")

    def get_first_wireless(self):
        """Get first wireless interface - prioritize clean interfaces"""
        try:
            time.sleep(1)
            result = subprocess.run(['ip', 'link', 'show'],
                                  capture_output=True, text=True)
            
            interfaces = []
            for line in result.stdout.split('\n'):
                if 'wl' in line and ': wl' in line:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        iface = parts[1].split('@')[0].strip()
                        interfaces.append(iface)
            
            for iface in interfaces:
                if not iface.endswith('mon') and not iface.endswith('monmon'):
                    return iface
            
            if interfaces:
                return interfaces[0]
        except:
            pass
        return None

    def get_mode_for_interface(self, interface):
        """Get mode for a specific interface"""
        try:
            result = subprocess.run(['iw', 'dev', interface, 'info'],
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'type' in line:
                    return line.split()[-1]
        except:
            pass
        return 'unknown'

    def get_monitor_interface(self):
        """Find existing monitor interface"""
        try:
            result = subprocess.run(['ip', 'link', 'show'],
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'wl' in line and ': wl' in line and 'mon' in line:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        iface = parts[1].split('@')[0].strip()
                        if iface.endswith('mon'):
                            return iface
        except:
            pass
        return None

    def get_physical_interface(self):
        """Find physical interface (without 'mon' or 'monmon')"""
        try:
            result = subprocess.run(['ip', 'link', 'show'],
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'wl' in line and ': wl' in line and 'mon' not in line.split(': ')[1]:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        return parts[1].split('@')[0].strip()
            
            result = subprocess.run(['iw', 'dev'],
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    iface = line.split()[-1]
                    if not iface.endswith('mon') and not iface.endswith('monmon'):
                        return iface
            
            if self.interface:
                physical = re.sub(r'mon+$', '', self.interface)
                if physical and physical != self.interface:
                    return physical
        except:
            pass
        return None

    def cleanup_monitor_interfaces(self):
        """Remove all existing monitor interfaces"""
        try:
            result = subprocess.run(['ip', 'link', 'show'],
                                  capture_output=True, text=True)
            
            interfaces_to_remove = []
            for line in result.stdout.split('\n'):
                if 'wl' in line and ': wl' in line:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        iface = parts[1].split('@')[0].strip()
                        if iface.endswith('mon') or iface.endswith('monmon'):
                            interfaces_to_remove.append(iface)
            
            for iface in interfaces_to_remove:
                try:
                    subprocess.run(f'sudo iw dev {iface} del', shell=True,
                                 stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                    print(f"{Colors.GREEN}✅ Removed: {iface}{Colors.END}")
                except:
                    pass
            
            time.sleep(1)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Cleanup error: {e}{Colors.END}")

    def set_monitor(self):
        """Set to monitor mode"""
        try:
            print(f"\n{Colors.BLUE}🔄 Switching to MONITOR mode...{Colors.END}")
            
            subprocess.run(f'sudo nmcli device set {self.interface} managed no', shell=True,
                         stderr=subprocess.DEVNULL)
            
            self.cleanup_monitor_interfaces()
            
            physical_iface = self.get_physical_interface()
            if not physical_iface:
                physical_iface = self.interface
            
            subprocess.run(f'sudo airmon-ng start {physical_iface}', shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(2)
            
            monitor_iface = self.get_monitor_interface()
            if monitor_iface:
                self.monitor_interface = monitor_iface
                self.interface = physical_iface
                
                subprocess.run(f'sudo ip link set {self.monitor_interface} up', shell=True)
                
                print(f"{Colors.GREEN}✅ Successfully switched to MONITOR mode{Colors.END}")
                print(f"{Colors.DIM}   Interface: {self.interface}{Colors.END}")
                print(f"{Colors.DIM}   Monitor: {self.monitor_interface}{Colors.END}")
            else:
                print(f"{Colors.RED}❌ Failed to create monitor interface!{Colors.END}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}❌ Failed: {e}{Colors.END}")
            return False
        
        return True

    def set_managed(self):
        """Set to managed mode"""
        try:
            print(f"\n{Colors.BLUE}🔄 Switching to MANAGED mode...{Colors.END}")
            
            if self.monitor_interface:
                subprocess.run(f'sudo airmon-ng stop {self.monitor_interface}', shell=True,
                             stderr=subprocess.DEVNULL)
                self.monitor_interface = None
            
            self.cleanup_monitor_interfaces()
            
            physical_iface = self.get_physical_interface()
            if not physical_iface:
                physical_iface = self.interface
            
            subprocess.run(f'sudo ip link set {physical_iface} down', shell=True)
            subprocess.run(f'sudo iw dev {physical_iface} set type managed', shell=True)
            subprocess.run(f'sudo ip link set {physical_iface} up', shell=True)
            
            self.interface = physical_iface
            
            subprocess.run(f'sudo nmcli device set {self.interface} managed yes', shell=True,
                         stderr=subprocess.DEVNULL)
            subprocess.run('sudo systemctl restart NetworkManager', shell=True,
                         stderr=subprocess.DEVNULL)
            
            try:
                subprocess.run(f'sudo dhclient -r {self.interface}', shell=True,
                             stderr=subprocess.DEVNULL)
                time.sleep(1)
                subprocess.run(f'sudo dhclient {self.interface}', shell=True,
                             stderr=subprocess.DEVNULL)
            except:
                pass
            
            print(f"{Colors.GREEN}✅ Successfully switched to MANAGED mode{Colors.END}")
            print(f"{Colors.DIM}   Interface: {self.interface}{Colors.END}")
            
        except Exception as e:
            print(f"{Colors.RED}❌ Failed: {e}{Colors.END}")
            return False
        
        return True

    def display_status(self):
        """Display current status"""
        # Update monitor interface
        self.monitor_interface = self.get_monitor_interface()
        
        # Get current mode
        if self.monitor_interface:
            mode = self.get_mode_for_interface(self.monitor_interface)
        else:
            mode = self.get_mode_for_interface(self.interface)
        
        print("\n" + "─" * self.term_width)
        print(f"{Colors.BOLD}📊 Status{Colors.END}")
        print("─" * self.term_width)
        
        # Interface
        print(f"{Colors.CYAN}┌ Interface:{Colors.END} {self.interface}")
        
        # Monitor interface
        if self.monitor_interface:
            print(f"{Colors.CYAN}├ Monitor:{Colors.END} {Colors.RED}{self.monitor_interface}{Colors.END}")
        else:
            print(f"{Colors.CYAN}├ Monitor:{Colors.END} {Colors.DIM}None{Colors.END}")
        
        # Mode
        if mode == 'monitor':
            mode_display = f"{Colors.RED}🔴 MONITOR MODE{Colors.END}"
            mode_color = Colors.RED
        elif mode == 'managed':
            mode_display = f"{Colors.GREEN}🟢 MANAGED MODE{Colors.END}"
            mode_color = Colors.GREEN
        else:
            mode_display = f"{Colors.YELLOW}❓ UNKNOWN{Colors.END}"
            mode_color = Colors.YELLOW
        
        print(f"{Colors.CYAN}└ Mode:{Colors.END} {mode_display}")
        print("─" * self.term_width + "\n")

    def display_menu(self):
        """Display interactive menu"""
        print(f"{Colors.BOLD}📋 Menu{Colors.END}")
        print("─" * self.term_width)
        print(f"  {Colors.BOLD}1.{Colors.END} {Colors.RED}📡 MONITOR{Colors.END} - Switch to monitor mode")
        print(f"  {Colors.BOLD}2.{Colors.END} {Colors.GREEN}🌐 MANAGED{Colors.END} - Switch to managed mode")
        print(f"  {Colors.BOLD}3.{Colors.END} {Colors.YELLOW}🔄 Refresh{Colors.END} - Update status")
        print(f"  {Colors.BOLD}4.{Colors.END} {Colors.BLUE}📊 Status{Colors.END} - Show detailed status")
        print(f"  {Colors.BOLD}5.{Colors.END} {Colors.RED}✖ Exit{Colors.END} - Exit application")
        print("─" * self.term_width)

    def run(self):
        """Main application loop"""
        while True:
            self.clear_screen()
            self.print_header()
            
            # Update status
            self.monitor_interface = self.get_monitor_interface()
            self.display_status()
            
            # Display menu
            self.display_menu()
            
            # Get user input
            try:
                choice = input(f"{Colors.BOLD}➜ Choose an option: {Colors.END}").strip()
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}👋 Goodbye!{Colors.END}")
                break
            
            if choice == '1':
                self.set_monitor()
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")
                
            elif choice == '2':
                self.set_managed()
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")
                
            elif choice == '3':
                continue
                
            elif choice == '4':
                self.clear_screen()
                self.print_header()
                self.display_status()
                
                # Show more details
                print(f"{Colors.BOLD}🔍 Detailed Information{Colors.END}")
                print("─" * self.term_width)
                
                # Show wireless interfaces
                print(f"{Colors.CYAN}Available Wireless Interfaces:{Colors.END}")
                try:
                    result = subprocess.run(['ip', 'link', 'show'],
                                          capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if 'wl' in line:
                            print(f"  {line.strip()}")
                except:
                    pass
                
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")
                
            elif choice == '5':
                print(f"\n{Colors.YELLOW}👋 Goodbye!{Colors.END}")
                break
                
            else:
                print(f"{Colors.RED}❌ Invalid choice! Please try again.{Colors.END}")
                time.sleep(1)

if __name__ == "__main__":
    try:
        app = BeautifulWirelessManagerCLI()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Goodbye!{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        sys.exit(1)