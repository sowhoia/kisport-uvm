import argparse
import pprint
import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

# python uvm_asm.py -i emu-program.asm -o emu-output.bin -t 1
# Вариант №4: алгебраический синтаксис и 3-байтные инструкции.

OPCODES = {
    "load_const": 14,   # rB = C
    "read_mem": 4,      # rB = mem[rC]
    "write_mem": 2,     # mem[rB] = rC
    "sub_mem": 1,       # mem[rC + B] -= rD
}


def mask(bits: int) -> int:
    return (1 << bits) - 1


def _ensure_range(value: int, bits: int, name: str) -> None:
    if not (0 <= value <= mask(bits)):
        raise ValueError(f"{name}={value} не помещается в {bits} бит")


@dataclass
class Instruction:
    name: str
    A: int
    B: int
    C: int | None = None
    D: int | None = None

    def to_bytes(self) -> bytes:
        if self.name == "load_const":
            _ensure_range(self.B, 7, "B (reg)")
            _ensure_range(self.C, 12, "C (const)")
            command = self.A | (self.B << 4) | (self.C << 11)
        elif self.name == "read_mem":
            _ensure_range(self.B, 7, "B (dst reg)")
            _ensure_range(self.C, 7, "C (addr reg)")
            command = self.A | (self.B << 4) | (self.C << 11)
        elif self.name == "write_mem":
            _ensure_range(self.B, 7, "B (addr reg)")
            _ensure_range(self.C, 7, "C (src reg)")
            command = self.A | (self.B << 4) | (self.C << 11)
        elif self.name == "sub_mem":
            _ensure_range(self.B, 5, "B (offset)")
            _ensure_range(self.C, 7, "C (base reg)")
            _ensure_range(self.D, 7, "D (src reg)")
            command = self.A | (self.B << 4) | (self.C << 9) | (self.D << 16)
        else:
            raise ValueError(f"Неизвестная операция {self.name}")
        return command.to_bytes(3, "little")

    def fields(self) -> dict:
        payload = {"op": self.name, "A": self.A, "B": self.B}
        if self.C is not None:
            payload["C"] = self.C
        if self.D is not None:
            payload["D"] = self.D
        return payload


LOAD_CONST_RE = re.compile(r"^r(?P<B>\d+)\s*=\s*(?P<C>\d+)$")
READ_RE = re.compile(r"^r(?P<B>\d+)\s*=\s*mem\[\s*r(?P<C>\d+)\s*]$")
WRITE_RE = re.compile(r"^mem\[\s*r(?P<B>\d+)\s*]\s*=\s*r(?P<C>\d+)$")
SUB_RE = re.compile(r"^mem\[\s*r(?P<C>\d+)\s*\+\s*(?P<B>\d+)\s*]\s*-\=\s*r(?P<D>\d+)$")
SUB_EQ_RE = re.compile(
    r"^mem\[\s*r(?P<C>\d+)\s*\+\s*(?P<B>\d+)\s*]\s*=\s*mem\[\s*r(?P<C2>\d+)\s*\+\s*(?P<B2>\d+)\s*]\s*-\s*r(?P<D>\d+)$"
)


def parse_line(line: str) -> Instruction:
    line = line.split("#", 1)[0].strip()
    if not line:
        return None

    if match := LOAD_CONST_RE.match(line):
        return Instruction("load_const", OPCODES["load_const"], int(match["B"]), int(match["C"]))
    if match := READ_RE.match(line):
        return Instruction("read_mem", OPCODES["read_mem"], int(match["B"]), int(match["C"]))
    if match := WRITE_RE.match(line):
        return Instruction("write_mem", OPCODES["write_mem"], int(match["B"]), int(match["C"]))
    if match := SUB_RE.match(line):
        return Instruction("sub_mem", OPCODES["sub_mem"], int(match["B"]), int(match["C"]), int(match["D"]))
    if match := SUB_EQ_RE.match(line):
        if int(match["B"]) != int(match["B2"]) or int(match["C"]) != int(match["C2"]):
            raise ValueError("Для вычитания адреса в левой и правой части должны совпадать")
        return Instruction("sub_mem", OPCODES["sub_mem"], int(match["B"]), int(match["C"]), int(match["D"]))
    raise ValueError(f"Не удалось разобрать строку: {line}")


def asm(ir: Iterable[Instruction]) -> bytes:
    return b"".join(instr.to_bytes() for instr in ir)


def full_asm(text: str) -> Tuple[bytes, List[dict]]:
    ir: List[Instruction] = []
    for raw_line in text.splitlines():
        instr = parse_line(raw_line)
        if instr:
            ir.append(instr)
    bytecode = asm(ir)
    return bytecode, [instr.fields() for instr in ir]


def test():
    # Проверки из спецификации варианта №4
    assert list(Instruction("load_const", 14, 34, 686).to_bytes()) == [0x2E, 0x72, 0x15]
    assert list(Instruction("read_mem", 4, 103, 29).to_bytes()) == [0x74, 0xEE, 0x00]
    assert list(Instruction("write_mem", 2, 74, 62).to_bytes()) == [0xA2, 0xF4, 0x01]
    assert list(Instruction("sub_mem", 1, 3, 13, 94).to_bytes()) == [0x31, 0x1A, 0x5E]


def main():
    test()
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Файл с программой в алгебраическом синтаксисе")
    parser.add_argument("-o", "--output", required=True, help="Файл для сохранения машинного кода")
    parser.add_argument("-t", "--test", required=True, help="Режим тестирования (1/0)")
    args = parser.parse_args()

    with open(args.input) as file:
        text = file.read()

    bytecode, ir = full_asm(text)
    with open(args.output, "wb") as output_file:
        output_file.write(bytecode)

    print(f"Собрано команд: {len(ir)}")
    if args.test == "1":
        pprint.pprint(ir)
        print(" ".join(hex(b) for b in bytecode))


if __name__ == "__main__":
    main()
