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
## MI300A / Ollama Configuration

Documenting the exact configuration is important for reproducibility and follows
AMD's recommended pattern for reporting MI300 inference results (by model,
precision, and context).

| Parameter | Value |
| --- | --- |
| Accelerator | AMD Instinct MI300A APU (gfx942); 4 present on node |
| GPUs used for inference | 1 of 4 (model on MainGPU:0; other 3 idle) |
| ROCm version | 7.14 (module `hipcc/7.14-rocm-el9`) |
| Ollama version | 0.21.2 |
| Generation model | llama3.1:8b (8.0B params, architecture: llama) |
| Quantisation | Q4_K_M |
| Context window | 131072 (128K); KV cache sized to match on GPU |
| GPU layers offloaded | 33/33 (fully offloaded) |
| Batch size | 512 |
| Flash attention | Enabled (auto) |
| Parallelism | OLLAMA_NUM_PARALLEL=1 (single-stream) |
| Embedding model | nomic-embed-text (embedding length 4096) |
| Ingest-only model | llama3.2:3b (used for index build, not serving) |
| Retrieval | LlamaIndex hybrid BM25 + dense, FINAL_TOP_K=12 |
| Temperature | 0.1 (near-deterministic) |
| Sampling stops | `<|start_header_id|>`, `<|end_header_id|>`, `<|eot_id|>` |
## CPU Analysis
Not applicable. This code performs no user-level floating-point compute on the CPU; its work is document retrieval plus LLM inference dispatched to the AMD MI300A. A scalar-peak FLOPS comparison would not characterise the workload. No CPU score is assigned.

## GPU Analysis (inference throughput on MI300A)

**Primary finding: as deployed, the GPU was unused — inference silently fell back to CPU, running ~40× slower than the hardware allows.**

The helpdesk's inference backend (Ollama) is intended to run llama3.1:8b on the node's MI300A GPU. In the as-deployed configuration, Ollama's GPU discovery failed ("failed to finish discovery before timeout" for all four devices) and it loaded the model on the CPU backend (`libggml-cpu-icelake.so`), with zero layers offloaded to GPU.

Generation throughput was measured directly via Ollama's `/api/generate` endpoint (warm model, 5 representative prompts × 3 repeats), isolating inference from the queue/retrieval layer:

| Condition | Generation (tok/s) | Prefill (tok/s) |
| --- | --- | --- |
| CPU fallback (as deployed) | ~5.7 median | ~122 median |
| GPU (ROCm loaded) | ~227 median | ~4469 median |
| **Improvement** | **~40×** | **~37×** |

**Root cause:** Ollama is launched (`start-ollama.sh`) from a shell without the ROCm runtime available, so the GPU libraries were not on the library path; GPU discovery timed out and inference fell back to CPU. The MI300A accelerator — the reason for siting the service on this node — sat idle.

**Fix (verified):** loading `module load hipcc/7.14-rocm-el9` before starting Ollama makes the MI300A GPU discoverable (`library=ROCm compute=gfx942`), fully offloads all 33/33 layers, and raises generation throughput from ~5.7 to ~227 tok/s. `start-ollama.sh` has been updated to load the module at startup.

**Secondary observation:** even after the fix, inference uses only 1 of the node's 4 MI300A GPUs (`OLLAMA_NUM_PARALLEL=1`, single MainGPU). The 8B model fits comfortably on one GPU, so this is reasonable, but throughput headroom exists via `OLLAMA_NUM_PARALLEL` or multiple workers across the 4 GPUs (see Further work).

**Scope note:** these figures characterise the *inference engine's* throughput on the MI300A, not GPU code written by the helpdesk (it has none — it dispatches inference to Ollama). tokens/s is used rather than a FLOP/s peak-percentage because it is the operative metric for LLM inference; a `rocprofiler`-based FLOP/s measurement is noted as further work.

## IO Analysis
Relevant, and the most natural rubric for this architecture: the system is a shared-filesystem queue (requests, responses, token streams) plus index reads.

For a high-level first pass, end-to-end latency was measured from request submission to response file appearing. Total benchmark I/O plus compute for 15 queries was 48.05 s. A precise `C_IO = 1 - (t_read + t_write)/t_total` split requires instrumenting the worker's retrieval/generation vs. queue-wait time (e.g. Darshan or in-worker timers), which is proposed as follow-up. At the high level, queue I/O is not observed to dominate: warm queries complete in ~2–4 s each, consistent with generation time rather than I/O stalls.

