# Instruction Set

PyTierra uses the Tierra 6.02 instruction set: 32 instructions encoded as 5-bit opcodes (values 0–31). Higher bits in a byte are ignored (opcode = byte % 32).

## Template Matching

Several instructions use **template matching**: they scan the soup for a complementary pattern of `nop0`/`nop1` instructions. A template is a consecutive sequence of `nop0` (0) and `nop1` (1) immediately following the instruction. The complement swaps each bit: `nop0` ↔ `nop1`.

Search directions:
- **Outward (o):** alternates forward and backward from the current IP
- **Forward (f):** searches only ahead
- **Backward (b):** searches only behind

The search range is limited to `search_limit × average_cell_size` addresses.

## Instructions

### NOPs (Templates)

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 0  | `nop0`   | No operation; template bit 0 | — |
| 1  | `nop1`   | No operation; template bit 1 | — |

### Arithmetic

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 2  | `not0`   | Flip low bit of CX | `cx ^= 1` |
| 3  | `shl`    | Shift CX left 1 | `cx <<= 1` |
| 4  | `zero`   | Zero CX | `cx = 0` |
| 5  | `ifz`    | Conditional skip | `if cx != 0: skip next` |
| 6  | `subCAB` | Subtract | `cx = ax - bx` |
| 7  | `subAAC` | Subtract | `ax = ax - cx` |
| 8  | `incA`   | Increment AX | `ax += 1` |
| 9  | `incB`   | Increment BX | `bx += 1` |
| 10 | `decC`   | Decrement CX | `cx -= 1` |
| 11 | `incC`   | Increment CX | `cx += 1` |

### Stack Operations

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 12 | `pushA`  | Push AX | `stack[sp++] = ax` |
| 13 | `pushB`  | Push BX | `stack[sp++] = bx` |
| 14 | `pushC`  | Push CX | `stack[sp++] = cx` |
| 15 | `pushD`  | Push DX | `stack[sp++] = dx` |
| 16 | `popA`   | Pop to AX | `ax = stack[--sp]` |
| 17 | `popB`   | Pop to BX | `bx = stack[--sp]` |
| 18 | `popC`   | Pop to CX | `cx = stack[--sp]` |
| 19 | `popD`   | Pop to DX | `dx = stack[--sp]` |

### Control Flow

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 20 | `jmpo`   | Jump outward | `ip = find_template(outward)` |
| 21 | `jmpb`   | Jump backward | `ip = find_template(backward)` |
| 22 | `call`   | Call subroutine | `push(return_addr); ip = find_template(outward)` |
| 23 | `ret`    | Return | `ip = pop()` |

All template-based jumps set the error flag (E) if no match is found, and skip past the template.

### Data Movement

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 24 | `movDC`  | Move CX to DX | `dx = cx` |
| 25 | `movBA`  | Move AX to BX | `bx = ax` |
| 26 | `movii`  | Indirect copy | `soup[ax] = soup[bx]` (write to daughter memory only) |

`movii` enforces memory protection: the destination (AX) must be in the creature's allocated daughter memory. Copy mutations may occur based on `rate_mov_mut`.

### Addressing

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 27 | `adro`   | Address outward | `ax = find_template(outward); cx = template_length` |
| 28 | `adrb`   | Address backward | `ax = find_template(backward); cx = template_length` |
| 29 | `adrf`   | Address forward | `ax = find_template(forward); cx = template_length` |

These find the address of a complementary template without jumping. The address goes into AX and the template length into CX.

### Memory & Division

| Op | Mnemonic | Description | Pseudo-code |
|----|----------|-------------|-------------|
| 30 | `mal`    | Allocate daughter | `ax = allocate(cx bytes)` |
| 31 | `divide` | Create daughter cell | Split daughter memory as independent organism |

`mal` allocates CX bytes of soup memory for the daughter cell. The address is returned in AX. If the soup is full, the reaper kills a creature to make room.

`divide` validates that enough instructions were copied (`mov_prop_thr_div`), then creates a new independent organism from the daughter memory. The daughter gets its own CPU, joins the scheduler, and begins executing.

## Execution Flaws

Most arithmetic and data-movement instructions are subject to **execution flaws**: with probability `rate_flaw`, the operation is perturbed by ±1. This provides a subtle source of variation beyond copy mutation.

## Flags

- **E (Error):** Set when an operation fails (template not found, memory violation, etc.)
- **S (Sign):** Set when the result of an arithmetic operation is negative
- **Z (Zero):** Set when the result is zero
