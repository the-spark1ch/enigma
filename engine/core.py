import os
import sys
import json
import time
import shutil
import hashlib
import platform
import subprocess
import threading
from typing import Dict, List, Any, Optional

IS_WINDOWS = platform.system() == "Windows"

def get_resource_path(filename: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_dir, filename)
    if os.path.exists(candidate):
        return candidate
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def is_admin() -> bool:
    if IS_WINDOWS:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

def request_elevation():
    if IS_WINDOWS:
        try:
            import ctypes
            is_frozen = getattr(sys, "frozen", False)
            if is_frozen:
                target_bin = sys.executable
                params = subprocess.list2cmdline(sys.argv[1:])
                cwd = os.path.dirname(os.path.abspath(sys.executable))
            else:
                target_bin = sys.executable
                params = subprocess.list2cmdline(sys.argv)
                cwd = os.path.dirname(os.path.abspath(sys.argv[0]))

            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", target_bin, params, cwd, 1)
            if int(ret) > 32:
                sys.exit(0)
            return False
        except Exception:
            return False
    return False

def get_app_storage_dir() -> str:
    if IS_WINDOWS:
        base_dir = os.environ.get("APPDATA")
        if not base_dir:
            base_dir = os.path.expanduser("~")
        target_dir = os.path.join(base_dir, "Enigma")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME")
        if not base_dir:
            base_dir = os.path.expanduser("~/.config")
        target_dir = os.path.join(base_dir, "enigma")
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def get_storage_path() -> str:
    return os.path.join(get_app_storage_dir(), "backup_state.json")

def get_checksum_path() -> str:
    return os.path.join(get_app_storage_dir(), "backup_state.json.sha256")

def get_config_path() -> str:
    return os.path.join(get_app_storage_dir(), "config.json")

def compute_file_sha256(filepath: str) -> Optional[str]:
    if not os.path.exists(filepath):
        return None
    try:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