IO score: not yet quantified (requires worker-side read/write timing). Preliminary observation: I/O does not appear to dominate runtime.

Caveat: these latency figures predate the GPU fix (they were measured under CPU-fallback inference). With GPU inference (~40× faster generation), absolute latencies fall sharply and the I/O share of runtime warrants re-measurement.
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

Note: the latency and concurrency measurements in this report were taken with inference on CPU fallback (see GPU Analysis). With GPU inference restored, absolute per-query latencies are substantially lower; the qualitative findings (linear concurrency scaling, single-worker ceiling) are unaffected, but absolute figures would be revised downward on re-measurement.
## Latency decomposition (retrieval vs generation)

To locate where each request's time is spent, the worker was instrumented to record retrieval time and generation time separately (`t_retrieval_s`, `t_generation_s` in each response). Measured across the 15-query benchmark (warm, GPU inference):

| Component | Typical time | Share |
| --- | --- | --- |
| Retrieval (hybrid BM25 + dense) | ~0.06 s | ~3% |
| Generation (llama3.1:8b on MI300A) | ~1.9 s | ~97% |
| Total (warm) | ~1.9–2.0 s | 100% |

(The first query of a run is a cold-start outlier — total ~8.3s, with model load inflating generation and first-use index warming inflating retrieval — and is excluded from the steady-state figures.)

**Finding:** each request is almost entirely generation; retrieval is negligible (~0.06s). This measurement replaces the earlier inference that "retrieval and serialisation" limit concurrency: retrieval is not a meaningful cost. The concurrency bottleneck is that the single worker performs **one generation at a time** (`OLLAMA_NUM_PARALLEL=1`), leaving the MI300A serving a single request while 3 of 4 GPUs sit idle.

**Implication:** retrieval optimisation would yield almost nothing. The effective levers for concurrent throughput are (a) raising `OLLAMA_NUM_PARALLEL` so one GPU serves multiple concurrent generations, and (b) running multiple workers across the idle GPUs. This is consistent with the observed GPU utilisation sawtooth (brief idle gaps between generations because retrieval is fast).
## Summary

These scores are indicative only and cannot be meaningfully compared across
rubrics without domain knowledge. For a RAG helpdesk, most traditional HPC rubrics do not apply; the meaningful characterisations are inference throughput, end-to-end latency, and service concurrency. The most significant finding is that the GPU was unused as deployed (inference fell back to CPU), resolved by a one-line ROCm environment fix for a ~40× throughput gain.

| Result | Score | Metric result |
| ---------------- | - | - |
| CPU              | N/A | No user CPU FLOPS workload |
| GPU              | Major flaw found & fixed | CPU fallback → ROCm; ~40× (5.7→227 tok/s) |
| IO               | Not quantified | I/O does not appear to dominate |
| Intra-node (80%) | N/A | No core-scaling parallelism |
| Inter-node (80%) | N/A | Single-node service |
| Concurrency | ~31 req/min | Service ceiling; latency scales linearly with load |
## Concurrency / Throughput (service scaling study)

Traditional intra/inter-node scaling does not apply to this code, but the
operationally meaningful question for a helpdesk *service* is how it behaves
under simultaneous users. The worker processes requests serially (FIFO, one at
a time — confirmed in `worker.py`: `claim_oldest()` claims a single oldest
request per poll cycle, no request-level threading). We therefore measured
per-request latency and throughput as concurrent load increases.

N requests were submitted simultaneously (via threads) at each concurrency
level, repeating a single representative query
("How do I submit a basic batch job using SLURM?") to isolate the queuing
effect. A warm-up query preceded the sweep to exclude cold-start.

| Concurrency (N) | Batch wall (s) | Min (s) | Median (s) | Max (s) | Throughput (req/min) | Failures |
| --- | --- | --- | --- | --- | --- | --- |
| 1  | 1.91  | 1.90 | 1.90 | 1.90  | 31.5 | 0 |
| 2  | 3.91  | 2.10 | 3.01 | 3.91  | 30.7 | 0 |
| 5  | 9.72  | 2.41 | 6.31 | 9.71  | 30.9 | 0 |
| 10 | 17.33 | 2.41 | 9.66 | 17.33 | 34.6 | 0 |

<img src='images/concurrency.png' width=600 />
**Findings:**
- **Throughput is constant at ~31 requests/minute** regardless of concurrency —
  the service capacity of the single-worker design. Concurrent load does not
  increase throughput.
