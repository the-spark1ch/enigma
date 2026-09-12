# **Enigma**

Enigma is a lightweight, zero-exposure system hardening and privacy management utility engineered for Windows operating systems. It gives users granular visibility into hidden diagnostic pipelines, scheduled telemetry wake-up routines, local artificial intelligence screen indexing, and local network leak vectors, providing a deterministic engine to audit and neutralize exposure surfaces.

Unlike heavyweight endpoint administration tools or Electron-packaged utilities, Enigma couples a native Python core with pywebview to render an asynchronous, hardware-accelerated interface with a minimal memory footprint. All typography and web assets are bundled strictly offline under a self-contained Content Security Policy (default-src 'self'), preventing background telemetry leaks and external DNS requests. Every system modification is recorded within an isolated, integrity-verified state snapshot, guaranteeing that any disabled service, script action, or registry policy can be completely restored to its original baseline at any time.

## **Core Capabilities**

Enigma evaluates and secures system configurations across primary exposure surfaces without degrading core operating system integrity:

> * **Operational Security Baselines**: Calibrates mitigations via three distinct operational baselines (**Balanced Baseline**, **Maximum Isolation**, and **Custom Architecture**) with persistent configuration caching in config.json.  
> * **Edition-Adaptive Telemetry Stripping**: Enforces Group Policy locks across Windows Data Collection (AllowTelemetry) that dynamically adapt between Enterprise/Education and Pro/Home editions, halts device census routines, disables Feedback notifications, and stops background Microsoft Edge diagnostic processes.  
> * **AI & Screen Vectorization Neutralization**: Blocks Windows 11 Recall screen captures and semantic vector analysis (TurnOffRecall), isolates Windows Copilot context streams, and disables Windows AI data analysis pipelines.  
> * **Network & Protocol Hardening**: Disables obsolete name resolution protocols (LLMNR and NetBIOS) directly via native 64-bit Registry abstractions, enforces system-wide DNS-over-HTTPS (EnableAutoDoh), and blocks peer-to-peer Delivery Optimization bandwidth seeding while preserving the underlying DoSvc service required for Windows Update and Microsoft Store compatibility.  
> * **Scoped Input Privacy Protection**: Inhibits cloud synchronization of typing dictionaries, handwriting recognition samples, and cross-device cloud clipboard sync while preserving local clipboard history (Win \+ V).  
> * **Fault-Tolerant Trace Sanitization**: Cleans unencrypted Jump Lists and Recent Documents histories with locked-descriptor fault tolerance, and prevents Windows Content Delivery Manager from silently deploying third-party packages.  
> * **Hardware & Kernel Architecture Inspector**: An integrated inspection modal providing real-time hardware identity, elevation token status, processor architecture, exact build revision, and Windows 11 platform status.

## **Operational Profiles**

| Profile | Scope & Focus | Operating System Impact |
| :---- | :---- | :---- |
| **Balanced Baseline** | Neutralizes diagnostic telemetry, advertising GUIDs, keystroke cadences, and background Edge daemons. | **Zero Impact**: Preserves LAN printing, Wi-Fi networking, Windows Update, Microsoft Store, and local clipboard history (Win \+ V). |
| **Maximum Isolation** | Full containment: Windows Recall AI, Copilot streams, NetBIOS, LLMNR, location sensors, and crash dump uploads. | **High Hardening**: Enforces strict air-gap style isolation across local subnets and telemetry daemons. |
| **Custom Architecture** | Unrestricted administrator audit. | Complete manual control over individual vectors without automated presets. |

## **Getting Started**

Enigma is distributed both as a standalone portable executable for direct use and as an open-source Python codebase for auditing and manual execution.

### **Option 1: Standalone Binary (Recommended)**

> 1. Download the latest Enigma.exe executable from the **GitHub Releases** page or from the **Official Website**.  
> 2. Run Enigma.exe with administrative privileges.  
> 3. If executed under a standard user token, select the **Elevate Privilege** button in the header bar to trigger Windows User Account Control (UAC) elevation.

### **Option 2: Running from Source**

#### **Requirements**

> * Windows 10 or Windows 11 (64-bit architecture)  
> * Python 3.10 or newer  
> * Microsoft Edge WebView2 Runtime (installed by default on modern Windows installations)

#### **Installation Steps**

Clone the repository and install the application dependencies:

```
git clone https://github.com/username/enigma.git  
cd enigma  
pip install pywebview
```

Start the application interface:

```
python main.py
```

### **Compiling to Standalone Executable**

To compile a standalone, single-file binary with embedded offline web assets and schemas:

```
pip install pyinstaller  
pyinstaller \--noconsole \--onefile \--name "Enigma" \--add-data "web;web" \--add-data "rules.json;." \--add-data "backup\_state.json;." main.py
```

## **Architectural Design**

The application is structured around a strict separation of engine operations, rule declarations, and transactional state persistence:

> * **Engine Kernel (core.py)**: Interfaces directly with the Windows API through 64-bit Registry abstractions (KEY\_WRITE, KEY\_WOW64\_64KEY), the Service Control Manager (sc.exe), and scheduled task interfaces (schtasks.exe). Manages automated system restore points (Checkpoint-Computer), frozen-aware UAC elevation, and native NetBIOS interface enumeration without spawning external PowerShell interpreters.  
> * **Declarative Rules (rules.json)**: Contains structured rules defining system targets, expected safe values, severity ranks, baseline profile assignments, and explicit remediation actions.  
> * **Triple-Layer State Storage (backup\_state.json)**: Preserves pre-remediation states—including original registry values, types (REG\_DWORD, REG\_SZ), initial service startup modes, and NetBIOS interface states—within %APPDATA%\\Enigma. State persistence leverages atomic buffer replacement (os.replace), replica mirroring (.bak), and SHA-256 integrity checksum verification (backup\_state.json.sha256).  
> * **Offline Interface Layer**: A desktop interface built with CSS grid and local TrueType typography (Bruno Ace, Plus Jakarta Sans, and Space Mono), communicating asynchronously with the Python host via JSON-RPC under a self-contained Content Security Policy.

## **State Management and Safety Guarantees**

Enigma rejects blind registry overrides and destructive terminal scripts. Before enforcing any mitigation:

> * **Non-Destructive Inspection**: The engine performs read-only checks against target registry keys, network adapters, and system services prior to any modification.  
> * **System Restore Safeguards**: An automated system restore point checkpoint is scheduled prior to batch or single-vector mitigations, enforcing a single-attempt session rule to prevent engine stalls on unconfigured machines.  
> * **Service Dependency Integrity**: Essential update daemons (such as DoSvc) are protected from full deactivation, neutralizing bandwidth seeding purely through Group Policy overrides.  
> * **Exact Rollback Capabilities**: Reverting an issue restores original registry entries, re-enables scheduled tasks, restores individual adapter NetBIOS options, and re-engages automatic services via the Service Control Manager.  
> * **Atomic State Commits**: State files are validated against SHA-256 checksums on startup to prevent operation with corrupted snapshots.

## **License**

Enigma is distributed under the terms of the **GNU General Public License v3.0 (GPLv3)**. You are free to run, review, modify, and redistribute this software. Any derivative works or distributions that incorporate this codebase must remain open source under the same GPLv3 terms.
