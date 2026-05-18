# Automatically Collected Experimental Results

These results were generated from the saved raw outputs.

- Sequential baseline time (`Tseq`): `26.876594 seconds`
- Docker available cores: `7`

### MPI1 Timing Results

| Processes | Run 1 (s) | Run 2 (s) | Run 3 (s) | Average Time (s) | Speedup | Efficiency |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 28.079709 | 25.431295 | 26.874339 | 26.795114 | 1.00 | 1.00 |
| 2 | 14.530604 | 14.255729 | 14.553288 | 14.446540 | 1.86 | 0.93 |
| 4 | 9.577585 | 11.229220 | 10.660970 | 10.489258 | 2.56 | 0.64 |
| 8 | 8.943007 | 8.288741 | 8.750497 | 8.660748 | 3.10 | 0.39 |

### MPI2 Timing Results

| Processes | Run 1 (s) | Run 2 (s) | Run 3 (s) | Average Time (s) | Speedup | Efficiency |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.683933 | 30.163059 | 29.160260 | 30.002417 | 0.90 | 0.90 |
| 2 | 17.125671 | 16.993506 | 17.272314 | 17.130497 | 1.57 | 0.78 |
| 4 | 12.776809 | 12.783447 | 12.526671 | 12.695642 | 2.12 | 0.53 |
| 8 | 11.567369 | 11.246532 | 12.198686 | 11.670862 | 2.30 | 0.29 |

## Representative Local Processing Times by Rank

The following tables correspond to Run 1 for each process configuration. They are useful as evidence for load-balance analysis.

### MPI1 Local Times

#### MPI1 with 1 process - Run 1

| Rank | Assigned Files | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|
| 0 | 3000 | 44951458 | 28.043346 |

#### MPI1 with 2 processes - Run 1

| Rank | Assigned Files | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|
| 0 | 1500 | 22362079 | 14.493528 |
| 1 | 1500 | 22589379 | 14.151747 |

#### MPI1 with 4 processes - Run 1

| Rank | Assigned Files | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|
| 0 | 750 | 10788141 | 9.168005 |
| 1 | 750 | 11064823 | 9.109573 |
| 2 | 750 | 11573938 | 9.546983 |
| 3 | 750 | 11524556 | 9.551571 |

#### MPI1 with 8 processes - Run 1

| Rank | Assigned Files | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|
| 0 | 375 | 5018405 | 7.785249 |
| 1 | 375 | 5150686 | 7.975957 |
| 2 | 375 | 6161885 | 8.823153 |
| 3 | 375 | 5488544 | 8.171050 |
| 4 | 375 | 5769736 | 8.444104 |
| 5 | 375 | 5914137 | 8.539361 |
| 6 | 375 | 5412053 | 8.303817 |
| 7 | 375 | 6036012 | 8.743710 |

### MPI2 Local Times

#### MPI2 with 1 process - Run 1

| Rank | Assigned Files | Estimated Size | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|---:|
| 0 | 3000 | 275054059 | 44951458 | 24.940198 |

#### MPI2 with 2 processes - Run 1

| Rank | Assigned Files | Estimated Size | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|---:|
| 0 | 1499 | 137527044 | 22474059 | 12.576859 |
| 1 | 1501 | 137527015 | 22477399 | 12.880224 |

#### MPI2 with 4 processes - Run 1

| Rank | Assigned Files | Estimated Size | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|---:|
| 0 | 750 | 68763511 | 11239261 | 8.336632 |
| 1 | 750 | 68763524 | 11237297 | 8.289663 |
| 2 | 751 | 68763489 | 11236601 | 8.397432 |
| 3 | 749 | 68763535 | 11238299 | 8.306593 |

#### MPI2 with 8 processes - Run 1

| Rank | Assigned Files | Estimated Size | Local Tokens | Local Time (s) |
|---:|---:|---:|---:|---:|
| 0 | 376 | 34381755 | 5620840 | 7.050991 |
| 1 | 375 | 34381731 | 5619966 | 7.305400 |
| 2 | 374 | 34381770 | 5617956 | 7.296909 |
| 3 | 375 | 34381802 | 5618676 | 7.363406 |
| 4 | 375 | 34381787 | 5618493 | 6.987812 |
| 5 | 375 | 34381696 | 5618576 | 7.466833 |
| 6 | 375 | 34381794 | 5618127 | 7.066424 |
| 7 | 375 | 34381724 | 5618824 | 7.117627 |
