#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_roster_web.py

提供 Web API 與前端介面，讓使用者可編輯 roster.txt（onsite / WFH），
並同步重建 roster.ics。使用 selection.txt 作為候選同事名單。
"""

import os
import re
import shutil
import argparse
import base64
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, abort
from update_roster import parse_roster_txt, generate_ics_bytes  # 請確定 PYTHONPATH

# 檔案與資料夾路徑
ROSTER_TXT     = "roster.txt"
ROSTER_ICS     = "roster.ics"
SELECTION_TXT  = "selection.txt"
BACKUP_DIR     = "Backup"

app = Flask(__name__, template_folder="templates")

def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_file(path: str):
    """若 path 存在，備份到 Backup/YYYYMMDD_<basename>"""
    if os.path.exists(path):
        today = date.today().strftime("%Y%m%d")
        base = os.path.basename(path)
        backup_name = f"{today}_{base}"
        shutil.copy(path, os.path.join(BACKUP_DIR, backup_name))

def write_roster_txt(roster, path=ROSTER_TXT):
    """把 roster 物件覆蓋寫回 roster.txt"""
    lines = ["AI 整合報名:\n"]
    week = ["(星期一)","(星期二)","(星期三)","(星期四)","(星期五)","(星期六)","(星期日)"]
    for item in sorted(roster, key=lambda x: x["date"]):
        d = datetime.strptime(item["date"], "%Y/%m/%d").date()
        lines.append(f"{item['date']} {week[d.weekday()]}\n")
        ons = "、".join(item["onsite"]) if item["onsite"] else "無"
        wfh = "、".join(item["wfh"])    if item["wfh"]    else "無"
        lines.append(f"現場：{ons}\n")
        lines.append(f"WFH：{wfh}\n\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def rebuild_files():
    """備份並重建 roster.txt、roster.ics"""
    ensure_backup_dir()
    backup_file(ROSTER_TXT)
    backup_file(ROSTER_ICS)

    roster = parse_roster_txt(ROSTER_TXT)
    write_roster_txt(roster, ROSTER_TXT)

    ics = generate_ics_bytes(roster)
    with open(ROSTER_ICS, "wb") as f:
        f.write(ics)

def load_selection(path=SELECTION_TXT):
    """讀 selection.txt，回傳同事名單清單"""
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

# --- API 路由 ---

@app.route("/api/selection", methods=["GET"])
def api_selection():
    return jsonify(load_selection())

@app.route("/api/roster", methods=["GET"])
def api_list():
    return jsonify(parse_roster_txt(ROSTER_TXT))

@app.route("/api/roster", methods=["POST"])
def api_add():
    data = request.get_json()
    if not data or "date" not in data:
        abort(400)
    roster = parse_roster_txt(ROSTER_TXT)
    if any(r["date"] == data["date"] for r in roster):
        return jsonify({"error": "該日期已存在"}), 400
    roster.append({
        "date":   data["date"],
        "onsite": data.get("onsite", []),
        "wfh":    data.get("wfh", [])
    })
    write_roster_txt(roster)
    rebuild_files()
    return jsonify({"ok": True})

@app.route("/api/roster/<date_str>", methods=["PUT"])
def api_edit(date_str):
    data = request.get_json()
    roster = parse_roster_txt(ROSTER_TXT)
    found = False
    for r in roster:
        if r["date"] == date_str:
            r["onsite"] = data.get("onsite", [])
            r["wfh"]    = data.get("wfh", [])
            found = True
            break
    if not found:
        return jsonify({"error": "找不到該日期"}), 404
    write_roster_txt(roster)
    rebuild_files()
    return jsonify({"ok": True})

@app.route("/api/roster/<date_str>", methods=["DELETE"])
def api_del(date_str):
    roster = [r for r in parse_roster_txt(ROSTER_TXT) if r["date"] != date_str]
    write_roster_txt(roster)
    rebuild_files()
    return jsonify({"ok": True})

@app.route("/")
def index():
    return render_template("index.html")

# --- 啟動伺服器 ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)