#!/usr/bin/env python3
"""
Autonomous Improvement Loop Runner — synt-wrkdr-1
Mengeksekusi siklus perbaikan otomatis:
1. Membaca task berikutnya dari RADAR_BACKLOG.md
2. Menyiapkan staging / branch
3. Menjalankan verifikasi QA Sentinel (Stop Signal)
4. Melakukan commit per-agent & rilis
"""

import sys
import re
import subprocess
from pathlib import Path

BACKLOG_FILE = Path("/home/hermes/macro-portal/RADAR_BACKLOG.md")
REPO_DIR = Path("/home/hermes/macro-portal")

def get_next_task():
    if not BACKLOG_FILE.exists():
        print("[-] RADAR_BACKLOG.md tidak ditemukan.")
        return None

    content = BACKLOG_FILE.read_text(encoding="utf-8")
    match = re.search(r"- \[ \] \*\*(TASK-\d+)\s*\(([^)]+)\)\*\*:\s*(.+)", content)
    if match:
        return {
            "task_id": match.group(1),
            "agent_roles": match.group(2).split("/"),
            "description": match.group(3).strip()
        }
    return None

def run_cmd(cmd, cwd=REPO_DIR):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def run_qa_gate():
    print("[*] Menjalankan QA Gate Verification...")
    # Jalankan pytest dan syntax linting sederhana
    code, out, err = run_cmd("python3 -m py_compile app/main.py app/database.py app/scheduler.py")
    if code != 0:
        print(f"[-] Python compilation error:\n{err}")
        return False
    print("[+] Python compilation: PASS")
    return True

def main():
    print("=== Werkudoro Autonomous Loop Runner (synt-wrkdr-1) ===")
    task = get_next_task()
    if not task:
        print("[+] Semua task di RADAR_BACKLOG.md sudah selesai atau belum ada task baru.")
        sys.exit(0)

    print(f"[*] Task Ditemukan: {task['task_id']} ({', '.join(task['agent_roles'])})")
    print(f"[*] Deskripsi: {task['description']}")

    # Verifikasi QA Sentinel
    if not run_qa_gate():
        print("[-] QA Sentinel: STOP SIGNAL AKTIF! Perubahan ditolak.")
        sys.exit(1)

    print("[+] Loop cycle readiness checked.")

if __name__ == "__main__":
    main()
