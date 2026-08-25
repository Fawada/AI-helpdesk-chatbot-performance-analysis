#!/usr/bin/env python3
"""
Plot concurrency benchmark results: latency-vs-N and throughput-vs-N.
Reads results/benchmark_concurrent_report.json, writes images/concurrency.png.

Usage: python scripts/plot_concurrency.py
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")   # no display needed on COSMA
import matplotlib.pyplot as plt

repo = Path(__file__).resolve().parent.parent
data = json.loads((repo / "results" / "benchmark_concurrent_report.json").read_text())
results = data["results"]

N        = [r["concurrency"] for r in results]
median   = [r["latency_median_s"] for r in results]
maximum  = [r["latency_max_s"] for r in results]
minimum  = [r["latency_min_s"] for r in results]
tput     = [r["throughput_req_per_min"] for r in results]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

# Left: latency vs concurrency
ax1.plot(N, maximum, "o-", label="max (last in queue)", color="#c0392b")
ax1.plot(N, median,  "s-", label="median", color="#2980b9")
ax1.plot(N, minimum, "^-", label="min (first served)", color="#27ae60")
ax1.set_xlabel("Concurrent requests (N)")
ax1.set_ylabel("Latency (s)")
ax1.set_title("Latency grows linearly with queue depth")
ax1.legend()
ax1.grid(True, alpha=0.3)

# Right: throughput vs concurrency
ax2.plot(N, tput, "o-", color="#8e44ad")
ax2.set_xlabel("Concurrent requests (N)")
ax2.set_ylabel("Throughput (req/min)")
ax2.set_title("Throughput flat (single-worker ceiling)")
ax2.set_ylim(0, max(tput) * 1.3)
ax2.grid(True, alpha=0.3)
ax2.axhline(y=sum(tput)/len(tput), color="gray", linestyle="--", alpha=0.6,
            label=f"mean ~{sum(tput)/len(tput):.0f} req/min")
ax2.legend()

fig.suptitle("HPC Helpdesk — Concurrency Behaviour (single serial worker)",
             fontsize=13)
fig.tight_layout()

out = repo / "images" / "concurrency.png"
fig.savefig(out, dpi=120, bbox_inches="tight")
print(f"Saved {out}")
