# Parameters Reference

Every configuration parameter in PyTierra, with its si0 config key, Python attribute name, default value, and description.

## Soup

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| SoupSize | `soup_size` | 60000 | int | Total size of the soup memory in bytes |

## Time Slicing

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| SliceSize | `slice_size` | 25 | int | Base number of instructions per time slice |
| SizDepSlice | `siz_dep_slice` | 0 | int | 1 = scale slice size by creature size (larger creatures get more time) |
| SlicePow | `slice_pow` | 1.0 | float | Exponent for size-dependent slicing: `slice = base × (size/ref)^pow` |
| SliceStyle | `slice_style` | 2 | int | Slice variation style (2 = Tierra standard) |
| SlicFixFrac | `slic_fix_frac` | 0.0 | float | Fixed fraction added to slice |
| SlicRanFrac | `slic_ran_frac` | 2.0 | float | Random fraction range for slice variation |

## Mutation Rates

Rates are specified as "generations per event" — lower values mean more frequent mutation.

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| GenPerBkgMut | `gen_per_bkg_mut` | 32 | int | Generations between background (cosmic ray) mutations. 0 = disabled |
| GenPerFlaw | `gen_per_flaw` | 32 | int | Generations between execution flaws (±1 perturbation on arithmetic) |
| GenPerMovMut | `gen_per_mov_mut` | 0 | int | Generations between copy (movii) mutations. 0 = disabled |
| GenPerDivMut | `gen_per_div_mut` | 32 | int | Generations between division mutations |
| MutBitProp | `mut_bit_prop` | 0.2 | float | Probability that a mutation flips a single bit (vs. random instruction) |

## Genetic Operators

Applied during `divide` to the daughter genome.

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| GenPerCroInsSamSiz | `gen_per_cro_ins_sam_siz` | 32 | int | Crossover same-size instruction swap |
| GenPerInsIns | `gen_per_ins_ins` | 32 | int | Insert instruction |
| GenPerDelIns | `gen_per_del_ins` | 32 | int | Delete instruction |
| GenPerCroIns | `gen_per_cro_ins` | 32 | int | Crossover instruction |
| GenPerDelSeg | `gen_per_del_seg` | 32 | int | Delete segment |
| GenPerInsSeg | `gen_per_ins_seg` | 32 | int | Insert segment |
| GenPerCroSeg | `gen_per_cro_seg` | 32 | int | Crossover segment |

## Memory Allocation

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| MalMode | `mal_mode` | 1 | int | Allocation strategy: 0=first-fit, 1=better-fit, 2=random, 3=near-parent, 4=near-address |
| MalReapTol | `mal_reap_tol` | 1 | int | Number of reap attempts when soup is full |
| MalTol | `mal_tol` | 20 | int | Tolerance for better-fit: accept block up to N bytes larger |
| MaxFreeBlocks | `max_free_blocks` | 800 | int | Maximum number of free blocks before compaction |
| MalSamSiz | `mal_sam_siz` | 0 | int | 1 = require daughter same size as mother |

## Cell Constraints

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| MinCellSize | `min_cell_size` | 12 | int | Minimum allowed cell size in instructions |
| MinGenMemSiz | `min_gen_mem_siz` | 12 | int | Minimum genome memory size |
| MinTemplSize | `min_templ_size` | 1 | int | Minimum template length for search |
| MovPropThrDiv | `mov_prop_thr_div` | 0.7 | float | Fraction of daughter that must be copied before divide is allowed |
| SearchLimit | `search_limit` | 5 | int | Template search range as multiple of average cell size |

## Reaper

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| ReapRndProp | `reap_rnd_prop` | 0.3 | float | Fraction of reaper queue randomly shuffled (0 = pure fitness, 1 = random) |
| LazyTol | `lazy_tol` | 10 | int | Tolerance for lazy creatures (those not reproducing). Higher = more lenient |
| DropDead | `drop_dead` | 5 | int | Stop simulation after N million instructions with no reproduction. 0 = disabled |

## Division Constraints

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| DivSameGen | `div_same_gen` | 0 | int | 1 = require daughter has same genotype as mother |
| DivSameSiz | `div_same_siz` | 0 | int | 1 = require daughter has same size as mother |

## Disturbance

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| DistFreq | `dist_freq` | -0.3 | float | Frequency of mass kill events. Negative = fraction of recovery time |
| DistProp | `dist_prop` | 0.2 | float | Proportion of population killed per disturbance |
| EjectRate | `eject_rate` | 0 | int | Rate of random cell ejection |

## Memory Protection

Bit flags: 1=execute, 2=write, 4=read.

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| MemModeFree | `mem_mode_free` | 0 | int | Protection on free memory (0 = no protection) |
| MemModeMine | `mem_mode_mine` | 0 | int | Protection on own memory |
| MemModeProt | `mem_mode_prot` | 2 | int | Protection on other creatures' memory (2 = write-protected) |

## Genebank

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| DiskBank | `disk_bank` | 1 | int | 1 = enable disk genebank |
| GeneBnker | `gene_bnker` | 0 | int | Genebank mode |
| GenebankPath | `genebank_path` | "gb0/" | str | Directory for .tie genome files |
| SaveFreq | `save_freq` | 100 | int | Save frequency in millions of instructions |
| SavMinNum | `sav_min_num` | 10 | int | Minimum population to trigger disk save |
| SavThrMem | `sav_thr_mem` | 0.02 | float | Memory occupancy threshold for save |
| SavThrPop | `sav_thr_pop` | 0.02 | float | Population proportion threshold for save |

## Miscellaneous

| si0 Key | Attribute | Default | Type | Description |
|---------|-----------|---------|------|-------------|
| alive | `alive` | 0 | int | Reserved |
| new_soup | `new_soup` | 1 | int | 1 = initialize fresh soup |
| seed | `seed` | 0 | int | Random seed (0 = time-based) |
| debug | `debug` | 0 | int | Debug level |

## Computed Rates

These are calculated automatically from the `gen_per_*` settings and current population statistics. They are not set directly in config files.

| Attribute | Description |
|-----------|-------------|
| `rate_mut` | Per-instruction probability of background mutation |
| `rate_flaw` | Per-instruction probability of execution flaw |
| `rate_mov_mut` | Per-movii probability of copy mutation |
