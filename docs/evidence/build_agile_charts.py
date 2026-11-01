"""Rebuild the Group 11 burndown and cumulative-flow charts from Jira status history.

Run from anywhere: python docs/evidence/build_agile_charts.py (needs matplotlib).
Input: jira_history_2026-11-01.json (Jira changelog, status field). Not imported by the app.
"""
import csv, json
from datetime import datetime, timedelta
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md

T = lambda s: datetime.strptime(s, "%m-%d %H:%M").replace(year=2026)
import json as _json
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_os.chdir(_HERE)  # read the JSON and write the charts next to this script
_D = _json.load(open("jira_history_2026-11-01.json"))
I = {int(k.split("-")[1]): (v[0], v[1], [tuple(x.split(">")) for x in v[2]]) for k, v in _D["issues"].items()}
I = {k:(s,a,[(T(t),st) for t,st in h]) for k,(s,a,h) in I.items()}
SPRINTS = {0:("Sprint 0",T("10-14 00:00"),T("10-20 23:59")),1:("Sprint 1",T("10-21 00:00"),T("10-27 23:59")),2:("Sprint 2",T("10-28 00:00"),T("10-31 23:59"))}
NOW = T("11-01 11:40")
PRS = [("10-19 17:44","#1"),("10-20 19:21","#3"),("10-20 19:51","#2"),("10-21 19:02","#4"),("10-22 20:26","#5"),("10-24 14:34","#6"),("10-24 18:02","#7"),("10-25 11:04","#8"),("10-25 19:47","#9"),("10-25 20:00","#10"),("10-27 23:05","#11"),("10-28 10:23","#13"),("10-28 10:24","#12"),("10-28 11:19","#14"),("10-28 14:25","#15"),("10-28 19:57","#16"),("10-29 22:30","#18"),("10-30 21:51","#17"),("10-30 21:55","#19"),("10-30 22:41","#20"),("10-30 23:35","#21"),("10-30 23:46","#22"),("10-31 11:35","#23"),("10-31 12:11","#24"),("10-31 15:46","#25"),("10-31 17:55","#26")]
PRS = [(T(t),n) for t,n in PRS]

def status_at(h, t):
    s = "To Do"
    for when, st in h:
        if when <= t: s = st
    return s
def done_at(h):
    """Time of the final Done, if the item is Done now (reopened items count from their last Done)."""
    return h[-1][0] if h and h[-1][1]=="Done" else None

