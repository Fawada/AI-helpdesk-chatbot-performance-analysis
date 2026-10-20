---
License: Copyright © 2026 Durham University, SHAREing Project, MIT Licensed
Creator: Thomas Flynn
Contributors: Fawada Qaiser
Summary: README file for the SHAREing assessment templates repository
---

# <img src='./images/logo.svg' width=90 style="vertical-align:middle" /> SHAREing: Performance Assessment Templates

**This repository is in a very early stage of development**

This repository is part of the [SHAREing](https://shareing-dri.github.io/) project and is focused on conducting pre-assessment and high-level performance assessments of research software.
We use a markdown document and set of associated scripts to generate graphs during the high-level assessment.

## Setup

Very few Python dependencies are required for the scripts, which can be installed locally, or in a virtual environment, by running the command 
```bash
pip install -r requirements.txt
```

Once you have cloned the repository, you can fill in the template in `report.md`.

## Structure of high-level performance assessment

Performance is broken down into 5 main topics
1. Core
2. Intra-node
3. Inter-node
4. GPU
5. I/O

Further details of how to conduct each performance measurement are given in the [guidebook](https://shareing-dri.github.io/performance-assessment/guidebook).
An example report is included in the `examples` folder.

The Core and I/O rubrics do not require significant calculation to complete so no associated script has been written.
At the point that this is being written, the GPU and Inter-node rubrics do not yet have a fixed workflow (2026-03-19).
Below we list the usage of each script for the high-level assessment.

### `intranode_times_to_graph.py`

Intra-node performance analysis is located in the `intranode_times_to_graph.py` script.

When called as a script, it takes data input from the standard input or a unix pipe.
It can take either CSV or Markdown table as input.
For demonstration purposes, suppose we have the data
```csv
1, 29.995
2, 18.23
4, 10.74
8, 10.33
16, 9.1307
32, 8.5401
64, 7.4589
```
in a csv file `times.csv`, where the first column is core count and the second is time in seconds.
If we want to check the graph looks reasonable, we can run with
```
$ ./scripts/intranode_times_to_graph.py --graph
```
and paste the data when it prompts.
Now we've checked the graph, we can generate a markdown table to copy-paste to the report and a graph image output to the default directory:
```
$ cat times.csv | ./scripts/intranode_times_to_graph.py -gmd --markdown-file=stdout
```

The script can also take a Markdown table as input in the same way as it can take CSV.
For a file `times.md`
```md
| Thread count | Time (s) | Parallel Efficiency |
| - | - | - |
| 1 | 29.995 | 1.000 |
| 2 | 18.230 | 0.823 |
| 4 | 10.740 | 0.698 |
| 8 | 10.330 | 0.363 |
| 16 | 9.1307 | 0.205 |
| 32 | 8.5401 | 0.110 |
| 64 | 7.4589 | 0.063 |
```
it can be passed exactly the same as `times.csv` was.

There are a variety of other usage flags, details of which can be found with
```shell
$ ./scripts/intranode_times_to_graph.py --help
```

Internally, this script contains three useful functions which could be used from other code:
1. `intranode_times_crit_80_60(times: list[tuple[int, float]]) -> (float, float)` - this calculates the 80% and 60% efficiency points and returns them as a tuple
2. `intranode_times_to_graph(times: list[tuple[int, float]]) -> plt.Figure` - self-explanatory, generates the graph
3. `intranode_times_to_markdown(times: list[tuple[int, float]]) -> str` - this renders the core counts and times as a three-column markdown table with core count, time, and parallel efficiency

Each function is passed the times as a list of tuples of core count and time taken.

### `internode_times_to_graph.py`

This script is `TODO`

### `summary.py`

Generation of a summary graphic is located in the `summary.py` script.

When called as a script, it takes data input from the standard input or a unix pipe the same way as the previous scripts.
It can take either CSV or Markdown table as input.
It accepts an arbitrary number of rows of "rubric, score".

## Contributions

This performance assessment is intentionally limited as we want to simply capture the performance of software at a *high level*.
However, if you have ideas of performance metrics which are necessary but missing, or if you find any faults with the scripts or template, please raise an issue.

## Acknowledgements
The initial development of the notebook was implemented by Ben Clark.
Further work on the notebook was undertaken by Thomas Flynn, before it was rewritten as scripts.
This project has received funding through the UKRI Digital Research Infrastructure Programme under grant UKRI1801 (SHAREing).

<img src='./images/ukri.png' width=200 style="vertical-align:middle" /> 

All files in this repository are released under the [MIT License](./LICENSE).
