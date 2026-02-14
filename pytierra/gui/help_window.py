"""Help window with Tierra primer and reference material."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QTextBrowser


_HELP_HTML = """\
<html>
<head>
<style>
body { font-family: -apple-system, sans-serif; margin: 16px; line-height: 1.5; }
h1 { color: #2a82da; border-bottom: 2px solid #2a82da; padding-bottom: 4px; }
h2 { color: #3a9; margin-top: 20px; }
h3 { color: #666; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #888; padding: 4px 8px; text-align: left; }
th { background-color: #2a82da; color: white; }
tr:nth-child(even) { background-color: #f0f0f0; }
code { background-color: #eee; padding: 1px 4px; border-radius: 3px; font-size: 13px; }
kbd { background-color: #ddd; border: 1px solid #aaa; border-radius: 3px;
      padding: 1px 5px; font-size: 12px; font-family: monospace; }
.group { color: #666; font-style: italic; }
</style>
</head>
<body>

<h1>PyTierra Help</h1>

<h2>What is Tierra?</h2>
<p>Tierra is an artificial life system created by <b>Thomas S. Ray</b> in 1991.
It simulates Darwinian evolution inside a computer. Digital organisms (creatures)
are self-replicating programs that live in a shared block of memory called the
<i>soup</i>. They compete for CPU time and memory space, and through mutation
and natural selection, they evolve new strategies for survival.</p>

<p>PyTierra is a faithful Python reimplementation of Tierra 6.02, the final
release of Ray's original C implementation.</p>

<h2>The Soup</h2>
<p>The soup is a contiguous array of memory (typically 60,000 bytes). Each byte
holds one instruction from a 32-instruction set. Creatures occupy contiguous
blocks within the soup. Free memory is scattered between living creatures.</p>

<p>The soup view displays each memory address as a colored pixel. Colors correspond
to instruction types: blue for NOPs, green for arithmetic, yellow for stack
operations, red for control flow, purple for moves, cyan for addressing,
and white/pink for memory allocation and division.</p>

<h2>Creatures</h2>
<p>A creature is a contiguous block of machine code in the soup, plus a virtual
CPU with four registers (AX, BX, CX, DX), a 10-deep stack, an instruction
pointer (IP), and three flags (Error, Sign, Zero).</p>

<p>Each creature receives a <b>time slice</b> — a fixed number of instructions
to execute per turn. The scheduler cycles through all living creatures in order.
When a creature executes enough faulty operations, the reaper removes it from
the soup to free memory for others.</p>

<h2>Self-Replication</h2>
<p>The ancestor organism (0080aaa, 80 instructions) replicates itself by:</p>
<ol>
<li>Measuring its own size using template search (<code>adrb</code>/<code>adrf</code>)</li>
<li>Allocating memory for a daughter cell (<code>mal</code>)</li>
<li>Copying itself instruction by instruction (<code>movii</code>) in a loop</li>
<li>Dividing to create the daughter as an independent cell (<code>divide</code>)</li>
</ol>

<h2>Evolution</h2>
<p>Evolution arises from three forces:</p>
<ul>
<li><b>Mutation:</b> Random bit-flips in the soup (cosmic rays), copy errors
during replication, and execution flaws that perturb arithmetic.</li>
<li><b>Selection:</b> Creatures compete for CPU time and memory. Efficient
replicators leave more offspring. The reaper kills the least fit.</li>
<li><b>Genetic drift:</b> Small populations experience random fluctuations.</li>
</ul>

<h2>Instruction Set</h2>
<p>PyTierra uses the Tierra 6.02 instruction set (32 instructions, 5-bit opcodes):</p>

<table>
<tr><th>Op</th><th>Mnemonic</th><th>Description</th></tr>
<tr><td>00</td><td>nop0</td><td>No operation (template bit 0)</td></tr>
<tr><td>01</td><td>nop1</td><td>No operation (template bit 1)</td></tr>
<tr class="group"><td colspan="3"><i>Arithmetic</i></td></tr>
<tr><td>02</td><td>not0</td><td>Flip low bit of CX</td></tr>
<tr><td>03</td><td>shl</td><td>Shift CX left by 1</td></tr>
<tr><td>04</td><td>zero</td><td>Set CX to 0</td></tr>
<tr><td>05</td><td>ifz</td><td>Skip next instruction if CX != 0</td></tr>
<tr><td>06</td><td>subCAB</td><td>CX = AX - BX</td></tr>
<tr><td>07</td><td>subAAC</td><td>AX = AX - CX</td></tr>
<tr><td>08</td><td>incA</td><td>Increment AX</td></tr>
<tr><td>09</td><td>incB</td><td>Increment BX</td></tr>
<tr><td>10</td><td>decC</td><td>Decrement CX</td></tr>
<tr><td>11</td><td>incC</td><td>Increment CX</td></tr>
<tr class="group"><td colspan="3"><i>Stack Operations</i></td></tr>
<tr><td>12</td><td>pushA</td><td>Push AX onto stack</td></tr>
<tr><td>13</td><td>pushB</td><td>Push BX onto stack</td></tr>
<tr><td>14</td><td>pushC</td><td>Push CX onto stack</td></tr>
<tr><td>15</td><td>pushD</td><td>Push DX onto stack</td></tr>
<tr><td>16</td><td>popA</td><td>Pop into AX</td></tr>
<tr><td>17</td><td>popB</td><td>Pop into BX</td></tr>
<tr><td>18</td><td>popC</td><td>Pop into CX</td></tr>
<tr><td>19</td><td>popD</td><td>Pop into DX</td></tr>
<tr class="group"><td colspan="3"><i>Control Flow</i></td></tr>
<tr><td>20</td><td>jmpo</td><td>Jump outward (bidirectional template match)</td></tr>
<tr><td>21</td><td>jmpb</td><td>Jump backward (backward template match)</td></tr>
<tr><td>22</td><td>call</td><td>Call: push return addr, jump to template match</td></tr>
<tr><td>23</td><td>ret</td><td>Return: pop address and jump</td></tr>
<tr class="group"><td colspan="3"><i>Data Movement</i></td></tr>
<tr><td>24</td><td>movDC</td><td>DX = CX</td></tr>
<tr><td>25</td><td>movBA</td><td>BX = AX</td></tr>
<tr><td>26</td><td>movii</td><td>Copy [BX] to [AX] (write to daughter only)</td></tr>
<tr class="group"><td colspan="3"><i>Addressing</i></td></tr>
<tr><td>27</td><td>adro</td><td>Find template outward, result in AX, size in CX</td></tr>
<tr><td>28</td><td>adrb</td><td>Find template backward</td></tr>
<tr><td>29</td><td>adrf</td><td>Find template forward</td></tr>
<tr class="group"><td colspan="3"><i>Memory &amp; Division</i></td></tr>
<tr><td>30</td><td>mal</td><td>Allocate CX bytes for daughter cell</td></tr>
<tr><td>31</td><td>divide</td><td>Split daughter as independent organism</td></tr>
</table>

<h2>Keyboard Shortcuts</h2>
<table>
<tr><th>Key</th><th>Action</th></tr>
<tr><td><kbd>Space</kbd></td><td>Play / Pause simulation</td></tr>
<tr><td><kbd>Right</kbd></td><td>Step one time slice</td></tr>
<tr><td><kbd>]</kbd></td><td>Speed up</td></tr>
<tr><td><kbd>[</kbd></td><td>Speed down</td></tr>
<tr><td><kbd>Cmd+N</kbd></td><td>New Soup</td></tr>
<tr><td><kbd>Cmd+O</kbd></td><td>Open Session</td></tr>
<tr><td><kbd>Cmd+S</kbd></td><td>Save Session</td></tr>
<tr><td><kbd>Cmd+G</kbd></td><td>Open Genebank</td></tr>
<tr><td><kbd>Cmd++</kbd></td><td>Zoom In</td></tr>
<tr><td><kbd>Cmd+-</kbd></td><td>Zoom Out</td></tr>
<tr><td><kbd>Cmd+0</kbd></td><td>Zoom to Fit</td></tr>
<tr><td><kbd>F1</kbd></td><td>This Help Window</td></tr>
</table>

<h2>Controls Reference</h2>
<h3>Toolbar</h3>
<ul>
<li><b>Play/Pause:</b> Start or stop the simulation.</li>
<li><b>Step:</b> Execute one time slice for the current creature.</li>
<li><b>Speed Slider:</b> Logarithmic scale from 1 to 10,000 slices per tick.</li>
</ul>

<h3>Tabs</h3>
<ul>
<li><b>Debug:</b> CPU state of the selected creature — registers, flags, stack,
live disassembly centered on the instruction pointer.</li>
<li><b>Inspect:</b> Full genome disassembly of a selected genotype. Copy to clipboard.</li>
<li><b>Inventory:</b> Sortable table of all living genotypes with population counts.
Click to inspect.</li>
<li><b>Graphs:</b> Real-time plots — population, mean size, fitness, genotype count,
soup fullness, IPS. Also size histogram and genotype frequency bar charts.</li>
<li><b>Mutations:</b> Configure mutation rates and genetic operators. Presets for
quick adjustment.</li>
<li><b>Selection:</b> Time slice and reaper settings that control selection pressure.</li>
<li><b>Settings:</b> Memory allocation mode, division constraints, disturbance, and
other advanced parameters.</li>
</ul>

<h3>View Overlays</h3>
<ul>
<li><b>Show Cells:</b> Color each creature's memory by genotype.</li>
<li><b>Show IPs:</b> Bright green dots at each creature's instruction pointer.</li>
<li><b>Show Fecundity:</b> Yellow-orange heat on occupied memory.</li>
</ul>

<h3>Genebank Window</h3>
<p>The genebank stores genotypes in a SQLite database (<code>~/.pytierra/genebank.db</code>).
Genotypes are auto-collected when their population exceeds thresholds. You can
filter, inspect, export (.tie format), inject back into the soup, or delete entries.</p>

</body>
</html>
"""


class HelpWindow(QMainWindow):
    """Window displaying Tierra primer and reference help."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyTierra Help")
        self.resize(700, 800)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_HELP_HTML)
        self.setCentralWidget(browser)