class PrivacyEngineAPI:
    def __init__(self):
        self._lock = threading.Lock()
        self._restore_point_attempted = False
        self.rules: List[Dict[str, Any]] = self._load_rules()
        self.audit_results: List[Dict[str, Any]] = []
        self.logs: List[str] = []
        self.backup_path = get_storage_path()
        self.checksum_path = get_checksum_path()
        self.backups: Dict[str, Any] = self._load_backups()

    def _load_rules(self) -> List[Dict[str, Any]]:
        rules_file = get_resource_path("rules.json")
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _load_backups(self) -> Dict[str, Any]:
        local_fallback = get_resource_path("backup_state.json")
        bak_file = self.backup_path + ".bak"

        if not os.path.exists(self.backup_path) and os.path.exists(local_fallback):
            try:
                shutil.copy2(local_fallback, self.backup_path)
            except Exception:
                pass

        if os.path.exists(self.backup_path):
            current_hash = compute_file_sha256(self.backup_path)

            if os.path.exists(self.checksum_path):
                try:
                    with open(self.checksum_path, "r", encoding="utf-8") as cf:
                        expected_hash = cf.read().strip()
                    if current_hash != expected_hash:
                        self.log("Integrity fault: backup_state.json SHA-256 mismatch detected.")
                        if os.path.exists(bak_file) and compute_file_sha256(bak_file) == expected_hash:
                            shutil.copy2(bak_file, self.backup_path)
                            self.log("State snapshot restored from verified backup replica.")
                except Exception as e:
                    self.log(f"Integrity check fault: {e}")
            else:
                if current_hash:
                    try:
                        with open(self.checksum_path, "w", encoding="utf-8") as cf:
                            cf.write(current_hash)
                    except Exception:
                        pass

            try:
                with open(self.backup_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"Failed to parse state snapshot: {e}")
                if os.path.exists(bak_file):
                    try:
                        with open(bak_file, "r", encoding="utf-8") as bf:
                            return json.load(bf)
                    except Exception:
                        pass
                return {}
        return {}

    def _save_backups(self):
        bak_file = self.backup_path + ".bak"
        try:
            with self._lock:
                tmp_path = self.backup_path + ".tmp"
                tmp_checksum = self.checksum_path + ".tmp"

                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.backups, f, indent=2, ensure_ascii=False)

                digest = compute_file_sha256(tmp_path)
                if digest:
                    with open(tmp_checksum, "w", encoding="utf-8") as cf:
                        cf.write(digest)

                if os.path.exists(self.backup_path):
                    shutil.copy2(self.backup_path, bak_file)

                os.replace(tmp_path, self.backup_path)
                if digest and os.path.exists(tmp_checksum):
                    os.replace(tmp_checksum, self.checksum_path)
        except Exception as e:
            self.log(f"Failed to write state snapshot: {e}")

    def _is_enterprise_edition(self) -> bool:
        if not IS_WINDOWS:
            return True
        raw = self._get_registry_raw("HKEY_LOCAL_MACHINE", "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", "EditionID")
        if raw.get("exists") and raw.get("value"):
            edition = str(raw["value"]).lower()
            for kw in ["enterprise", "education", "server", "iot"]:
                if kw in edition:
                    return True
        return False

    def _get_recommended_reg_value(self, entry: Dict[str, Any]) -> Any:
        if entry.get("value") == "AllowTelemetry":
            return 0 if self._is_enterprise_edition() else 1
        return entry.get("recommended")

    def create_restore_point(self, description: str = "Enigma Baseline Snapshot") -> bool:
        if not IS_WINDOWS or self._restore_point_attempted:
            return False
        self._restore_point_attempted = True
        self.log(f"Generating system restore point: {description}...")
        try:
            self._set_windows_registry(
                "HKEY_LOCAL_MACHINE",
                "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\SystemRestore",
                "SystemRestorePointCreationFrequency",
                0,
                "dword"
            )
            cmd = f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'"
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=25
            )
            if res.returncode == 0:
                self.log("System restore point generated successfully.")
                return True
            else:
                self.log("System restore point creation skipped or unavailable on this system.")
                return False
        except subprocess.TimeoutExpired:
            self.log("System restore point creation timed out.")
            return False
        except Exception as e:
            self.log(f"System restore point failed: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        cfg_path = get_config_path()
        try:
            with self._lock:
                tmp_path = cfg_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, cfg_path)
            return {"success": True}
        except Exception as e:
            self.log(f"Config write error: {e}")
            return {"success": False, "error": str(e)}

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        with self._lock:
            self.logs.append(entry)
        print(f"[Enigma] {entry}")

    def get_system_overview(self) -> Dict[str, Any]:
        edition = ""
        build_num = ""
        display_version = ""
        if IS_WINDOWS:
            raw_prod = self._get_registry_raw("HKEY_LOCAL_MACHINE", "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", "ProductName")
            if raw_prod.get("exists"):
                edition = str(raw_prod["value"])
            raw_build = self._get_registry_raw("HKEY_LOCAL_MACHINE", "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", "CurrentBuild")
            if raw_build.get("exists"):
                build_num = str(raw_build["value"])
            raw_ver = self._get_registry_raw("HKEY_LOCAL_MACHINE", "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", "DisplayVersion")
            if raw_ver.get("exists"):
                display_version = str(raw_ver["value"])

            try:
                if build_num and int(build_num) >= 22000:
                    edition = edition.replace("Windows 10", "Windows 11")
            except ValueError:
                pass

        if IS_WINDOWS:
            try:
                if build_num and int(build_num) >= 22000:
                    os_family = "Windows 11"
                else:
                    os_family = f"Windows {platform.release()}"
            except ValueError:
                os_family = f"{platform.system()} {platform.release()}"
        else:
            os_family = f"{platform.system()} {platform.release()}"

        return {
            "os": os_family,
            "edition": edition or os_family,
            "build": build_num or platform.version(),
            "display_version": display_version,
            "architecture": platform.machine(),
            "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "Unknown"),
            "hostname": platform.node(),
            "is_admin": is_admin(),
            "python_version": platform.python_version()
        }

    def request_admin(self) -> Dict[str, Any]:
        self.log("Invoking administrative elevation request...")
        res = request_elevation()
        return {"success": res}

    def _get_registry_raw(self, hive_name: str, subkey: str, value_name: str) -> Dict[str, Any]:
        if not IS_WINDOWS:
            return {"exists": False, "value": None, "type": None}
        try:
            import winreg
            hive = getattr(winreg, hive_name)
            access_flags = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(hive, subkey, 0, access_flags) as key:
                val, val_type = winreg.QueryValueEx(key, value_name)
                return {"exists": True, "value": val, "type": val_type}
        except Exception:
            return {"exists": False, "value": None, "type": None}

    def _check_windows_registry(self, hive_name: str, subkey: str, value_name: str, expected_safe: Any) -> bool:
        raw = self._get_registry_raw(hive_name, subkey, value_name)
        if not raw["exists"]:
            return False
        return raw["value"] == expected_safe

    def _set_windows_registry(self, hive_name: str, subkey: str, value_name: str, value: Any, val_type_str: str = "dword") -> bool:
        if not IS_WINDOWS:
            return False
        try:
            import winreg
            hive = getattr(winreg, hive_name)
            access_flags = winreg.KEY_WRITE | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.CreateKeyEx(hive, subkey, 0, access_flags) as k:
                v_type = winreg.REG_DWORD if val_type_str == "dword" else winreg.REG_SZ
                winreg.SetValueEx(k, value_name, 0, v_type, value)
            return True
        except PermissionError:
            self.log(f"Access denied writing registry: {hive_name}\\{subkey}")
            return False
        except Exception as e:
            self.log(f"Registry write fault {subkey}\\{value_name}: {e}")
            return False

    def _delete_windows_registry_value(self, hive_name: str, subkey: str, value_name: str) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            import winreg
            hive = getattr(winreg, hive_name)
            access_flags = winreg.KEY_SET_VALUE | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(hive, subkey, 0, access_flags) as k:
                winreg.DeleteValue(k, value_name)
            return True
        except Exception:
            return False

    def _get_netbios_interfaces(self) -> List[str]:
        if not IS_WINDOWS:
            return []
        interfaces = []
        try:
            import winreg
            base_key = r"SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
            access_flags = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key, 0, access_flags) as k:
                idx = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(k, idx)
                        interfaces.append(subkey_name)
                        idx += 1
                    except OSError:
                        break
        except Exception:
            pass
        return interfaces

    def _check_netbios_disabled(self) -> bool:
        if not IS_WINDOWS:
            return True
        interfaces = self._get_netbios_interfaces()
        if not interfaces:
            return True
        for iface in interfaces:
            subkey = f"SYSTEM\\CurrentControlSet\\Services\\NetBT\\Parameters\\Interfaces\\{iface}"
            raw = self._get_registry_raw("HKEY_LOCAL_MACHINE", subkey, "NetbiosOptions")
            if not raw["exists"] or raw["value"] != 2:
                return False
        return True

    def _set_netbios_mode(self, mode: int = 2) -> bool:
        if not IS_WINDOWS:
            return False
        interfaces = self._get_netbios_interfaces()
        success = True
        for iface in interfaces:
            subkey = f"SYSTEM\\CurrentControlSet\\Services\\NetBT\\Parameters\\Interfaces\\{iface}"
            res = self._set_windows_registry("HKEY_LOCAL_MACHINE", subkey, "NetbiosOptions", mode, "dword")
            if not res:
                success = False
        return success

    def _backup_netbios_state(self) -> List[Dict[str, Any]]:
        if not IS_WINDOWS:
            return []
        records = []
        interfaces = self._get_netbios_interfaces()
        for iface in interfaces:
            subkey = f"SYSTEM\\CurrentControlSet\\Services\\NetBT\\Parameters\\Interfaces\\{iface}"
            raw = self._get_registry_raw("HKEY_LOCAL_MACHINE", subkey, "NetbiosOptions")
            records.append({
                "interface": iface,
                "prev_exists": raw["exists"],
                "prev_value": raw["value"],
                "prev_type": raw["type"]
            })
        return records

    def _restore_netbios_state(self, records: List[Dict[str, Any]]):
        if not IS_WINDOWS:
            return
        for rec in records:
            iface = rec["interface"]
            subkey = f"SYSTEM\\CurrentControlSet\\Services\\NetBT\\Parameters\\Interfaces\\{iface}"
            if rec["prev_exists"] and rec["prev_value"] is not None:
                self._set_windows_registry("HKEY_LOCAL_MACHINE", subkey, "NetbiosOptions", rec["prev_value"], "dword")
            else:
                self._delete_windows_registry_value("HKEY_LOCAL_MACHINE", subkey, "NetbiosOptions")

    def _check_service_disabled(self, service_name: str) -> bool:
        if not IS_WINDOWS:
            return True
        subkey = f"SYSTEM\\CurrentControlSet\\Services\\{service_name}"
        raw = self._get_registry_raw("HKEY_LOCAL_MACHINE", subkey, "Start")
        if not raw["exists"]:
            return True
        return raw["value"] == 4

    def _get_service_start_mode(self, service_name: str) -> Optional[int]:
        if not IS_WINDOWS:
            return None
        subkey = f"SYSTEM\\CurrentControlSet\\Services\\{service_name}"
        raw = self._get_registry_raw("HKEY_LOCAL_MACHINE", subkey, "Start")
        if raw["exists"] and isinstance(raw["value"], int):
            return raw["value"]
        return None

    def _disable_service(self, service_name: str):
        if not IS_WINDOWS:
            return
        subkey = f"SYSTEM\\CurrentControlSet\\Services\\{service_name}"
        self._set_windows_registry("HKEY_LOCAL_MACHINE", subkey, "Start", 4, "dword")
        try:
            subprocess.run(
                ["sc", "stop", service_name],
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=7
            )
        except subprocess.TimeoutExpired:
            self.log(f"Service termination timeout: {service_name}")
        except Exception:
            pass

    def _restore_service(self, service_name: str, start_mode: int):
        if not IS_WINDOWS:
            return
        subkey = f"SYSTEM\\CurrentControlSet\\Services\\{service_name}"
        self._set_windows_registry("HKEY_LOCAL_MACHINE", subkey, "Start", start_mode, "dword")
        if start_mode in (2, 3):
            try:
                subprocess.run(
                    ["sc", "start", service_name],
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except Exception:
                pass

    def _check_scheduled_tasks_disabled(self, task_paths: List[str]) -> bool:
        if not IS_WINDOWS:
            return True
        for task in task_paths:
            try:
                output = subprocess.check_output(
                    ["schtasks", "/query", "/tn", task, "/fo", "list"],
                    creationflags=0x08000000,
                    stderr=subprocess.STDOUT,
                    timeout=5
                ).decode(errors="ignore")
                if "Ready" in output or "Running" in output:
                    return False
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue
        return True

    def _disable_scheduled_tasks(self, task_paths: List[str]):
        if not IS_WINDOWS:
            return
        for task in task_paths:
            try:
                subprocess.run(
                    ["schtasks", "/change", "/tn", task, "/disable"],
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except subprocess.TimeoutExpired:
                self.log(f"Task deactivation timeout: {task}")
            except Exception as e:
                self.log(f"Unable to disable scheduled task {task}: {e}")

    def _enable_scheduled_tasks(self, task_paths: List[str]):
        if not IS_WINDOWS:
            return
        for task in task_paths:
            try:
                subprocess.run(
                    ["schtasks", "/change", "/tn", task, "/enable"],
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except subprocess.TimeoutExpired:
                self.log(f"Task activation timeout: {task}")
            except Exception as e:
                self.log(f"Unable to restore scheduled task {task}: {e}")

    def _clean_directory(self, path_str: str):
        expanded = os.path.expandvars(path_str)
        if os.path.exists(expanded):
            try:
                items = os.listdir(expanded)
            except Exception:
                return

            for item in items:
                p = os.path.join(expanded, item)
                try:
                    if os.path.isfile(p) or os.path.islink(p):
                        os.unlink(p)
                    elif os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                except Exception:
                    continue

    def _evaluate_vulnerability_status(self, issue: Dict[str, Any]) -> bool:
        if not IS_WINDOWS:
            return issue.get("status") == "vulnerable"

        if "registry_entries" in issue:
            for entry in issue["registry_entries"]:
                expected = self._get_recommended_reg_value(entry)
                if not self._check_windows_registry(entry["hive"], entry["key"], entry["value"], expected):
                    return True

        if issue.get("netbios_mitigation"):
            if not self._check_netbios_disabled():
                return True

        if "services" in issue:
            for s in issue["services"]:
                if not self._check_service_disabled(s):
                    return True

        if "tasks" in issue:
            if not self._check_scheduled_tasks_disabled(issue["tasks"]):
                return True

        return False

    def start_full_scan(self) -> Dict[str, Any]:
        self.log(f"Running comprehensive audit over {len(self.rules)} rules...")
        analyzed_issues = []
        for item in self.rules:
            issue = dict(item)
            is_vuln = self._evaluate_vulnerability_status(issue)
            issue["status"] = "vulnerable" if is_vuln else "secure"
            analyzed_issues.append(issue)

        with self._lock:
            self.audit_results = analyzed_issues
            logs_snapshot = list(self.logs[-30:])

        vulnerable_items = [x for x in analyzed_issues if x["status"] == "vulnerable"]
        critical_count = sum(1 for x in vulnerable_items if x["severity"] == "critical")

        self.log(f"Audit completed. Found {len(vulnerable_items)} vectors ({critical_count} critical).")
        return {
            "success": True,
            "issues": analyzed_issues,
            "vulnerable_count": len(vulnerable_items),
            "critical_count": critical_count,
            "total_count": len(analyzed_issues),
            "logs": logs_snapshot
        }

    def _backup_issue_state(self, target: Dict[str, Any]):
        issue_id = target["id"]
        if issue_id in self.backups:
            return

        backup_record: Dict[str, Any] = {"registry": [], "services": []}

        if "registry_entries" in target:
            for entry in target["registry_entries"]:
                raw = self._get_registry_raw(entry["hive"], entry["key"], entry["value"])
                backup_record["registry"].append({
                    "hive": entry["hive"],
                    "key": entry["key"],
                    "value": entry["value"],
                    "type": entry.get("type", "dword"),
                    "prev_exists": raw["exists"],
                    "prev_value": raw["value"],
                    "prev_type": raw["type"]
                })

        if target.get("netbios_mitigation"):
            backup_record["netbios"] = self._backup_netbios_state()

        if "services" in target:
            for s in target["services"]:
                start_mode = self._get_service_start_mode(s)
                backup_record["services"].append({
                    "name": s,
                    "prev_start": start_mode
                })

        self.backups[issue_id] = backup_record
        self._save_backups()

    def fix_issue(self, issue_id: str) -> Dict[str, Any]:
        with self._lock:
            target = next((x for x in self.audit_results if x["id"] == issue_id), None)
        if not target:
            return {"success": False, "error": "Vector profile not found"}

        if not self._restore_point_attempted:
            self.create_restore_point("Enigma Pre-Remediation Snapshot")

        self.log(f"Hardening vector: {target['title']}")
        self._backup_issue_state(target)

        if IS_WINDOWS:
            if "registry_entries" in target:
                for entry in target["registry_entries"]:
                    rec_val = self._get_recommended_reg_value(entry)
                    self._set_windows_registry(
                        entry["hive"], entry["key"], entry["value"], rec_val, entry.get("type", "dword")
                    )

            if target.get("netbios_mitigation"):
                self._set_netbios_mode(2)

            if "services" in target:
                for s in target["services"]:
                    self._disable_service(s)

            if "tasks" in target:
                self._disable_scheduled_tasks(target["tasks"])

            if "directory_cleanups" in target:
                for d in target["directory_cleanups"]:
                    self._clean_directory(d)

        is_still_vulnerable = self._evaluate_vulnerability_status(target)
        if is_still_vulnerable:
            target["status"] = "vulnerable"
            self.log(f"Failed to harden: {target['title']}. Insufficient rights.")
            with self._lock:
                logs_snapshot = list(self.logs[-30:])
            return {
                "success": False,
                "error": "Failed to enforce policies. Elevation required.",
                "issue_id": issue_id,
                "logs": logs_snapshot
            }

        target["status"] = "secure"
        self.log(f"Successfully secured: {target['title']}")

        with self._lock:
            vulnerable_items = [x for x in self.audit_results if x["status"] == "vulnerable"]
            logs_snapshot = list(self.logs[-30:])
        critical_count = sum(1 for x in vulnerable_items if x["severity"] == "critical")

        return {
            "success": True,
            "issue_id": issue_id,
            "vulnerable_count": len(vulnerable_items),
            "critical_count": critical_count,
            "logs": logs_snapshot
        }

    def revert_issue(self, issue_id: str) -> Dict[str, Any]:
        with self._lock:
            target = next((x for x in self.audit_results if x["id"] == issue_id), None)
        if not target:
            return {"success": False, "error": "Vector profile not found"}

        backup_record = self.backups.get(issue_id)
        if not backup_record:
            return {"success": False, "error": "No backup snapshot exists for this vector"}

        self.log(f"Reverting vector: {target['title']}")

        if IS_WINDOWS:
            for reg in backup_record.get("registry", []):
                if reg["prev_exists"]:
                    self._set_windows_registry(reg["hive"], reg["key"], reg["value"], reg["prev_value"], reg["type"])
                else:
                    self._delete_windows_registry_value(reg["hive"], reg["key"], reg["value"])

            if "netbios" in backup_record:
                self._restore_netbios_state(backup_record["netbios"])

            for svc in backup_record.get("services", []):
                if svc["prev_start"] is not None:
                    self._restore_service(svc["name"], svc["prev_start"])

            if "tasks" in target:
                self._enable_scheduled_tasks(target["tasks"])

        is_vuln = self._evaluate_vulnerability_status(target)
        target["status"] = "vulnerable" if is_vuln else "secure"

        del self.backups[issue_id]
        self._save_backups()

        with self._lock:
            vulnerable_items = [x for x in self.audit_results if x["status"] == "vulnerable"]
            logs_snapshot = list(self.logs[-30:])
        critical_count = sum(1 for x in vulnerable_items if x["severity"] == "critical")

        self.log(f"Reversion finished: {target['title']}")
        return {
            "success": True,
            "issue_id": issue_id,
            "status": target["status"],
            "vulnerable_count": len(vulnerable_items),
            "critical_count": critical_count,
            "logs": logs_snapshot
        }

    def fix_all_vulnerabilities(self, issue_ids: List[str]) -> Dict[str, Any]:
        self.log(f"Commencing batch remediation ({len(issue_ids)} vectors)...")
        if not self._restore_point_attempted:
            self.create_restore_point("Enigma Batch Remediation Snapshot")

        success_count = 0
        for i_id in issue_ids:
            res = self.fix_issue(i_id)
            if res.get("success"):
                success_count += 1

        with self._lock:
            vulnerable_items = [x for x in self.audit_results if x["status"] == "vulnerable"]
            audit_snapshot = list(self.audit_results)
            logs_snapshot = list(self.logs[-30:])
        critical_count = sum(1 for x in vulnerable_items if x["severity"] == "critical")
        self.log(f"Batch execution completed: {success_count}/{len(issue_ids)} resolved.")

        return {
            "success": True,
            "remediated_count": success_count,
            "issues": audit_snapshot,
            "vulnerable_count": len(vulnerable_items),
            "critical_count": critical_count,
            "logs": logs_snapshot
        }

    def get_logs(self) -> List[str]:
        with self._lock:
            return list(self.logs[-30:])
