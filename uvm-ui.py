from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, TextArea

from uvm_asm import full_asm
from uvm_interp import execute

DEMO = """
# Вариант №4: простое вычитание из памяти
r0 = 0          # базовый адрес
r1 = 10         # значение
mem[r0] = r1    # mem[0] = 10
r2 = 3
mem[r0 + 0] -= r2   # mem[0] = 10 - 3
r3 = mem[r0]   # читаем результат в r3
""".strip()

TEMPLATE = """
IR: {ir}
bytecode: {bytecode}
registers[0:8]: {registers}
memory[0:15]: {memory}
""".strip()


def format_memory(mem, limit=16):
    return {i: (mem[i] if i < len(mem) else 0) for i in range(limit)}


class ClockApp(App):
    CSS = """
    Screen { align: center middle; }
    Digits { width: auto; }
    """

    def compose(self) -> ComposeResult:
        yield TextArea(text=DEMO, id="input")
        yield Button(label="start", id="main")
        yield TextArea(id="output", text=" ")

    @on(Button.Pressed, "#main")
    def click(self) -> None:
        program = self.query_one("#input").text
        bytecode, ir = full_asm(program)
        registers, memory = execute(bytecode)
        textcode = " ".join(f"{b:02x}" for b in bytecode)
        self.query_one("#output").text = TEMPLATE.format(
            ir=ir,
            bytecode=textcode,
            registers=registers[:8],
            memory=format_memory(memory),
        )


app = ClockApp()
app.run()