# raw evidence table
with open("jira_status_history.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["issue","planned_sprint","assignee","time_sydney","new_status"])
    for k,(s,a,h) in sorted(I.items()):
        for t,st in h: w.writerow([f"SCRUM-{k}",SPRINTS[s][0],a,t.strftime("%Y-%m-%d %H:%M"),st])

times=[T("10-14 00:00")+timedelta(hours=x) for x in range(int((NOW-T("10-14 00:00")).total_seconds()//3600)+1)]+[NOW]
fig, ax = plt.subplots(figsize=(11,5.2))
total=len(I)
rem=[sum(1 for s,a,h in I.values() if status_at(h,t)!="Done") for t in times]
ax.step(times,rem,where="post",lw=2.2,color="#2a6fdb",label="Remaining work items (actual Jira status)")
# planned (ideal) line: each sprint's items due by its planned end
ideal_t=[T("10-14 00:00")]; ideal_v=[total]; left=total
for sid in (0,1,2):
    n=sum(1 for s,_,_ in I.values() if s==sid); left-=n
    ideal_t.append(SPRINTS[sid][2]); ideal_v.append(left)
ax.plot(ideal_t,ideal_v,"--",color="#888",lw=1.4,label="Planned (each sprint's items done by its planned end)")
for sid,(n,a,b) in SPRINTS.items():
    ax.axvspan(a,b,color=["#f3f6fb","#fbf7ef","#f1f8f1"][sid],zorder=0)
    ax.text(a+timedelta(hours=6),total+1.2,n,fontsize=9,color="#555")
for t,n in PRS:
    ax.axvline(t,color="#d9822b",alpha=.35,lw=1)
ax.plot([],[],color="#d9822b",alpha=.6,label="GitHub PR merged to main")
ax.set_ylim(0,total+3); ax.set_xlim(T("10-14 00:00"),T("11-01 12:00"))
ax.xaxis.set_major_locator(md.DayLocator(interval=2)); ax.xaxis.set_major_formatter(md.DateFormatter("%d %b"))
ax.set_ylabel("Open Jira work items (35 planned)"); ax.set_title("Group 11 burndown reconstructed from Jira status-change timestamps")
ax.legend(loc="lower left",fontsize=8.5,frameon=False); ax.grid(axis="y",alpha=.25)
fig.text(0.01,0.005,f"Source: Jira changelog for SCRUM-1..43 (epics and one placeholder subtask excluded), read {NOW:%d %b %H:%M} AEDT; PR merges from git history.\nReopened items count as open until their final Done. A status time is when Jira was updated, which can lag the code.",fontsize=7,color="#666")
fig.tight_layout(rect=(0,0.05,1,1)); fig.savefig("burndown_overall.png",dpi=160)

# per-sprint burndown
fig, axs = plt.subplots(1,3,figsize=(13,4),sharey=False)
for sid,ax in zip((0,1,2),axs):
    name,a,b=SPRINTS[sid]; items=[h for s,_,h in I.values() if s==sid]
    end=NOW
    ts=[a+timedelta(hours=x) for x in range(int((end-a).total_seconds()//3600)+1)]+[end]
    ax.step(ts,[sum(1 for h in items if status_at(h,t)!="Done") for t in ts],where="post",lw=2,color="#2a6fdb",label="Actual remaining")
    ax.plot([a,b],[len(items),0],"--",color="#888",label="Planned guideline")
    ax.axvline(b,color="#c0392b",lw=1,alpha=.6); ax.text(b,len(items)+.3," planned end",fontsize=8,color="#c0392b")
    ax.set_title(f"{name} ({a:%d}–{b:%d %b}, {len(items)} items)",fontsize=10); ax.set_ylim(0,len(items)+1.5)
    ax.xaxis.set_major_locator(md.DayLocator(interval=3 if sid==0 else 2)); ax.xaxis.set_major_formatter(md.DateFormatter("%d/%m")); ax.grid(axis="y",alpha=.25)
axs[0].set_ylabel("Open items"); axs[0].legend(fontsize=8,frameon=False)
fig.suptitle("Per-sprint burndown (planned sprint windows; actual Jira status timestamps)",fontsize=11)
fig.tight_layout(); fig.savefig("burndown_per_sprint.png",dpi=160)

# cumulative flow
order=["Done","In Review","In Progress","To Do"]; cols={"Done":"#3a9a5b","In Review":"#9b7fd4","In Progress":"#2a6fdb","To Do":"#c9ced6"}
times=times+[NOW+timedelta(hours=8)]
counts={s:[sum(1 for _,_,h in I.values() if status_at(h,t)==s) for t in times] for s in order}
fig, ax = plt.subplots(figsize=(11,4.6))
ax.stackplot(times,*[counts[s] for s in order],labels=order,colors=[cols[s] for s in order],step="post")
ax.set_xlim(T("10-14 00:00"),NOW+timedelta(hours=8)); ax.set_ylim(0,total)
ax.xaxis.set_major_locator(md.DayLocator(interval=2)); ax.xaxis.set_major_formatter(md.DateFormatter("%d %b"))
ax.set_title("Cumulative flow of the 35 planned work items (Jira status history)"); ax.set_ylabel("Work items")
ax.legend(loc="upper left",fontsize=8.5,frameon=False)
fig.tight_layout(); fig.savefig("cumulative_flow.png",dpi=160)

summary={sid:{"name":SPRINTS[sid][0],"planned":sum(1 for s,_,_ in I.values() if s==sid),
  "done_by_planned_end":sum(1 for s,_,h in I.values() if s==sid and done_at(h) and done_at(h)<=SPRINTS[sid][2]),
  "done_now":sum(1 for s,_,h in I.values() if s==sid and done_at(h))} for sid in SPRINTS}
print(json.dumps(summary,indent=1))
late=[(k,done_at(h)) for k,(s,_,h) in I.items() if done_at(h) and done_at(h)>SPRINTS[s][2]]
print("done after planned end:",sorted(f"SCRUM-{k} {t:%d %b}" for k,t in late))
