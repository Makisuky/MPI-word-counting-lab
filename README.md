# Parallel Word Counting in a Text Corpus with MPI

## Team Information

**Zahir Acosta De La Asunción · Alejandro David Alonso Durán · María Isabel Gutiérrez González · Lucía Isabel Montoya Orozco**

**Course:** Computer Architecture 2 &nbsp;|&nbsp; May 2026

- Repository: `mpi-word-counting-lab`
  
---

## Table of Contents

1. [Problem Description](#1-problem-description)
2. [Environment and Execution Instructions](#2-environment-and-execution-instructions)
3. [Experimental Plan](#3-experimental-plan)
4. [Experimental Plan Execution](#4-experimental-plan-execution)
5. [Analysis](#5-analysis)
6. [Conclusions](#6-conclusions)
7. [References](#references)

---

## 1. Problem Description

Word frequency counting across large document collections is a computationally intensive operation that appears repeatedly in information retrieval, text mining, and natural language processing [2]. In its straightforward sequential form, the problem requires iterating over every document in the corpus, tokenizing its contents, and updating a frequency accumulator for each term of interest. When the corpus contains tens of millions of tokens distributed across thousands of files, sequential processing time grows linearly with data volume and becomes a bottleneck that motivates the adoption of parallel computing techniques.

The specific goal of this laboratory assignment is to determine how many times each of the 200 words in the query file `consulta.txt` appears across a corpus of 3,000 text files named `file_XXXX.txt`, and to report the ten most frequent ones. The corpus was generated synthetically using `generator.py` with a deliberately heterogeneous file-size distribution: roughly 60 percent of the files are small (2,000 to 5,000 words), 30 percent are medium (10,000 to 20,000 words), and 10 percent are large (50,000 to 100,000 words). This distribution replicates the characteristics of real-world document collections, where a minority of documents is orders of magnitude longer than the majority, and it is the root cause of the load imbalance analyzed in later sections.

The laboratory addresses the problem in three progressive stages. The first stage establishes a correctness and timing reference by running a provided sequential implementation. The second stage introduces parallelism through MPI using a static file-distribution strategy that assigns the same number of files to each process without considering file size. The third stage corrects the load imbalance observed in the second stage by distributing files proportionally to their size in bytes. Each stage is evaluated across at least three independent runs per process-count configuration, and the results are compared using the standard parallel performance metrics of speedup and efficiency.

---

## 2. Environment and Execution Instructions

All experiments were executed inside a Docker container using the image `augustosalazar/slim-mpi:2`, which bundles Python 3, the `mpi4py` library, and a pre-configured Open MPI installation [3][4]. Using Docker ensures a fully reproducible environment — the same compiler versions, interpreter, and library binaries are active regardless of the host operating system. All project files were mounted into the container at the path `/app` using Docker's `-v` volume flag.

The number of logical cores available inside the container was verified by running `nproc`, which reported 7 available cores. Because the laboratory required testing with p = 8 MPI processes, executions at that configuration needed the `--oversubscribe` flag. This flag allows Open MPI to launch more processes than available cores, but it does not create additional computing capacity. When two MPI processes share a single core, the operating system alternates between them through context switching, which adds scheduling overhead and introduces timing variability [4]. The results reported for p = 8 must therefore be interpreted with this environmental constraint in mind.

The main execution commands used throughout the experiment were the following:

```bash
# Generación del dataset
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 python /app/generator.py

# Baseline secuencial
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 python /app/baseline_secuencial.py

# MPI Versión 1 con p procesos (ejemplo p=4)
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root -n 4 python /app/mpi1.py

# MPI con p=8 (requiere oversubscribe por límite de 7 núcleos)
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --oversubscribe -n 8 python /app/mpi1.py
```

---

## 3. Experimental Plan

The experimental plan was structured in four sequential phases. The first phase generated the dataset using `generator.py`. The second phase ran the sequential baseline to establish the reference time *T_seq* and the ground-truth word counts. The third and fourth phases executed `mpi1.py` and `mpi2.py` respectively, each with p ∈ {1, 2, 4, 8} and three independent runs per configuration. The performance metrics computed were speedup, defined as S_p = T_seq / T_p, and efficiency, defined as E_p = S_p / p, where T_seq = 26.876594 s is the sequential baseline time and *T_p* is the average of the three total execution times at p processes.

### a. Sequential Baseline

The sequential reference implementation, contained in `baseline_secuencial.py`, was provided by the teaching staff and was not modified in any way. Its execution proceeds as follows. First, it reads `consulta.txt` and loads all query words into a Python `set` object, which provides O(1) average-case lookup and is the most efficient data structure for membership testing. It then iterates over all entries in the `dataset/` directory whose names match the pattern `file_*.txt`, using `os.listdir()` to obtain the file list. The order in which files are processed is not guaranteed, because `os.listdir()` returns entries in filesystem order, which can vary across runs.

For each file, the program opens it in UTF-8 text mode, reads its content line by line, and splits each line into tokens using `str.split()`, which segments on any whitespace sequence without discarding punctuation that may be adjacent to words. For every token, it checks membership in the query set and, if found, increments the corresponding counter in a Python `Counter` object [5]. When the full corpus traversal is complete, the program calls `Counter.most_common(10)` to extract the top ten results and writes the full sorted frequency list to a CSV file inside the `dataset/` folder. This CSV file serves as the correctness reference against which both MPI implementations were verified.

One implementation detail worth noting is the tokenization difference between the baseline and both MPI versions. The baseline uses `str.split()`, while the MPI versions use `re.findall(r"\b\w+\b", text.lower())`, which extracts only alphanumeric sequences delimited by word boundaries and ignores any adjacent punctuation. In the synthetic corpus generated for this laboratory both methods produce identical token sets, as confirmed by comparing the CSV output files of all three implementations.

### b. MPI Version 1

The first parallel implementation, `mpi1.py`, follows the SPMD (Single Program Multiple Data) programming model characteristic of MPI. All processes execute the same program code, but each one operates on a distinct subset of the corpus. The execution flow is divided into three clearly defined phases (initialization and distribution, parallel local computation, and result collection and aggregation) each with a specific communication pattern.

During the **initialization phase**, the process with rank 0 acts as the coordinator. It opens `consulta.txt` and builds the list of 200 query words, then broadcasts this list to all other processes using `comm.bcast()`. A collective broadcast internally uses a binary-tree communication pattern that reduces the number of point-to-point messages required from O(p) to O(log p), making it far more efficient than individual sends as p grows [1]. After the broadcast, every process holds an identical local copy of the query words. Rank 0 additionally retrieves the sorted list of corpus files using `glob.glob()` and distributes them statically — process of rank *i* receives the files at positions i, i+p, i+2p, and so on in the list, expressed in Python as `all_files[i::p]`. This round-robin strategy guarantees that the number of files differs by at most one between any pair of processes, but it offers no guarantee about the volume of actual work each process will receive.

During the **local computation phase**, each process independently opens its assigned files, tokenizes their contents using `re.findall()`, and accumulates query-word counts in a local `Counter` object. This phase is entirely parallel and the time spent here is recorded as `local_time` in each rank's output. It is the key indicator for load-balance analysis, because any difference in local times directly reflects an imbalance in the amount of work assigned to each process.

During the **collection phase**, the collective operation `comm.gather()` retrieves all local `Counter` objects and delivers them to rank 0. This operation acts as an implicit synchronization barrier — rank 0 cannot proceed until every process has finished its local computation and sent its results. Consequently, the total wall-clock time of the parallel program is determined by the slowest process. Any load imbalance translates directly into idle waiting time for the faster processes, reducing global efficiency. Once all partial counters are collected, rank 0 merges them using `Counter.update()`, extracts the top ten results, and saves the complete frequency list to a CSV file.

### c. The Test Procedure

The timing methodology was designed to minimize external variability and produce reliable execution-time estimates. For both MPI versions, total wall-clock time was measured using `MPI.Wtime()`, a high-resolution wall-clock timer synchronized across all processes in the communicator [6]. The measurement window opens immediately before the broadcast call and closes immediately after rank 0 prints the top ten results, so that the recorded time reflects the full end-to-end work of the parallel program, including communication, computation, and aggregation. The sequential baseline used `time.perf_counter()`, which provides the highest-resolution clock available in Python for this type of measurement.

For each combination of implementation version and process count, exactly three consecutive independent runs were performed inside the same Docker container without restarting it between runs. This approach may introduce a partial disk-cache effect on the second and third runs, since the operating system may retain recently accessed file contents in memory. However, given that the full corpus exceeds 275 MB and the container's available memory is limited, the cache effect is expected to be partial and broadly consistent across all configurations, making it unlikely to systematically favor one implementation over another.

The raw output of every run was saved as a plain-text file under `outputs/raw/`. A post-processing script then extracted the numeric values and consolidated them into two CSV files (`timing_summary.csv` for total execution times and `local_times.csv` for per-rank data) to facilitate systematic analysis. The average of the three total execution times was used as *T_p* for the speedup and efficiency calculations, and the per-rank data from Run 1 of each configuration was used as representative evidence for load-balance analysis.

---

## 4. Experimental Plan Execution

### a. Sequential Baseline Timing

The sequential implementation processed all 3,000 corpus files in a single run, reading a total of 44,951,458 tokens and finding 3,631,778 occurrences of query words across the corpus. The recorded execution time was 26.876594 seconds, which serves as the fixed reference value *T_seq* for all speedup and efficiency calculations in this report. The ten most frequent query words found were *a* (785,774 occurrences), *para* (392,156), *sus* (228,913), *otros* (105,530), *ante* (99,832), *unos* (88,794), *otra* (83,901), *vosotros* (61,617), *mios* (58,420), and *tuya* (56,635). Both MPI implementations produced identical top-ten lists and identical total occurrence counts in all evaluated configurations, confirming their correctness.

### b. MPI Version 1 Timing Results

Table I presents the individual run times, the computed average *T_p*, the speedup S_p = T_seq / T_p, and the efficiency E_p = S_p / p for each configuration of `mpi1.py`:

**TABLE I — Execution time, speedup, and efficiency of mpi1.py (T_seq = 26.876594 s)**

| **p** | **Run 1 (s)** | **Run 2 (s)** | **Run 3 (s)** | **Average (s)** | **Speedup** | **Efficiency** |
|:-----:|:-------------:|:-------------:|:-------------:|:---------------:|:-----------:|:--------------:|
| 1 | 28.079709 | 25.431295 | 26.874339 | 26.795114 | 1.00 | 1.00 |
| 2 | 14.530604 | 14.255729 | 14.553288 | 14.446540 | 1.86 | 0.93 |
| 4 | 9.577585 | 11.229220 | 10.660970 | 10.489258 | 2.56 | 0.64 |
| 8 | 8.943007 | 8.288741 | 8.750497 | 8.660748 | 3.10 | 0.39 |

With p = 1, `mpi1.py` averaged 26.795 seconds, nearly identical to the sequential baseline of 26.876 seconds. This near-zero difference confirms that the overhead introduced by the MPI runtime (the broadcast and gather operations executed with a single process) is negligible for this problem size. As the process count increases, execution time decreases consistently: 14.447 seconds with p = 2, 10.489 seconds with p = 4, and 8.661 seconds with p = 8. The between-run variability is moderate, reaching its highest relative spread at p = 4, where the three individual times range from 9.578 to 11.229 seconds, a 17.3 percent difference attributed mainly to fluctuations in disk I/O throughput within the Docker container.

### c. Load Imbalance Evidence

Although the static distribution strategy `all_files[i::p]` assigns the same number of files to every process, it cannot guarantee equal workloads when file sizes are heterogeneous. To quantify this imbalance, the local processing times and token counts reported by each rank were analyzed for Run 1. Tables II and III show this data for p = 4 and p = 8 respectively.

**TABLE II — Per-rank local times and token counts, mpi1.py with p = 4 (Run 1)**

| **Rank** | **Files** | **Local tokens** | **Local time (s)** |
|:--------:|:---------:|:----------------:|:------------------:|
| 0 | 750 | 10,788,141 | 9.168 |
| 1 | 750 | 11,064,823 | 9.110 |
| 2 | 750 | 11,573,938 | 9.547 |
| 3 | 750 | 11,524,556 | 9.552 |

**TABLE III — Per-rank local times and token counts, mpi1.py with p = 8 (Run 1)**

| **Rank** | **Files** | **Local tokens** | **Local time (s)** |
|:--------:|:---------:|:----------------:|:------------------:|
| 0 | 375 | 5,018,405 | 7.785 |
| 1 | 375 | 5,150,686 | 7.976 |
| 2 | 375 | 6,161,885 | 8.823 |
| 3 | 375 | 5,488,544 | 8.171 |
| 4 | 375 | 5,769,736 | 8.444 |
| 5 | 375 | 5,914,137 | 8.539 |
| 6 | 375 | 5,412,053 | 8.304 |
| 7 | 375 | 6,036,012 | 8.744 |

With p = 4, the difference in token count between the most loaded rank (rank 2, with 11,573,938 tokens) and the least loaded rank (rank 0, with 10,788,141 tokens) amounts to 785,797 tokens, a relative difference of 7.3 percent. This manifests as a 0.384-second spread in local processing times across the four processes.

With p = 8, the imbalance grows substantially more pronounced. Rank 2 processed 6,161,885 tokens while rank 0 processed only 5,018,405, a gap of 1,143,480 tokens, or 22.8 percent of the minimum load. The corresponding time difference between the slowest and fastest ranks reaches 1.038 seconds. The causal mechanism is straightforward: the round-robin distribution assigns files based on their alphabetical position in the sorted list, without accounting for the large variation in file sizes introduced by the corpus generator. The 10 percent of large files, each containing between 50,000 and 100,000 words, contribute a disproportionate share of the total token count, and their alphabetical positions determine which ranks inherit the heavier load.

The impact on total execution time is direct. The `comm.gather()` collective operation acts as a synchronization barrier — rank 0 cannot begin aggregating results until every process has finished its local computation. Processes that finish earlier must therefore wait idle at the barrier, wasting CPU cycles that could have been used for additional computation. This idle-waiting effect is a textbook manifestation of load imbalance in message-passing parallel programs [7], and it explains why the efficiency of `mpi1.py` drops from 0.93 at p = 2 to only 0.39 at p = 8.

### d. Implementation of MPI Version 2 Correcting the Imbalance

The second parallel implementation, `mpi2.py`, extends the architecture of `mpi1.py` by inserting an intelligent scheduling phase in rank 0 before files are distributed to the worker processes. The balancing strategy is a greedy algorithm known as **Longest Processing Time first (LPT)**, originally proposed by Graham in 1966 as a heuristic for scheduling independent tasks on identical parallel machines. The algorithm works as follows: rank 0 computes the size in bytes of each corpus file using `os.path.getsize()`, sorts the files in descending order of size, and then iterates through the sorted list, assigning each file to whichever process currently holds the smallest estimated cumulative load. This greedy approach does not guarantee an optimal distribution, but it produces solutions with a bounded deviation from the optimum that tends to be very small in practice. The rest of the execution flow (broadcast, local computation, gather, and aggregation) is identical to `mpi1.py`.

**TABLE IV — Execution time, speedup, and efficiency of mpi2.py (T_seq = 26.876594 s)**

| **p** | **Run 1 (s)** | **Run 2 (s)** | **Run 3 (s)** | **Average (s)** | **Speedup** | **Efficiency** |
|:-----:|:-------------:|:-------------:|:-------------:|:---------------:|:-----------:|:--------------:|
| 1 | 30.683933 | 30.163059 | 29.160260 | 30.002417 | 0.90 | 0.90 |
| 2 | 17.125671 | 16.993506 | 17.272314 | 17.130497 | 1.57 | 0.78 |
| 4 | 12.776809 | 12.783447 | 12.526671 | 12.695642 | 2.12 | 0.53 |
| 8 | 11.567369 | 11.246532 | 12.198686 | 11.670862 | 2.30 | 0.29 |

A striking observation is the result at p = 1. With a single process, `mpi2.py` averaged 30.002 seconds versus 26.795 seconds for `mpi1.py` in the same configuration. Since p = 1 involves no actual parallelism, this difference of 3.207 seconds precisely isolates and quantifies the sequential overhead introduced by the LPT scheduling phase — the cost of running `os.path.getsize()` on 3,000 files, sorting the resulting list, and executing the greedy assignment loop. With p = 8, the gap between the two implementations widens further: `mpi2.py` averaged 11.671 seconds while `mpi1.py` averaged 8.661 seconds, a difference of 34.7 percent.

**TABLE V — Per-rank local times and token counts, mpi2.py with p = 8 (Run 1)**

| **Rank** | **Files** | **Est. size (B)** | **Local tokens** | **Local time (s)** |
|:--------:|:---------:|:-----------------:|:----------------:|:------------------:|
| 0 | 376 | 34,381,755 | 5,620,840 | 7.051 |
| 1 | 375 | 34,381,731 | 5,619,966 | 7.305 |
| 2 | 374 | 34,381,770 | 5,617,956 | 7.297 |
| 3 | 375 | 34,381,802 | 5,618,676 | 7.363 |
| 4 | 375 | 34,381,787 | 5,618,493 | 6.988 |
| 5 | 375 | 34,381,696 | 5,618,576 | 7.467 |
| 6 | 375 | 34,381,794 | 5,618,127 | 7.066 |
| 7 | 375 | 34,381,724 | 5,618,824 | 7.118 |

The load-balance outcome is remarkably successful. The maximum difference in token count between any pair of ranks is just 2,884 tokens — 5,620,840 versus 5,617,956 — which is 0.05 percent of the maximum load. By comparison, `mpi1.py` exhibited a 22.8 percent token imbalance in the same configuration, meaning that `mpi2.py` reduced the load variance by a factor greater than 396. The estimated byte size assigned to each rank differs by less than 110 bytes across all eight processes — a relative difference of 0.0003 percent — confirming that the LPT algorithm functioned correctly and that file size serves as a reliable proxy for processing cost in this corpus.

Table VI consolidates the results of both implementations across all evaluated process counts, enabling a direct side-by-side comparison of their performance characteristics.

**TABLE VI — Summary comparison of mpi1.py vs. mpi2.py across all configurations**

| **p** | **MPI1 Avg (s)** | **MPI1 Sp** | **MPI1 Ep** | **MPI2 Avg (s)** | **MPI2 Sp** | **MPI2 Ep** |
|:-----:|:----------------:|:-----------:|:-----------:|:----------------:|:-----------:|:-----------:|
| 1 | 26.795 | 1.00 | 1.00 | 30.002 | 0.90 | 0.90 |
| 2 | 14.447 | 1.86 | 0.93 | 17.130 | 1.57 | 0.78 |
| 4 | 10.489 | 2.56 | 0.64 | 12.696 | 2.12 | 0.53 |
| 8 | 8.661 | 3.10 | 0.39 | 11.671 | 2.30 | 0.29 |

---

## 5. Analysis

### a. Did the first MPI implementation improve execution time compared to the sequential baseline?

Yes, clearly and consistently. The implementation `mpi1.py` reduced execution time from the baseline reference of 26.876 seconds to 14.447 seconds with p = 2, to 10.489 seconds with p = 4 (a 61.0 percent reduction), and to 8.661 seconds with p = 8 (a 67.8 percent reduction). The improvement is monotonic across all evaluated process counts, with each doubling of p producing a further reduction in execution time, although with diminishing returns. The consistency of results across three independent runs per configuration, together with verified output correctness, confirms that MPI-based data decomposition over the file set is an effective parallelization strategy for this problem.

The fact that `mpi1.py` with p = 1 averaged 26.795 seconds establishes that the overhead of the MPI runtime infrastructure is negligible at this problem scale. This means that the gains observed at p > 1 are genuinely attributable to parallelism, rather than to other implementation differences such as the tokenizer or the file-listing method.

### b. Was the observed speedup linear?

No. The ideal speedup with p processes is equal to p — that is, doubling the number of processes should halve the execution time — but the measured speedup values for `mpi1.py` were 1.00, 1.86, 2.56, and 3.10 for p = 1, 2, 4, and 8 respectively, all well below the corresponding ideal values of 1, 2, 4, and 8. This sublinear behavior is expected and has multiple concurrent causes that are well understood in the parallel computing literature.

The fundamental structural cause is **Amdahl's Law** [8], which states that if a fraction *s* of the program is inherently sequential, the maximum achievable speedup with p processes is bounded by:

```
S_p ≤ 1 / [s + (1 − s) / p]
```

In `mpi1.py`, the sequential fractions include reading `consulta.txt` and building the file list in rank 0, performing the broadcast, executing the gather, merging the partial counters, and writing the output CSV. Although each of these operations is fast in absolute terms, their relative contribution to total runtime increases as p grows and local computation time shrinks.

A second cause is the load imbalance documented in the previous section, which forces faster processes to idle at the gather barrier while waiting for the slowest one. A third cause, specific to the p = 8 configuration, is the use of `--oversubscribe` over only 7 physical cores. The eighth MPI process must time-share a core with another process, causing context-switching overhead that reduces the effective throughput of both competing processes and lowers the measured speedup below what would be obtained with 8 fully dedicated cores.

Applying Amdahl's Law directly to the experimental data allows the inherently sequential fraction of the program to be estimated quantitatively. Using the measured speedup of 3.10 at p = 8 and solving for s:

```
s = (1/S_p - 1/p) / (1 - 1/p) = (1/3.10 - 1/8) / (1 - 1/8) ≈ 0.16
```

This means that approximately **16 percent** of the total program execution is inherently sequential and cannot be parallelized regardless of how many processes are added. As a consequence, even with an arbitrarily large number of processes the maximum theoretical speedup for this program is bounded by 1/s ≈ **6.3**, well below the linear ideal. This estimate is consistent with the observed efficiency drop from 0.93 at p = 2 to 0.39 at p = 8, which reflects both the growing weight of the sequential fraction and the scheduling overhead introduced by oversubscription at p = 8.

### c. Is there evidence of load imbalance? How was it observed?

Yes, and the evidence is quantitative, reproducible, and progressively more severe as the process count increases. The imbalance was observed directly through the `local_time` and `local_tokens` values reported by each rank at the end of every run:

- **p = 2:** Token difference of 227,300 (1.0% of minimum load); local-time spread of 0.342 s.
- **p = 4:** Token gap of 785,797 (7.3%); local-time spread of 0.384 s.
- **p = 8:** Maximum token difference of 1,143,480 (22.8% of minimum load); slowest rank takes 1.038 s longer than the fastest.

The pattern of increasing imbalance with growing p has a clear causal explanation. As the number of processes increases, each one receives a smaller subset of files. With fewer files per process, the relative influence of the large files on the total workload of a given rank becomes larger and more variable. In statistical terms, the relative variance of the per-process load increases as the subset size decreases — an effect analogous to the law of large numbers: with fewer files to average over, the per-process load converges less reliably to the corpus-wide expected value per file.

### d. Did the second implementation reduce load imbalance?

Yes, and the reduction was dramatic. With p = 8, `mpi2.py` reduced the maximum token difference between ranks from 1,143,480 tokens to just 2,884 tokens, a relative imbalance of only **0.05 percent**. This represents a reduction in load variance by a **factor greater than 396**. The estimated byte sizes assigned to each rank differ by less than 110 bytes over a per-rank total of approximately 34.38 MB, a relative difference of 0.0003 percent, confirming that the LPT algorithm produced a near-optimal distribution and that file size reliably proxies processing cost in this corpus.

Even with this near-perfect load balance, the per-rank local times of `mpi2.py` with p = 8 still vary by 0.479 seconds (from 6.988 to 7.467 seconds). This residual variability demonstrates that sources of timing variation exist beyond the load imbalance itself — most notably fluctuations in disk I/O performance during concurrent file reads and in OS process scheduling. Eliminating the workload imbalance did not eliminate all sources of timing spread, but it did reduce the spread meaningfully compared to `mpi1.py`, where the spread was 1.038 seconds under the same configuration.

### e. Did the improved distribution strategy produce a real performance improvement?

No, not in terms of total execution time. Despite achieving near-perfect load balance, `mpi2.py` was consistently **slower** than `mpi1.py` across every evaluated process count:

- **p = 8:** 11.671 s vs. 8.661 s — a difference of **34.7 percent**
- **p = 4:** 12.696 s vs. 10.489 s — a difference of **21.0 percent**
- **p = 2:** 17.130 s vs. 14.447 s — a difference of **18.6 percent**

The cause of this counterintuitive result is the sequential overhead introduced by the scheduling phase of `mpi2.py`, which executes entirely in rank 0 before any process can begin local computation. This phase comprises three operations that `mpi1.py` does not perform: calling `os.path.getsize()` on all 3,000 corpus files, sorting the resulting list in descending order, and running the greedy assignment loop over all 3,000 files. The combined cost of these operations is directly measurable from the p = 1 results: `mpi2.py` took 30.002 seconds versus 26.795 seconds for `mpi1.py`, a **fixed overhead of 3.207 seconds** that is independent of the degree of parallelism and that penalizes `mpi2.py` at every process count.

This result does not invalidate the LPT-based distribution strategy as a general approach. It establishes that the strategy's cost-effectiveness depends on the scale of the problem. With a corpus of 3,000 files and per-process computation times of roughly 8 to 10 seconds, a fixed planning overhead of 3.2 seconds is too large a fraction of the total to be offset by a better load balance. With a much larger corpus the planning overhead would become negligible relative to the computation, and the balance improvement could translate into a meaningful reduction in total wall-clock time.

### f. What limitations affected your experiment?

The most significant limitation was the **hardware constraint** of the execution environment. The Docker container reported 7 logical cores via `nproc`, but the experimental protocol required testing with p = 8 MPI processes. This made it necessary to use `--oversubscribe`, which allows Open MPI to create more processes than there are available cores at the cost of forced CPU sharing between competing processes. When two MPI processes must time-share a single core, the OS kernel alternates between them through context switching, adding scheduling latency to both and causing the measured performance to fall below what would be obtained with 8 fully dedicated cores [4]. The reported speedup and efficiency values at p = 8 are therefore conservative estimates — the actual performance on hardware with genuine 8-core capacity would likely be higher.

A second limitation is that **file size in bytes is an imperfect estimator** of actual processing cost. The computational cost of tokenizing a file with `re.findall()` depends not only on the number of tokens but also on the density of regex-pattern matches, the average word length, and the character distribution within the file. For the synthetic Spanish-language corpus used in this laboratory, the correlation between file size and token count is very high. However, in corpora with more heterogeneous content — mixtures of source code, XML markup, richly formatted text, or multiple writing systems — this correlation could be substantially weaker, and the size-based scheduling heuristic would be less effective.

A third limitation is the **timing variability** introduced by the Docker virtualized filesystem. File access within a container passes through an additional layer of I/O virtualization compared to direct hardware access, and the latency of this layer can vary depending on the workload of the host system. This variability is visible in the p = 4 results of `mpi1.py`, where the three individual run times span a range of 1.651 seconds even though the program and the data are identical across runs. This level of timing noise cannot be fully controlled within the container-based laboratory framework.

---

## 6. Conclusions

This laboratory demonstrated that MPI-based parallelization produces measurable, reproducible, and significant improvements in the execution time of a word-counting workload over a 3,000-file text corpus. Both parallel implementations produced results that were identical to the sequential baseline across every evaluated configuration, validating the correctness of the data-distribution logic, the collective communication pattern, and the result-aggregation step in both implementations.

Both parallel implementations reduced execution time relative to the 26.876-second sequential baseline. The best overall performance was achieved by `mpi1.py` with p = 8 processes, which brought the total execution time down to **8.661 seconds**, a speedup of **3.10×** and a reduction of **67.8 percent**. This improvement, while sublinear compared to the theoretical ideal of 8×, is substantial from a practical standpoint and justifies the adoption of the parallel framework. The sublinear behavior is consistent with Amdahl's Law, which predicts that the inherently sequential portions of the program — the broadcast, gather, I/O operations, and result aggregation — impose a firm ceiling on the achievable speedup, and is compounded by oversubscription at p = 8.

The most important problem observed in the first parallel version was **load imbalance**. Although every process received the same number of files, the actual volume of work measured in tokens varied by as much as 22.8 percent between ranks at p = 8. This imbalance arises because the static round-robin distribution ignores file size, and the corpus contains a minority of very large files that contribute a disproportionate share of the total token count. The consequence is that faster processes must idle at the gather synchronization barrier, waiting for the slowest one to finish. This idle time grows with p and drives efficiency down from 0.93 at p = 2 to 0.39 at p = 8.

The second implementation, `mpi2.py`, addressed the imbalance through an LPT greedy scheduling algorithm that distributes files based on their estimated processing cost in bytes. With p = 8, the maximum token difference between any pair of ranks fell from 22.8 percent to just **0.05 percent** — a reduction by a factor of more than 396 — confirming that file size is a reliable proxy for processing cost in this corpus. Nevertheless, the balance improvement did not translate into better total execution time. The fixed sequential overhead of the scheduling phase in rank 0 (~3.2 seconds) exceeded the gain from the improved balance at every tested process count, making `mpi2.py` **34.7 percent slower** than `mpi1.py` at p = 8.

The evidence-based judgment is that **`mpi1.py` is the better-performing implementation** for this corpus size and execution environment. `mpi2.py` achieves superior load balance but at a planning cost that outweighs the benefit at this scale.

The overall experiment illustrates one of the most important principles in parallel algorithm design: **the cost of coordination must be proportional to the benefit it produces**, and the optimal distribution strategy always depends on the specific characteristics of the workload and the scale of the data being processed.

From an engineering standpoint, the experimental data provides a concrete criterion for deciding when the LPT strategy of `mpi2.py` becomes worthwhile. The scheduling overhead was measured at 3.207 seconds per run, independent of p. For this overhead to be recovered, the reduction in idle waiting time caused by a better load balance must exceed 3.207 seconds. With p = 8, the load imbalance in `mpi1.py` cost approximately 1.038 seconds of idle waiting time per run. For the balance improvement to offset the scheduling overhead at the same imbalance ratio, the local computation phase would need to be roughly **3.1 times longer**, which corresponds to a corpus approximately three times larger — around **9,000 files** at the same size distribution. At that scale, or under a size distribution with greater heterogeneity, `mpi2.py` would be the engineering-justified choice. This breakeven analysis transforms an empirical observation into a design guideline, which is the kind of engineering judgment that should inform the selection of parallelization strategies in production systems.

---

## References

[1] W. Gropp, E. Lusk, and A. Skjellum, [*Using MPI: Portable Parallel Programming with the Message-Passing Interface*](https://mitpress.mit.edu/9780262527392/using-mpi/), 3rd ed. Cambridge, MA, USA: MIT Press, 2014.

[2] C. D. Manning, P. Raghavan, and H. Schutze, [*Introduction to Information Retrieval*](https://nlp.stanford.edu/IR-book/). Cambridge, UK: Cambridge University Press, 2008.

[3] L. Dalcin, R. Paz, and M. Storti, "MPI for Python," *Journal of Parallel and Distributed Computing*, vol. 65, no. 9, pp. 1108–1115, 2005. DOI: [10.1016/j.jpdc.2005.03.010](https://doi.org/10.1016/j.jpdc.2005.03.010)

[4] E. Gabriel et al., "Open MPI: Goals, Concept, and Design of a Next Generation MPI Implementation," in *Proc. 11th European PVM/MPI Users' Group Meeting*, Budapest, Hungary, 2004, pp. 97–104. DOI: [10.1007/978-3-540-30218-6_19](https://doi.org/10.1007/978-3-540-30218-6_19)

[5] Python Software Foundation, "collections — Container datatypes," *Python 3 Documentation*. [Online]. Available: https://docs.python.org/3/library/collections.html

[6] W. Gropp, T. Hoefler, R. Thakur, and E. Lusk, [*Using Advanced MPI: Modern Features of the Message-Passing Interface*](https://mitpress.mit.edu/9780262527637/using-advanced-mpi/). Cambridge, MA, USA: MIT Press, 2014.

[7] R. Rabenseifner, G. Hager, and G. Jost, "Hybrid MPI/OpenMP Parallel Programming on Clusters of Multi-Core SMP Nodes," in *Proc. 17th Euromicro Int. Conf. on Parallel, Distributed and Network-Based Processing*, Weimar, Germany, 2009, pp. 427–436. DOI: [10.1109/PDP.2009.43](https://doi.org/10.1109/PDP.2009.43)

[8] G. M. Amdahl, "Validity of the single processor approach to achieving large scale computing capabilities," in *Proc. AFIPS Spring Joint Computer Conference*, Atlantic City, NJ, USA, 1967, pp. 483–485. DOI: [10.1145/1465482.1465560](https://doi.org/10.1145/1465482.1465560)
