# **Enigma**

Enigma is a lightweight, zero-exposure system hardening and privacy management utility engineered for Windows operating systems. It gives users granular visibility into hidden diagnostic pipelines, scheduled telemetry wake-up routines, local artificial intelligence screen indexing, and local network leak vectors, providing a deterministic engine to audit and neutralize exposure surfaces.

Unlike heavyweight endpoint administration tools or Electron-packaged utilities, Enigma couples a native Python core with pywebview to render an asynchronous, hardware-accelerated interface with a minimal memory footprint. Every system modification is recorded within an isolated state snapshot, guaranteeing that any disabled service, script action, or registry policy can be completely restored to its original baseline at any time.

## **Core Capabilities**

Enigma evaluates and secures system configurations across five primary vectors to achieve maximum operational confidentiality without degrading core operating system integrity.

> * **Diagnostic Data & Telemetry Stripping**: Enforces Group Policy locks across Windows Data Collection (AllowTelemetry), halts device census routines, disables Feedback notifications, and stops background Microsoft Edge diagnostic processes.  
> * **AI & Screen Vectorization Neutralization**: Blocks Windows 11 Recall screen captures and semantic vector analysis (TurnOffRecall), isolates Windows Copilot context streams, and disables Windows AI data analysis pipelines.  
> * **Network & Protocol Hardening**: Disables obsolete local name resolution protocols (LLMNR and NetBIOS) to protect credentials against NetNTLM relay attacks, enforces system-wide DNS-over-HTTPS (EnableAutoDoh), and shuts down peer-to-peer Windows Update Delivery Optimization (DoSvc) seeding.  
> * **Input Privacy Protection**: Inhibits cloud synchronization of typing dictionaries, handwriting recognition samples, and cross-device cloud clipboard logging.  
> * **Digital Trace Sanitization**: Cleans unencrypted Jump Lists and Recent Documents histories, and prevents Windows Content Delivery Manager from silently downloading third-party promotional packages.

## **Getting Started**

Enigma is distributed both as a standalone portable executable for direct use and as an open-source Python codebase for auditing and manual execution.

### **Option 1: Standalone Binary (Recommended)**

For general use, download the pre-compiled binary. It requires no Python environment, external libraries, or manual setup:

> 1. Download the latest Enigma.exe executable from the **GitHub Releases** page or from the **Official Website**.  
> 2. Run Enigma.exe with administrative privileges.  
> 3. If executed under a standard user token, select the **Elevate Privilege** button in the header bar to trigger Windows User Account Control (UAC) elevation.

### **Option 2: Running from Source**

For developers, security researchers, and users who wish to inspect the execution pipeline directly:

#### **Requirements**

> * Windows 10 or Windows 11 (64-bit architecture)  
> * Python 3.10 or newer  
> * Microsoft Edge WebView2 Runtime (installed by default on modern Windows installations)

#### **Installation Steps**

Clone the repository and install the application dependencies:

&nbsp;

&nbsp;

&nbsp;

Bash

git clone https://github.com/username/enigma.git  
cd enigma  
pip install pywebview

Start the application interface:

&nbsp;

&nbsp;

&nbsp;

Bash

python main.py

## **Architectural Design**

The program is architected around a strict separation of engine operations, rule declarations, and state persistence:

> * **Engine Kernel (core.py)**: Interfaces directly with the Windows API through 64-bit Registry abstractions (KEY\_WOW64\_64KEY), the Service Control Manager (sc.exe), and scheduled task interfaces (schtasks.exe). Process actions and thread-safe logging are synchronized via standard synchronization locks.  
> * **Declarative Rules (rules.json)**: Contains structured rules defining system targets, expected secure values, severity ranks, and explicit shell or PowerShell actions for deep network mitigation.  
> * **Transactional State Storage (backup\_state.json)**: Preserves pre-remediation states—including original registry values, types (REG\_DWORD, REG\_SZ), and initial service startup modes (Automatic, Manual, Disabled)—within %APPDATA%\\Enigma.  
> * **Interface Layer**: A high-contrast desktop UI built with CSS grid and custom typography (Unbounded, Plus Jakarta Sans, and Space Mono), communicating asynchronously with the Python host via JSON-RPC.

## **State Management and Safety Guarantees**

Enigma rejects blind registry overrides and destructive terminal scripts. Before enforcing any mitigation:

> * The engine performs a non-destructive read against all target registry keys and system services.  
> * Missing keys are flagged distinctly from modified keys, ensuring that restoration does not leave orphaned values behind.  
> * Stopping a service records its active configuration mode, enabling an exact rollback rather than forcing services into an arbitrary default state.  
> * If policy application fails due to missing access rights or third-party locks, the transaction aborts and details are surfaced directly to the integrated console log.

## **License**

Enigma is distributed under the terms of the **GNU General Public License v3.0 (GPLv3)**. You are free to run, review, modify, and redistribute this software. Any derivative works or distributions that incorporate this codebase must remain open source under the same GPLv3 terms.