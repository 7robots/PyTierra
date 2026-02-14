"""CPU state: registers, stack, flags, instruction pointer."""

STACK_SIZE = 10


class CPU:
    __slots__ = ("ax", "bx", "cx", "dx", "ip", "sp", "stack", "flag_e", "flag_s", "flag_z", "_ip_modified")

    def __init__(self):
        self.ax: int = 0
        self.bx: int = 0
        self.cx: int = 0
        self.dx: int = 0
        self.ip: int = 0
        self.sp: int = 0
        self.stack: list[int] = [0] * STACK_SIZE
        self.flag_e: bool = False  # error
        self.flag_s: bool = False  # sign (negative)
        self.flag_z: bool = False  # zero
        self._ip_modified: bool = False

    def push(self, value: int) -> None:
        self.sp = (self.sp + 1) % STACK_SIZE
        self.stack[self.sp] = value

    def pop(self) -> int:
        value = self.stack[self.sp]
        self.sp = (self.sp - 1) % STACK_SIZE
        return value

    def set_flags(self, value: int) -> None:
        self.flag_z = (value == 0)
        self.flag_s = (value < 0)
        self.flag_e = False

    def get_reg(self, name: str) -> int:
        return getattr(self, name)

    def set_reg(self, name: str, value: int) -> None:
        setattr(self, name, value)

    def copy_from(self, other: "CPU") -> None:
        self.ax = other.ax
        self.bx = other.bx
        self.cx = other.cx
        self.dx = other.dx
        self.sp = other.sp
        self.stack = other.stack[:]
        self.flag_e = other.flag_e
        self.flag_s = other.flag_s
        self.flag_z = other.flag_z
