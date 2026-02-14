# Genebank

The genebank tracks all genotypes that have ever existed in a simulation. It serves as both a runtime registry and a persistent archive.

## Naming Convention

Genotype names follow the Tierra convention:

```
NNNNxxx
```

- **NNNN** — genome size in decimal, zero-padded to 4 digits (e.g., `0080`)
- **xxx** — three-letter label within that size class (e.g., `aaa`, `aab`, `aac`)

Examples:
- `0080aaa` — the original 80-instruction ancestor
- `0045aaa` — the first 45-instruction genotype (typically a parasite)
- `0080aab` — a mutant of the ancestor, still 80 instructions

Labels are assigned sequentially within each size class. The first genotype of size N is always `NNNNaaa`, the second is `NNNNaab`, and so on through `NNNNzzz` (17,576 possible labels per size).

### Special Parent Names

- `0666god` — the "divine" parent of injected/inoculated organisms

## Runtime Genebank

The in-memory genebank (`pytierra.genebank.GeneBank`) tracks:

- **Genotype name** — assigned on first registration
- **Genome** — the raw instruction bytes
- **Population** — current number of living cells with this genotype
- **Max population** — highest population ever reached
- **Parent genotype** — name of the parent's genotype
- **Origin time** — instruction count when first seen

### Registration

When a cell divides, the daughter's genome is hashed and looked up in the genebank. If it matches an existing genotype, the population count is incremented. If it's new, a name is assigned and the genotype is registered.

### Genome Hashing

Genotypes are identified by a hash of their genome bytes within their size class. Two genomes of the same size with the same instruction sequence are the same genotype.

## SQLite Genebank (GUI)

The GUI's genebank window (`GenebankWindow`) stores genotypes in a SQLite database at:

```
~/.pytierra/genebank.db
```

### Schema

The database has a single `genotypes` table:

| Column | Type | Description |
|--------|------|-------------|
| name | TEXT PRIMARY KEY | Genotype name (e.g., `0080aaa`) |
| genome | BLOB | Raw instruction bytes |
| size | INTEGER | Genome size |
| max_pop | INTEGER | Highest population reached |
| origin_time | INTEGER | When first seen (instruction count) |
| parent | TEXT | Parent genotype name |
| last_seen | INTEGER | Last instruction count when population > 0 |

### Auto-Collection

Every ~2 seconds, the GUI checks all living genotypes against collection thresholds (configurable via `sav_min_num`, `sav_thr_mem`, `sav_thr_pop`). Qualifying genotypes are inserted or updated in the database.

## .tie File Format

Tierra genome files use the `.tie` extension. Format:

```
format: 3  bits: 0
genotype: 0080aaa  parent genotype: 0666god

CODE

track 0:

nop1    ; 0
nop1    ; 1
...
```

### Reading .tie Files

```python
from pytierra.genome_io import load_genome
genome = load_genome("path/to/0080aaa.tie")  # returns bytes
```

### Writing .tie Files

```python
from pytierra.genome_io import save_genome
save_genome("output.tie", genome_bytes, name="0080aaa", parent="0666god")
```

## Disk Genebank

The CLI simulation periodically saves qualifying genotypes to disk as `.tie` files in the `genebank_path` directory (default: `gb0/`). The save frequency is controlled by `save_freq` (in millions of instructions). A genotype is saved if it meets any of:

- Population >= `sav_min_num` (default: 10)
- Memory occupancy >= `sav_thr_mem` (default: 2%)
- Population proportion >= `sav_thr_pop` (default: 2%)

## Genebank Window Features

- **Filter** — search genotypes by name
- **Sort** — click column headers to sort by any field
- **Inspect** — view genome details
- **Inject** — reintroduce a stored genotype into the running soup
- **Export** — save as `.tie` file
- **Delete** — remove from the database
- **Refresh** — manually trigger collection from the running simulation
