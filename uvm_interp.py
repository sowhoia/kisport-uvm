import argparse
import xml.etree.ElementTree as ET
from typing import List, Tuple

# python uvm_interp.py -i emu-output.bin -o dump.xml -r "0-32"

OPCODES = {
    14: "load_const",
    4: "read_mem",
    2: "write_mem",
    1: "sub_mem",
}


def mask(bits: int) -> int:
    return (1 << bits) - 1


def ensure_memory_size(memory: List[int], addr: int) -> None:
    if addr >= len(memory):
        memory.extend([0] * (addr + 1 - len(memory)))


def execute(bytecode: bytes) -> Tuple[List[int], List[int]]:
    registers = [0] * 128  # 7-битные адреса регистров
    memory = [0] * 256     # данные расширяются по мере необходимости

    if len(bytecode) % 3 != 0:
        raise ValueError("Длина машинного кода должна быть кратна 3 байтам")

    for i in range(0, len(bytecode), 3):
        command = int.from_bytes(bytecode[i : i + 3], "little")
        opcode = command & mask(4)
        if opcode not in OPCODES:
            raise ValueError(f"Неизвестный opcode: {opcode}")

        if opcode == 14:  # load_const
            reg = (command >> 4) & mask(7)
            const = (command >> 11) & mask(12)
            registers[reg] = const
        elif opcode == 4:  # read_mem
            dst = (command >> 4) & mask(7)
            ptr_reg = (command >> 11) & mask(7)
            addr = registers[ptr_reg]
            ensure_memory_size(memory, addr)
            registers[dst] = memory[addr]
        elif opcode == 2:  # write_mem
            ptr_reg = (command >> 4) & mask(7)
            src_reg = (command >> 11) & mask(7)
            addr = registers[ptr_reg]
            ensure_memory_size(memory, addr)
            memory[addr] = registers[src_reg]
        elif opcode == 1:  # sub_mem
            offset = (command >> 4) & mask(5)
            base_reg = (command >> 9) & mask(7)
            src_reg = (command >> 16) & mask(7)
            addr = registers[base_reg] + offset
            ensure_memory_size(memory, addr)
            memory[addr] = memory[addr] - registers[src_reg]
    return registers, memory


def parse_range(range_value: str) -> Tuple[int, int]:
    start, end = range_value.split("-")
    start_i, end_i = int(start), int(end)
    if start_i > end_i:
        start_i, end_i = end_i, start_i
    return start_i, end_i


def dump_xml(memory: List[int], registers: List[int], start: int, end: int, output: str) -> None:
    root = ET.Element("uvm_dump")
    regs_el = ET.SubElement(root, "registers")
    for idx, value in enumerate(registers):
        reg_el = ET.SubElement(regs_el, "reg", index=str(idx))
        reg_el.text = str(value)

    memory_el = ET.SubElement(root, "memory", start=str(start), end=str(end))
    for addr in range(start, end + 1):
        value = memory[addr] if addr < len(memory) else 0
        cell = ET.SubElement(memory_el, "cell", address=str(addr))
        cell.text = str(value)

    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Путь к бинарному файлу с программой")
    parser.add_argument("-o", "--output", required=True, help="Файл для дампа памяти в XML")
    parser.add_argument("-r", "--range", required=True, help='Диапазон адресов для дампа, например "0-32"')
    args = parser.parse_args()

    start, end = parse_range(args.range)
    with open(args.input, "rb") as file:
        bytecode = file.read()

    registers, memory = execute(bytecode)
    dump_xml(memory, registers, start, end, args.output)
    print(f"Дамп памяти записан в {args.output}")


if __name__ == "__main__":
    main()