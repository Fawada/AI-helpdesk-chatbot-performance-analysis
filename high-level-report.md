---
License: Copyright © 2026 Durham University, SHAREing Project, MIT Licensed
Creator: Fawada Qaiser
Contributors: Fawada Qaiser
Summary: High-level assessment report - RAG HPC help desk
---

# <img src='./images/logo.svg' width=90 style="vertical-align:middle" /> SHAREing: High-level performance assessment report

## Setup Details
* Program: DRI-helpdesk-Replication-Guide (RAG HPC helpdesk), tag `assessment-2026-08-v1`
* Parallel model: none in the client; worker is a single-node service on one APU. No MPI, no multithreaded scaling knob exposed.
* Dependencies: llama-index (+ ollama/embeddings/bm25 plugins), python-docx, psutil; Ollama runtime; llama3.1:8b, nomic-embed-text
* Compiler: N/A (interpreted Python; inference via precompiled Ollama runtime)
* Compiler flags: N/A
* Problem spec: 15-query characteristic benchmark (`hpc-helpdesk-standard-benchmark`), submitted sequentially over a shared-filesystem queue

## CPU Analysis
Not applicable. This code performs no user-level floating-point compute on the CPU; its work is document retrieval plus LLM inference dispatched to the AMD MI300A. A scalar-peak FLOPS comparison would not characterise the workload. No CPU score is assigned.

## GPU Analysis
Not measured in this high-level pass. The compute-intensive work (llama3.1:8b inference) runs on the MI300A APU. A meaningful GPU peak-performance-percentage would require profiling the Ollama runtime (e.g. `rocprofiler`/`rocm-smi`) on the worker, which is a deeper study than a high-level black-box glance. The MI300A's unified memory (no separate VRAM) also means the standard "benchmark exceeds GPU cache/VRAM" preparation step needs re-interpretation. Flagged as the primary candidate for follow-up if a deeper rubric is pursued. No GPU score assigned at this stage.

## IO Analysis
Relevant, and the most natural rubric for this architecture: the system is a shared-filesystem queue (requests, responses, token streams) plus index reads.

For a high-level first pass, end-to-end latency was measured from request submission to response file appearing. Total benchmark I/O plus compute for 15 queries was 48.05 s. A precise `C_IO = 1 - (t_read + t_write)/t_total` split requires instrumenting the worker's retrieval/generation vs. queue-wait time (e.g. Darshan or in-worker timers), which is proposed as follow-up. At the high level, queue I/O is not observed to dominate: warm queries complete in ~2–4 s each, consistent with generation time rather than I/O stalls.

IO score: not yet quantified (requires worker-side read/write timing). Preliminary observation: I/O does not appear to dominate runtime.

## Intra-node Analysis
Not applicable as specified. The workbook's intra-node rubric is a strong-scaling study over core counts on a fixed problem. This code exposes no such parallelism: the client is sequential and the worker is a single-process service; there is no thread/core sweep to perform. A conceptually analogous study would be **request concurrency** (multiple simultaneous users on the queue) measuring throughput, but that is a different metric from strong-scaling parallel efficiency and is noted as possible future work. No intra-node score assigned.

## Inter-node Analysis
Not applicable. The code does not run across multiple nodes (no MPI or distributed execution); the worker is bound to a single GPU node. Weak-scaling across nodes cannot be performed. No inter-node score assigned.

## End-to-end latency (primary high-level result)
The characteristic result for this code is response latency:

| Metric | Value |
| -- | -- |
| Queries | 15 |
| Total duration | 48.05 s |
| Cold-start (query 1) | 9.0 s |
| Warm steady-state | ~2–4 s/query (median ~3 s) |
| Timeouts / failures | 0 |
| Client memory (harness only) | ~14 MB |

Measurement caveat: response-time granularity is ~1 s (client polls with
`time.sleep(1)`); true per-query latencies are within ±1 s. Cold-start reflects
model load into the MI300A on first query.

## Summary

These scores are indicative only and cannot be meaningfully compared across
rubrics without domain knowledge. For a RAG helpdesk, most traditional HPC
rubrics do not apply; the meaningful characterisation is end-to-end latency.

| Result | Score | Metric result |
| ---------------- | - | - |
| CPU              | N/A | No user CPU FLOPS workload |
| GPU              | Not measured | Candidate for follow-up (MI300A inference) |
| IO               | Not quantified | I/O does not appear to dominate |
| Intra-node (80%) | N/A | No core-scaling parallelism |
| Inter-node (80%) | N/A | Single-node service |
