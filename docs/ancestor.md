# Ancestor Organism: 0080aaa

The ancestor organism is an 80-instruction self-replicating program hand-written by Thomas Ray. It is the "mother of all other creatures" — every organism in a Tierra simulation descends from this genome.

## Overview

The ancestor performs four steps to replicate:

1. **Measure itself** — find its own start and end addresses using template search
2. **Allocate daughter** — request memory for a copy
3. **Copy itself** — instruction-by-instruction copy loop (as a subroutine)
4. **Divide** — split the copy as an independent organism, then loop

## Annotated Disassembly

### Beginning Marker (0–3)

```
 0  nop1    ; ┐
 1  nop1    ; │ Beginning marker: 1111
 2  nop1    ; │ Complement is 0000 (searched by adrb at line 9)
 3  nop1    ; ┘
```

### Self-Examination (4–22)

The creature measures its own size by finding the distance between its beginning and end markers.

```
 4  zero    ; cx = 0
 5  not0    ; cx = 1 (flip low bit)
 6  shl     ; cx = 2 (shift left)
 7  shl     ; cx = 4 (shift left again)
 8  movDC   ; dx = cx = 4 (save template length)
 9  adrb    ; Search backward for complement of next template → ax
10  nop0    ; ┐
11  nop0    ; │ Template: 0000 (complement of beginning marker 1111)
12  nop0    ; │ adrb returns address just after the match
13  nop0    ; ┘
14  subAAC  ; ax = ax - cx; cx was set to 4 (template length) by adrb
            ; ax now points to start of creature
15  movBA   ; bx = ax (bx = start address of mother)
16  adrf    ; Search forward for complement of next template → ax
17  nop0    ; ┐
18  nop0    ; │ Template: 0001 (complement of end marker 1110)
19  nop0    ; │ adrf returns address just after the match
20  nop1    ; ┘
21  incA    ; ax++ (include the dummy instruction after end marker)
22  subCAB  ; cx = ax - bx (cx = size of creature = 80)
```

After this block: `bx` = start of mother, `cx` = size (80), `ax` = end+1.

### Reproduction Loop (23–38)

```
23  nop1    ; ┐
24  nop1    ; │ Reproduction loop marker: 1101
25  nop0    ; │ (jumped to from line 34 after divide)
26  nop1    ; ┘
27  mal     ; Allocate cx bytes for daughter → ax = daughter address
28  call    ; Call copy procedure (search for complement of next template)
29  nop0    ; ┐
30  nop0    ; │ Template: 0011 (complement of copy procedure marker 1100)
31  nop1    ; │ call pushes return address (line 33) and jumps
32  nop1    ; ┘
33  divide  ; Create independent daughter cell from copied memory
34  jmpo    ; Jump to reproduction loop complement
35  nop0    ; ┐
36  nop0    ; │ Template: 0010 (complement of repro loop marker 1101)
37  nop1    ; │
38  nop0    ; ┘
```

After `divide`, the mother loops back to `mal` to allocate and copy again.

### Copy Procedure (39–74)

This is a subroutine called from line 28. On entry: `ax` = daughter start, `bx` = mother start, `cx` = size.

```
39  ifz     ; Dummy separator (never skips because cx > 0)
40  nop1    ; ┐
41  nop1    ; │ Copy procedure entry marker: 1100
42  nop0    ; │ (found by call at line 28)
43  nop0    ; ┘
44  pushA   ; Save ax (daughter address) on stack
45  pushB   ; Save bx (mother address) on stack
46  pushC   ; Save cx (size) on stack
```

#### Copy Loop (47–65)

```
47  nop1    ; ┐
48  nop0    ; │ Copy loop marker: 1010
49  nop1    ; │ (jumped to from line 61)
50  nop0    ; ┘
51  movii   ; Copy soup[bx] → soup[ax] (one instruction mother→daughter)
52  decC    ; cx-- (remaining bytes)
53  ifz     ; If cx == 0, execute next instruction; otherwise skip
54  jmpo    ; Jump to copy exit (when cx == 0, copy is done)
55  nop0    ; ┐
56  nop1    ; │ Template: 0100 (complement of exit marker 1011)
57  nop0    ; │
58  nop0    ; ┘
59  incA    ; ax++ (next daughter address)
60  incB    ; bx++ (next mother address)
61  jmpo    ; Jump back to copy loop marker
62  nop0    ; ┐
63  nop1    ; │ Template: 0101 (complement of copy loop marker 1010)
64  nop0    ; │
65  nop1    ; ┘
```

#### Copy Exit (66–74)

```
66  ifz     ; Dummy separator
67  nop1    ; ┐
68  nop0    ; │ Copy exit marker: 1011
69  nop1    ; │ (found by jmpo at line 54)
70  nop1    ; ┘
71  popC    ; Restore cx (size)
72  popB    ; Restore bx (mother start)
73  popA    ; Restore ax (daughter start)
74  ret     ; Return to caller (line 33: divide)
```

### End Marker (75–79)

```
75  nop1    ; ┐
76  nop1    ; │ End marker: 1110
77  nop1    ; │ Complement 0001 is searched by adrf at line 16
78  nop0    ; ┘
79  ifz     ; Dummy separator (terminates creature boundary)
```

## Template Summary

| Lines | Pattern | Purpose |
|-------|---------|---------|
| 0–3   | 1111 | Beginning marker |
| 23–26 | 1101 | Reproduction loop |
| 40–43 | 1100 | Copy procedure entry |
| 47–50 | 1010 | Copy loop |
| 67–70 | 1011 | Copy exit |
| 75–78 | 1110 | End marker |

## Evolutionary Potential

The ancestor is deliberately simple and somewhat wasteful:
- It uses 4-bit templates throughout (some could be shorter)
- The copy loop copies one instruction per iteration with no optimization
- It measures itself every reproduction cycle

These inefficiencies create evolutionary opportunities. Parasites (e.g., 0045aaa) emerge that are roughly half the size — they skip the copy procedure entirely and instead call the ancestor's copy subroutine, using its code to replicate themselves.
