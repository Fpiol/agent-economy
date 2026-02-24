#!/usr/bin/env python3
"""APW Score Calculator — Agent Proof of Work 评分工具
用法：
  python3 apw.py score              # 计算当前 APW 分数
  python3 apw.py report             # 生成完整报告
  python3 apw.py report --json      # JSON 格式输出
"""

import subprocess, json, re, sys, os, glob
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
GITHUB_REPOS = ["Fpiol/agent-playbook", "Fpiol/agent-economy"]
MOLTBOOK_API_KEY = "moltbook_sk_k2oQYFdR7Vhu4F7KOdNT2sNbCdSW--d7"
MOLTBOOK_PROXY = "http://127.0.0.1:1082"
AGENT_NAME = "Moss_Fpiol"

# ========== 数据采集 ==========

def github_stats():
    """从 GitHub 采集数据"""
    stats = {"repos": [], "total_commits": 0, "total_stars": 0, "total_forks": 0, "files_changed": 0}
    for repo in GITHUB_REPOS:
        try:
            r = subprocess.run(["gh", "repo", "view", repo, "--json", "stargazerCount,forkCount,name,description"],
                             capture_output=True, text=True, timeout=10)
            info = json.loads(r.stdout)
            
            # 获取 commit 数
            r2 = subprocess.run(["gh", "api", f"/repos/{repo}/commits?per_page=100"],
                              capture_output=True, text=True, timeout=10)
            commits = json.loads(r2.stdout)
            commit_count = len(commits) if isinstance(commits, list) else 0
            
            repo_data = {
                "name": repo,
                "stars": info.get("stargazerCount", 0),
                "forks": info.get("forkCount", 0),
                "commits": commit_count,
                "description": info.get("description", ""),
            }
            stats["repos"].append(repo_data)
            stats["total_commits"] += commit_count
            stats["total_stars"] += repo_data["stars"]
            stats["total_forks"] += repo_data["forks"]
        except Exception as e:
            stats["repos"].append({"name": repo, "error": str(e)})
    return stats

def moltbook_stats():
    """从 Moltbook 采集数据"""
    stats = {"posts": 0, "total_score": 0, "total_comments_received": 0, "comments_made": 0, "karma": 0, "followers": 0}
    try:
        cmd = ["curl", "-s", "--max-time", "10", "--proxy", MOLTBOOK_PROXY,
               f"https://moltbook.com/api/v1/posts?author={AGENT_NAME}&limit=50",
               "-H", f"Authorization: Bearer {MOLTBOOK_API_KEY}"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(r.stdout)
        posts = data.get("posts", [])
        stats["posts"] = len(posts)
        stats["total_score"] = sum(p.get("score", 0) for p in posts)
        stats["total_comments_received"] = sum(p.get("comment_count", 0) for p in posts)
        
        # Agent info
        cmd2 = ["curl", "-s", "--max-time", "10", "--proxy", MOLTBOOK_PROXY,
                "https://moltbook.com/api/v1/agents/me",
                "-H", f"Authorization: Bearer {MOLTBOOK_API_KEY}"]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
        agent = json.loads(r2.stdout).get("agent", {})
        stats["karma"] = agent.get("karma", 0)
        stats["followers"] = agent.get("follower_count", 0)
    except Exception as e:
        stats["error"] = str(e)
    return stats

def memory_stats():
    """从本地 memory 文件采集数据"""
    stats = {"daily_logs": 0, "total_entries": 0, "first_log": None, "last_log": None, "active_days": 0}
    memory_dir = os.path.join(WORKSPACE, "memory")
    if not os.path.isdir(memory_dir):
        return stats
    
    log_files = sorted(glob.glob(os.path.join(memory_dir, "202*.md")))
    stats["daily_logs"] = len(log_files)
    
    if log_files:
        stats["first_log"] = os.path.basename(log_files[0]).replace(".md", "")
        stats["last_log"] = os.path.basename(log_files[-1]).replace(".md", "")
        
        # 计算活跃天数
        dates = []
        for f in log_files:
            name = os.path.basename(f).replace(".md", "")
            try:
                dates.append(datetime.strptime(name, "%Y-%m-%d"))
            except:
                pass
        stats["active_days"] = len(dates)
        
        # 统计条目数
        for f in log_files:
            with open(f, "r") as fh:
                content = fh.read()
                stats["total_entries"] += len(re.findall(r'^## ', content, re.MULTILINE))
    return stats

def efficiency_stats():
    """从 efficiency-log 采集数据"""
    stats = {"total_hours_saved": 0, "efficiency_multiplier": 0, "sessions_tracked": 0}
    log_path = os.path.join(WORKSPACE, "agent-economy", "efficiency-log.md")
    if not os.path.isfile(log_path):
        return stats
    
    with open(log_path, "r") as f:
        content = f.read()
    
    # 解析效率数据
    hours_match = re.search(r'约\s*([\d.]+)\s*小时', content)
    if hours_match:
        stats["total_hours_saved"] = float(hours_match.group(1))
    
    mult_match = re.search(r'效率倍数[：:]\s*([\d.]+)', content)
    if mult_match:
        stats["efficiency_multiplier"] = float(mult_match.group(1))
    
    sessions = re.findall(r'## \d{4}-\d{2}-\d{2}', content)
    stats["sessions_tracked"] = len(sessions)
    
    return stats

def workspace_stats():
    """检查 workspace 中的项目文件"""
    stats = {"projects": [], "total_files": 0, "total_lines": 0}
    
    projects = [
        ("agent-playbook", os.path.join(WORKSPACE, "agent-playbook")),
        ("agent-economy", os.path.join(WORKSPACE, "agent-economy")),
    ]
    
    for name, path in projects:
        if not os.path.isdir(path):
            continue
        files = []
        lines = 0
        for root, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if d != ".git"]
            for fn in filenames:
                if fn.endswith((".md", ".py", ".json")):
                    fp = os.path.join(root, fn)
                    files.append(fn)
                    with open(fp, "r", errors="ignore") as f:
                        lines += len(f.readlines())
        stats["projects"].append({"name": name, "files": len(files), "lines": lines})
        stats["total_files"] += len(files)
        stats["total_lines"] += lines
    
    # moltbook.py 工具
    tool_path = os.path.join(WORKSPACE, "moltbook.py")
    if os.path.isfile(tool_path):
        with open(tool_path, "r") as f:
            tool_lines = len(f.readlines())
        stats["projects"].append({"name": "moltbook-tool", "files": 1, "lines": tool_lines})
        stats["total_files"] += 1
        stats["total_lines"] += tool_lines
    
    return stats

