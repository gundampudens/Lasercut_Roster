#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_roster.py

讀取同目錄下的 roster.txt，產生 zero‐duration 的 roster.ics（事件開始即結束），並推送到 GitHub Repo
(預設適用於 gundampudens/Lasercut_Roster，main 分支)
支持從環境變數或 --token CLI 參數讀取 PAT
更新前自動將舊的 roster.ics、roster.txt 備份到本機 Backup 資料夾，
檔名分別為 roster_YYYYMMDD.ics / roster_YYYYMMDD.txt
"""

import os
import re
import shutil
import argparse
import base64
from datetime import datetime, date, time
import pytz
from icalendar import Calendar, Event
from github import Github, Auth

# 可透過 CLI 或環境變數覆寫的預設值
DEFAULT_REPO       = "gundampudens/Lasercut_Roster"
DEFAULT_BRANCH     = "main"
DEFAULT_ICS_PATH   = "roster.ics"
DEFAULT_COMMIT_MSG = "Auto-update roster.ics"
BACKUP_DIR         = "Backup"

def parse_roster_txt(path: str):
    """
    解析 roster.txt，返回：
      [
        {"date":"YYYY/MM/DD", "onsite":[...], "wfh":[...]},
        ...
      ]
    支援：
      - 首行為標題，自動丟棄
      - 區塊以空白行分隔
      - 支援「日期: 」或直接「YYYY/MM/DD」
      - 現場、WFH 行順序可調、冒號前後可有空白
      - 名單以半形逗號、全形頓號、或空白分隔
      - WFH: 無 或 空白 表示沒人
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # 丟掉第一行
    text = re.sub(r"^.*\n", "", text, count=1)
    blocks = re.split(r"\n\s*\n", text.strip())
    roster = []

    for blk in blocks:
        lines = [l.strip() for l in blk.splitlines() if l.strip()]
        if not lines:
            continue

        # 找日期
        date_str = None
        for l in lines:
            m = re.search(r"(\d{4}/\d{2}/\d{2})", l)
            if m:
                date_str = m.group(1)
                break
        if not date_str:
            continue

        onsite = []
        wfh = []
        for l in lines:
            if re.match(r"^現場\s*[：:]", l):
                names = re.sub(r"^現場\s*[：:]\s*", "", l)
                onsite = [n.strip() for n in re.split(r"[,\s、]+", names) if n.strip()]
            elif re.match(r"^WFH\s*[：:]", l, re.IGNORECASE):
                names = re.sub(r"^WFH\s*[：:]\s*", "", l).strip()
                if names and names != "無":
                    wfh = [n.strip() for n in re.split(r"[,\s、]+", names) if n.strip()]

        roster.append({
            "date": date_str,
            "onsite": onsite,
            "wfh": wfh
        })

    return roster

def generate_ics_bytes(roster: list) -> bytes:
    """
    依排班產生 Calendar：
      - 日間 on‐site：12:00，zero‐duration，標題【日間】
      - 晚間 on‐site：19:00，zero‐duration，標題【晚間】
      - WFH：20:00，zero‐duration，標題【WFH】
    """
    cal = Calendar()
    cal.add("prodid", "-//Lasercut Roster//example.com//")
    cal.add("version", "2.0")
    tz = pytz.timezone("Asia/Hong_Kong")

    for item in roster:
        d = datetime.strptime(item["date"], "%Y/%m/%d").date()

        # 定義三個時刻
        dt_day   = tz.localize(datetime.combine(d, time(hour=12)))
        dt_eve   = tz.localize(datetime.combine(d, time(hour=19)))
        dt_wfh   = tz.localize(datetime.combine(d, time(hour=20)))

        # 拆分 onsite 日間 vs 晚間
        onsite_day = []
        onsite_eve = []
        for name in item["onsite"]:
            if "(日間)" in name:
                onsite_day.append(name.replace("(日間)", "").strip())
            else:
                onsite_eve.append(name)

        def make_event(label: str, names: list, dt: datetime):
            ev = Event()
            ev.add("summary", f"【{label}】" + "、".join(names))
            ev.add("dtstart", dt)
            # zero-duration：dtend 同 dtstart
            ev.add("dtend", dt)
            ev.add("description", f"人數：{len(names)}")
            return ev

        if onsite_day:
            cal.add_component(make_event("日間", onsite_day, dt_day))
        if onsite_eve:
            cal.add_component(make_event("晚間", onsite_eve, dt_eve))
        if item["wfh"]:
            cal.add_component(make_event("WFH", item["wfh"], dt_wfh))

    return cal.to_ical()

def push_to_github(ics_bytes: bytes, repo_name: str, path_in_repo: str,
                   branch: str, commit_msg: str, token: str):
    """
    備份遠端 roster.ics，然後更新或新建
    """
    print(f"→ Token 前 4 位: {token[:4]}{'*'*(len(token)-4)}")
    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    base, ext = os.path.splitext(path_in_repo)
    backup_name = f"{base}_{today}{ext}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        contents = repo.get_contents(path_in_repo, ref=branch)
        old = base64.b64decode(contents.content)
        with open(backup_path, "wb") as bf:
            bf.write(old)
        print(f"→ 已將遠端檔案備份至：{backup_path}")

        repo.update_file(
            path    = contents.path,
            message = commit_msg,
            content = ics_bytes.decode("utf-8"),
            sha     = contents.sha,
            branch  = branch
        )
        print(f"✅ 更新成功：{repo_name}@{branch}/{path_in_repo}")
    except Exception:
        repo.create_file(
            path    = path_in_repo,
            message = commit_msg,
            content = ics_bytes.decode("utf-8"),
            branch  = branch
        )
        print(f"✅ 建立成功：{repo_name}@{branch}/{path_in_repo}")

def main():
    p = argparse.ArgumentParser(
        description="同步 roster.txt 到 GitHub 的 roster.ics（zero‐duration），並備份舊檔"
    )
    p.add_argument("-i","--input", default="roster.txt", help="排班文字檔路徑")
    p.add_argument("-r","--repo",  default=DEFAULT_REPO,   help="GitHub repo (user/name)")
    p.add_argument("-p","--path",  default=DEFAULT_ICS_PATH,help="Repo 中的 ICS 路徑")
    p.add_argument("-b","--branch",default=DEFAULT_BRANCH, help="分支名稱")
    p.add_argument("-m","--msg",   default=DEFAULT_COMMIT_MSG,help="Commit 訊息")
    p.add_argument("-t","--token", default=None,            help="GitHub Token（或於環境變數 GITHUB_TOKEN）")
    args = p.parse_args()

    # 備份 roster.txt
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    base, ext = os.path.splitext(os.path.basename(args.input))
    backup_txt = f"{base}_{today}{ext}"
    backup_txt_path = os.path.join(BACKUP_DIR, backup_txt)
    shutil.copy(args.input, backup_txt_path)
    print(f"→ 已將排班檔備份至：{backup_txt_path}")

    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("❌ 必須提供 --token 或設定環境變數 GITHUB_TOKEN")

    roster   = parse_roster_txt(args.input)
    ics_data = generate_ics_bytes(roster)
    push_to_github(
        ics_bytes    = ics_data,
        repo_name    = args.repo,
        path_in_repo = args.path,
        branch       = args.branch,
        commit_msg   = args.msg,
        token        = token
    )

if __name__ == "__main__":
    main()