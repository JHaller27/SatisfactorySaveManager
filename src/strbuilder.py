class StringBuilder:
    def __init__(self, padding: str = '\t'):
        self.depth = 0
        self.lines = []
        self.pad_str = padding

    def padding(self) -> None:
        return self.pad_str * self.depth

    def appendln(self, text: str) -> None:
        for line in text.split('\n'):
            if len(line) == 0:
                self.lines.append(line)
            else:
                self.lines.append('{}{}'.format(
                    self.padding(),
                    line
                ))

    def append(self, text: str) -> None:
        if len(self.lines) == 0:
            self.lines.append('')

        lines = text.split('\n')
        self.lines[-1].append(lines[0])
        if len(lines) > 0:
            for line in lines[1:]:
                self.appendln(line)

    def indent(self, amt: int = 1) -> None:
        self.depth += amt

    def unindent(self, amt: int = 1) -> None:
        self.depth -= amt if self.depth - amt >= 0 else 0

    def __str__(self) -> str:
        return '\n'.join(self.lines)


class UsesStringBuilder:
    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        raise NotImplementedError()
    def __str__(self):
        return str(self.to_sb())