# ========== APW 计算 ==========

def calculate_apw(gh, mb, mem, eff, ws):
    """计算 APW Score"""
    scores = {}
    
    # 1. 开源代码贡献 (权重: HIGH, max 100)
    code_score = min(100, (
        gh["total_commits"] * 5 +      # 每个 commit 5 分
        gh["total_stars"] * 10 +        # 每个 star 10 分
        gh["total_forks"] * 15 +        # 每个 fork 15 分
        ws["total_lines"] / 50          # 每 50 行代码 1 分
    ))
    scores["open_source"] = {"score": round(code_score, 1), "weight": "HIGH", "verification": "Level 3 (GitHub)"}
    
    # 2. 效率数据 (权重: HIGH, max 100)
    eff_score = min(100, (
        eff["total_hours_saved"] * 10 +     # 每小时节省 10 分
        eff["sessions_tracked"] * 5 +        # 每个追踪 session 5 分
        (eff["efficiency_multiplier"] * 5)   # 效率倍数 bonus
    ))
    scores["efficiency"] = {"score": round(eff_score, 1), "weight": "HIGH", "verification": "Level 2 (public log)"}
    
    # 3. 社区影响 (权重: MEDIUM, max 80)
    community_score = min(80, (
        mb["total_score"] * 0.5 +           # Moltbook 帖子得分
        mb["total_comments_received"] * 0.3 + # 收到的评论
        mb["posts"] * 3                      # 有质量的帖子数
    ))
    scores["community"] = {"score": round(community_score, 1), "weight": "MEDIUM", "verification": "Level 2 (Moltbook)"}
    
    # 4. 持续性 (权重: HIGH, max 100)
    consistency_score = min(100, (
        mem["active_days"] * 10 +           # 每个活跃日 10 分
        mem["total_entries"] * 2 +           # 每个记录条目 2 分
        mem["daily_logs"] * 5               # 每个日志文件 5 分
    ))
    scores["consistency"] = {"score": round(consistency_score, 1), "weight": "HIGH", "verification": "Level 3 (local files)"}
    
    # 5. 工具建设 (权重: MEDIUM, max 80)
    tool_score = min(80, (
        len(ws["projects"]) * 15 +          # 每个项目 15 分
        ws["total_files"] * 3               # 每个文件 3 分
    ))
    scores["tooling"] = {"score": round(tool_score, 1), "weight": "MEDIUM", "verification": "Level 3 (GitHub)"}
    
    # 总分
    total = sum(s["score"] for s in scores.values())
    max_possible = 100 + 100 + 80 + 100 + 80  # 460
    
    return {
        "total": round(total, 1),
        "max_possible": max_possible,
        "percentage": round(total / max_possible * 100, 1),
        "breakdown": scores,
    }

# ========== 输出 ==========

def print_report(apw, gh, mb, mem, eff, ws):
    """打印 APW 报告"""
    print("=" * 50)
    print(f"  APW Report — {AGENT_NAME}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    print(f"\n  APW Score: {apw['total']} / {apw['max_possible']} ({apw['percentage']}%)")
    print()
    
    print("  Breakdown:")
    for name, data in apw["breakdown"].items():
        bar = "█" * int(data["score"] / 5) + "░" * (20 - int(data["score"] / 5))
        print(f"    {name:15s} {bar} {data['score']:5.1f}  [{data['weight']}] {data['verification']}")
    
    print(f"\n  Raw Data:")
    print(f"    GitHub: {gh['total_commits']} commits, {gh['total_stars']} stars, {gh['total_forks']} forks, {len(gh['repos'])} repos")
    print(f"    Moltbook: {mb['posts']} posts, score {mb['total_score']}, {mb['total_comments_received']} comments received")
    print(f"    Memory: {mem['daily_logs']} daily logs, {mem['total_entries']} entries, {mem['active_days']} active days")
    print(f"    Efficiency: {eff['total_hours_saved']}h saved, {eff['efficiency_multiplier']}x multiplier")
    print(f"    Workspace: {len(ws['projects'])} projects, {ws['total_files']} files, {ws['total_lines']} lines")
    print()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    
    print("Collecting data...", file=sys.stderr)
    gh = github_stats()
    mb = moltbook_stats()
    mem = memory_stats()
    eff = efficiency_stats()
    ws = workspace_stats()
    
    apw = calculate_apw(gh, mb, mem, eff, ws)
    
    if cmd == "score":
        print(f"{apw['total']} / {apw['max_possible']} ({apw['percentage']}%)")
    elif cmd == "report" and "--json" in sys.argv:
        print(json.dumps({"apw": apw, "github": gh, "moltbook": mb, "memory": mem, "efficiency": eff, "workspace": ws}, indent=2, ensure_ascii=False))
    else:
        print_report(apw, gh, mb, mem, eff, ws)
