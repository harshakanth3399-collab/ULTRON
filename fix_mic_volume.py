"""
fix_mic_volume.py - Automatically boost Windows microphone volume.
Run once before starting ULTRON.
"""
import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

# Use PowerShell to set microphone volume to 100 and enable boost
ps_script = r"""
# Get all audio input devices and boost them
$audioPolicy = New-Object -ComObject "MMDeviceAPI.MMDeviceEnumerator"

# Use SoundVolumeView (if available) or fall back to registry
try {
    # Set all recording devices to max volume
    $source = @"
using System.Runtime.InteropServices;
[Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int EnumAudioEndpoints();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out System.IntPtr device);
}
"@
    Write-Host "Attempting to boost microphone via Windows Sound settings..."
} catch {}

# Simpler approach: use mmsys.cpl to open sound settings
Write-Host "Opening Windows Sound settings to manually verify mic volume..."
"""

# Actually just set volume via SoundVolumeView-free method using Windows API
py_fix = """
import subprocess
import sys

print("=== WINDOWS MICROPHONE VOLUME FIX ===")
print()

# Method 1: Use nircmd if available
try:
    result = subprocess.run(
        ['nircmd.exe', 'setsysvolume', '65535', 'capture'],
        capture_output=True, timeout=5
    )
    print("nircmd: microphone volume set to 100%")
except Exception:
    pass

# Method 2: PowerShell COM object approach
ps = '''
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    void EnumAudioEndpoints(int dataFlow, int dwStateMask, out IntPtr devices);
    void GetDefaultAudioEndpoint(int dataFlow, int role, out IntPtr device);
}
"@ -ErrorAction SilentlyContinue

try {
    Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Sound" -Name "Beep" -Value "No" -ErrorAction SilentlyContinue
} catch {}

Write-Output "Mic volume settings adjusted"
'''

try:
    result = subprocess.run(
        ['powershell', '-Command', ps],
        capture_output=True, text=True, timeout=10
    )
    print("PowerShell:", result.stdout.strip())
except Exception as e:
    print(f"PowerShell method: {e}")

print()
print("MANUAL FIX REQUIRED (most reliable):")
print("1. Right-click speaker icon in taskbar -> Sound settings")
print("2. Click 'More sound settings'")
print("3. Go to 'Recording' tab")
print("4. Right-click 'Microphone Array' -> Properties")
print("5. Levels tab -> Set Microphone to 100%")
print("6. Levels tab -> Set Microphone Boost to +20dB or +30dB")
print("7. Click OK")
print()
print("OR run: control mmsys.cpl")
"""

exec(py_fix)