- **Per-request latency grows linearly with queue depth.** The last of 10
  simultaneous requests waits ~17s, sitting behind 9 others (batch wall ≈ N ×
  service time confirms strict serialisation).
- **Zero failures** at all levels: the queue absorbs backlog gracefully;
  requests wait rather than drop.

**Implication:** the current single-worker design is well-behaved but caps
service capacity at ~31 req/min. If concurrent demand routinely exceeds this,
the natural mitigation is multiple workers consuming the same queue — the
architecture (atomic claim via rename) already supports this without
modification.

Note: single-request latency here (~1.9s) is lower than the sequential
benchmark's ~3s, due to finer polling (0.1s vs 1s) and a fully warm model;
the two figures should not be directly compared.
## Concurrency on the GPU-fixed configuration

The concurrency sweep was repeated after the GPU fix (inference on MI300A, ~227 tok/s), with the model warmed beforehand. GPU utilisation was monitored via `rocm-smi` during the run.

| Concurrency (N) | Batch wall (s) | Min (s) | Median (s) | Max (s) | Throughput (req/min) | Failures |
| --- | --- | --- | --- | --- | --- | --- |
| 1  | 2.30  | 2.30 | 2.30  | 2.30  | 26.0 | 0 |
| 2  | 4.31  | 2.20 | 3.26  | 4.31  | 27.9 | 0 |
| 5  | 8.91  | 1.81 | 5.91  | 8.91  | 33.7 | 0 |
| 10 | 19.03 | 2.50 | 10.21 | 19.02 | 31.5 | 0 |

**Key finding — the GPU fix did not materially change concurrent throughput (~30 req/min, same as the CPU-fallback run).** Raw token generation improved ~40× (see GPU Analysis), but end-to-end throughput under load is governed by the single-worker serial pipeline (retrieval, queue handling, `OLLAMA_NUM_PARALLEL=1`), not by generation speed.

**GPU utilisation under concurrent load:** `rocm-smi` showed GPU0 sawtoothing between ~99% and 0% — bursts of generation separated by idle periods while the worker performs retrieval and claims the next request. GPUs 1-3 remained essentially unused (~1%). The MI300A is therefore **fixed but under-utilised** under concurrent demand.

**Implication:** the concurrency bottleneck is worker serialisation, not GPU compute. Throughput headroom exists via (a) raising `OLLAMA_NUM_PARALLEL` to let one GPU serve multiple concurrent generations, and (b) running multiple workers across the three idle GPUs. This is the primary scalability optimisation for the service.

Note: per-request latency is now much lower than the CPU-fallback run (e.g. N=1 warm ~2.3s vs generation alone taking ~15s on CPU for a long answer), so the GPU fix substantially improved *individual* response times even though aggregate concurrent throughput is unchanged.
## Evaluation framework and further work

A RAG chatbot must be assessed along three independent dimensions — **system/GPU performance, retrieval quality, and answer quality**. A fast chatbot may still retrieve the wrong evidence or generate unsupported answers, so speed alone is not a sufficient assessment.

**Assessed in this report (system/GPU performance):** generation throughput (tokens/s) and the CPU-fallback/ROCm-fix finding; end-to-end latency (cold vs warm); concurrency/throughput and single-worker saturation; GPU utilisation and offload; error/timeout rate (zero observed); full configuration record.

**Further work — not yet assessed:**

*Retrieval quality* (requires a labelled test set of questions → relevant chunks): Recall@k, Precision@k, Hit-rate@k, MRR, nDCG@k; context sufficiency; ablations of dense vs BM25 vs hybrid, chunk size, embedding model, and top-k (k = 3, 5, 10).

*Answer quality* (requires reference answers and/or an LLM judge plus human review): correctness, faithfulness/groundedness, answer relevance, citation accuracy, hallucination rate, abstention on no-answer questions.

*Extended system sweeps:* TTFT and TPOT; p50/p95/p99 latency (computable from existing per-query data); retrieval-vs-generation latency decomposition (to confirm where each request's time is spent); model-size sweep (llama3.2:3b vs llama3.1:8b — both already available); quantisation and context-length sweeps; a latency–quality Pareto plot once quality metrics exist. (A GPU-fixed concurrency re-run at 1/2/5/10 is done — see "Concurrency on the GPU-fixed configuration"; higher levels 16+ remain further work.)

*Prerequisite:* the retrieval and answer-quality work depends on building a labelled benchmark set (~100–300 representative questions with relevant chunks and reference answers). This is the natural next phase and the main outstanding effort.
