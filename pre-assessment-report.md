# Pre-assessment: AI HPC Helpdesk (RAG Chatbot)

## Assessment objective

An internal review of the `DRI-helpdesk-Replication-Guide` RAG helpdesk
(https://github.com/Fawada/DRI-helpdesk-Replication-Guide), tag
`assessment-2026-08-v1`, using the `hpc-helpdesk-standard-benchmark` (15
representative helpdesk queries). Assessment performed by Fawada Qaiser,
DiRAC / Durham University, on 2026-08-17.

## Disclaimers

1. This report is not a commentary on code quality, but an indicator of the
   quality of the current SHAREing testing methodology as of 2026-08.
2. The pre-assessment is only a preliminary assessment of submission
   suitability and does not guarantee a full assessment.

## Table of contents

- [x] 1: Benchmark setup
- [x] 2: Description of working environment
- [x] 3: Compiler setup and optimisations
- [x] 4: Computational complexity and scaling
- [x] 5: Memory, storage and I/O
- [x] 6: Additional comments from submitter
- [x] 7: Pre-assessment outcome

## 1: Benchmark setup

### Fetch and build program

The code is a self-hosted retrieval-augmented-generation (RAG) helpdesk. A
worker on the GPU node retrieves relevant documentation chunks (LlamaIndex
hybrid BM25 + dense retrieval) and generates answers with a local LLM
(llama3.1:8b via Ollama). Clients and worker communicate through a
shared-filesystem queue; no external API is used.

```bash
git clone https://github.com/Fawada/DRI-helpdesk-Replication-Guide.git
cd DRI-helpdesk-Replication-Guide
python3 -m venv ~/hpc-helpdesk-env
source ~/hpc-helpdesk-env/bin/activate
pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama \
            llama-index-retrievers-bm25 python-docx psutil
```

Models are served locally via Ollama on the GPU node:

```bash
ollama pull llama3.1:8b       # generation
ollama pull nomic-embed-text  # embeddings
```

### Fetch and run benchmark

The benchmark is included with the code under `benchmark/`. It submits each
query as a JSON file to the shared queue and waits for the corresponding
response file.

```bash
cd DRI-helpdesk-Replication-Guide
source install/config.sh      # sets HELPDESK_ROOT and queue paths (shared FS)
bash worker/start-worker.sh   # start worker on GPU node (once)
python benchmark/run_benchmark.py
```

Expected output: one `[SUBMITTED]` / `Completed in <t> seconds` line per query,
then a summary (total duration, per-query results saved to
`results/benchmark_report.json`). No file output beyond the JSON report and the
queue traffic.

### Reference architecture

The reference and assessment system are the same: COSMA8 (Durham University),
GPU node ga008. No cross-architecture comparison is in scope for this review.

## 2: Description of working environment

### Hardware information

### Hardware information

The COSMA8 system at Durham University was used for this assessment. The worker
runs on GPU node ga008. Hardware was confirmed directly on the compute node via
`cat /proc/cpuinfo`, `lscpu`, and `free -h` (rather than assumed), following the
workbook's guidance to read specifications from the compute node itself and never
from a login node.

| Specification        | Per node (ga008)                                  |
| -------------------- | ------------------------------------------------- |
| Accelerator (APU)    | AMD Instinct MI300A                               |
| Architecture         | Integrated CPU+GPU (APU) with unified memory      |
| CPU(s)               | 192 (2 threads/core)                              |
| Sockets              | 4                                                 |
| NUMA nodes           | 4                                                 |
| Total memory         | 501 GiB (unified CPU/GPU pool)                    |
| LLM                  | llama3.1:8b (Ollama, local)                       |
| Embeddings           | nomic-embed-text                                  |

NUMA layout (from `lscpu`):
NUMA node0 CPU(s):                       0-23,96-119
NUMA node1 CPU(s):                       24-47,120-143
NUMA node2 CPU(s):                       48-71,144-167
NUMA node3 CPU(s):                       72-95,168-191.

Note: the MI300A is an APU, so CPU and GPU share a single unified 501 GiB memory
pool rather than the GPU having separate dedicated VRAM. Login nodes on COSMA8
(e.g. login7a, Intel Xeon Gold 5120) differ from the MI300A compute nodes, so
login-node specifications are not representative of the assessment hardware.00

### Assessment tools

1. Pre-assessment:
   - Wall-clock timing (benchmark harness)
   - psutil (client memory footprint)
2. High-level assessment:
   - End-to-end response latency (per-query wall time)
   - I/O proportion (candidate; queue + index reads)
   - GPU utilisation (candidate; nvidia-smi / nsight on the worker)
3. Low-level assessment:
   - To be determined if the high-level stage flags a specific rubric.

## 3: Compiler setup and optimisations

Not applicable in the conventional sense. This is an interpreted Python
application; there is no user compilation step. The performance-critical work is
LLM inference executed by Ollama (a precompiled runtime) on the GPU. No compiler
flags, vectorisation toggles, or accelerator build options are exposed by the
submitted code.

## 4: Computational complexity and scaling

The workload does not scale in the classic strong/weak sense (no MPI, no
multi-node, no thread-count sweep). The natural scaling dimensions are:

- Corpus size (number of indexed document chunks), affecting retrieval.
- Concurrency (number of simultaneous users/requests on the queue), affecting
  throughput.

For this review the corpus is fixed and queries are submitted sequentially, so a
single fixed problem setup is used. Strong/weak scaling studies from the workbook
are noted as not applicable and excluded with justification in the high-level
report.

## 5: Memory, storage and I/O

Client-side memory footprint is ~14 MB (benchmark harness only). The worker's
model (llama3.1:8b) occupies roughly 6 GB, drawn from the node's unified 501 GiB
memory pool shared between CPU and GPU (MI300A APU), not a separate VRAM bank.

Storage: the benchmark writes small JSON request/response files to the
shared-filesystem queue and a single `benchmark_report.json`. No large temporary
or checkpoint files.

I/O: the architecture is intrinsically filesystem-queue based (requests,
responses, token streams, and index reads). This makes I/O proportion a
genuinely relevant high-level rubric for this code, unlike most others. Console
output is minimal.

## 6: Additional comments from submitter

The submitter and assessor are the same person for this internal review. The
code is a production deployment on COSMA and has been replicated at Keele
(GreenHPC), so the benchmark reflects real usage.

## 7: Pre-assessment outcome

The code builds, runs, and completes the benchmark without user interaction
(~48 s for 15 queries, well within the <10 min guideline). It meets the
pre-assessment criteria and **proceeds to the high-level assessment**. Note that
several standard rubrics (core FLOPS, intra-node, inter-node) do not map onto a
single-GPU RAG service; the high-level report justifies which rubrics apply.
00
