from mpi4py import MPI
from collections import Counter
import os
import glob
import re
import csv


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

DATASET_DIR = "/app/dataset"
QUERY_FILE = os.path.join(DATASET_DIR, "consulta.txt")


def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)


def count_words_in_files(files, query_words):
    query_set = set(query_words)
    local_counter = Counter()
    total_tokens = 0

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().lower()
            tokens = tokenize(text)
            total_tokens += len(tokens)

            for token in tokens:
                if token in query_set:
                    local_counter[token] += 1

    return local_counter, total_tokens


def balanced_distribution_by_size(files, number_of_processes):
    """
    Greedy load balancing:
    1. Sort files from largest to smallest.
    2. Assign each next file to the process with the smallest accumulated size.
    """
    file_info = [(file_path, os.path.getsize(file_path)) for file_path in files]
    file_info.sort(key=lambda x: x[1], reverse=True)

    chunks = [[] for _ in range(number_of_processes)]
    loads = [0 for _ in range(number_of_processes)]

    for file_path, file_size in file_info:
        target_rank = loads.index(min(loads))
        chunks[target_rank].append(file_path)
        loads[target_rank] += file_size

    return chunks, loads


total_start = MPI.Wtime()

if rank == 0:
    with open(QUERY_FILE, "r", encoding="utf-8") as f:
        query_words = [line.strip().lower() for line in f if line.strip()]

    all_files = sorted(glob.glob(os.path.join(DATASET_DIR, "file_*.txt")))

    # Improved distribution: balance by file size
    chunks, estimated_loads = balanced_distribution_by_size(all_files, size)
else:
    query_words = None
    chunks = None
    estimated_loads = None

query_words = comm.bcast(query_words, root=0)
local_files = comm.scatter(chunks, root=0)

local_start = MPI.Wtime()
local_counts, local_tokens = count_words_in_files(local_files, query_words)
local_end = MPI.Wtime()

local_time = local_end - local_start
local_estimated_size = sum(os.path.getsize(file_path) for file_path in local_files)

all_counts = comm.gather(local_counts, root=0)
all_tokens = comm.gather(local_tokens, root=0)
all_local_times = comm.gather(local_time, root=0)
all_file_counts = comm.gather(len(local_files), root=0)
all_estimated_sizes = comm.gather(local_estimated_size, root=0)

print(
    f"Rank {rank}: assigned_files={len(local_files)}, "
    f"estimated_size={local_estimated_size}, "
    f"local_tokens={local_tokens}, local_time={local_time:.6f} seconds"
)

if rank == 0:
    global_counts = Counter()

    for partial_counter in all_counts:
        global_counts.update(partial_counter)

    total_end = MPI.Wtime()
    total_time = total_end - total_start

    print("\nDataset processed:", DATASET_DIR)
    print("Query file: consulta.txt")
    print("Files processed:", sum(all_file_counts))
    print("Total tokens read:", sum(all_tokens))
    print("Total occurrences found:", sum(global_counts.values()))
    print(f"Total execution time: {total_time:.6f} seconds")
    print(f"Execution time: {total_time:.6f} seconds")

    print("\nTop 10 palabras de consulta en el corpus:")
    for word, count in global_counts.most_common(10):
        print(f"  {word}: {count}")

    output_file = os.path.join(DATASET_DIR, "mpi2_results.csv")
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "count"])
        for word, count in global_counts.most_common():
            writer.writerow([word, count])

    print("\nProcess summary:")
    for i in range(size):
        print(
            f"Rank {i}: files={all_file_counts[i]}, "
            f"estimated_size={all_estimated_sizes[i]}, "
            f"local_time={all_local_times[i]:.6f} seconds"
        )

    print(f"\nResultados guardados en: {output_file}")