from strbuilder import StringBuilder, UsesStringBuilder


COMPRESSED_FILE_FORMAT_MIN_VERSION = 21


def s2hms(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f'{h:d}h, {m:02d}m, {s:02d}s'

def ticks2hms(ticks: int) -> str:
    import datetime

    epoch = datetime.datetime(1, 1, 1)
    converted_ticks = epoch + datetime.timedelta(microseconds = ticks/10)
    return converted_ticks.strftime("%Y-%m-%d %H:%M:%S UTC")

class CSSBytes:
    def __init__(self, data: bytes):
        self.bytes = data
        self.mark = 0

    @classmethod
    def from_file(cls, fname: str) -> 'CSSBytes':
        with open(fname, 'rb') as fin:
            data = fin.read()
        return cls(data)

    def __getitem__(self, idx):
        return self.bytes[idx]

    def peek(self, bytecount: int = 512):
        return self[self.mark:self.mark + bytecount]

    def read(self, bytecount: int = -1):
        if bytecount == -1:
            data = self[self.mark:]
            self.mark = bytecount(self.bytes)
            return data

        end = self.mark + bytecount
        data = self[self.mark:end]
        self.mark = end
        return data

    def read_int(self, bytecount: int):
        return int.from_bytes(self.read(bytecount), 'little', signed=False)

    def get_presized_block(self, presize_len: int = 4) -> 'CSSBytes':
        size_len = self.read_int(presize_len)
        return CSSBytes(self.read(size_len))

    def get_array(self, item_size: int, precount_len: int = 4) -> 'CSSBytes':
        count = self.read_int(precount_len)
        return CSSBytes(self.read(item_size * count))

    def read_varlen_str(self):
        s = ''
        i = self.read_int(1)
        while i != 0:
            s += chr(i)
            i = self.read_int(1)
        return s

    def read_str(self, bytecount: int = -1):
        s = ''

        if bytecount == -1:
            bytecount = self.read_int(4)

        for _ in range(bytecount - 1):
            s += chr(self.read_int(1))
        self.read(1)

        return s


class SaveFile(UsesStringBuilder):
    def __init__(self, data: CSSBytes):
        self.header = HeaderData(data)

    @classmethod
    def from_file(cls, fname: str) -> 'SaveFile':
        return cls(CSSBytes.from_file(fname))

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        sb.appendln('Header')
        sb.indent()
        self.header.to_sb(sb)
        sb.unindent()

        return sb


class HeaderData(UsesStringBuilder):
    def __init__(self, data: CSSBytes):
        self.header_version = data.read_int(4)
        self.save_version = data.read_int(4)
        self.build_version = data.read_int(4)
        self.world_type = data.read_str()
        self.world_properties = data.read_str().split('?')[1:]
        self.session_name = data.read_str()
        self.play_time_sec = data.read_int(4)
        self.play_time_str = s2hms(self.play_time_sec)
        self.save_date_ticks = data.read_int(8)
        self.save_date_str = ticks2hms(self.save_date_ticks)
        self.save_visibility = data.read_int(1)

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        sb.appendln('Header version: %d' % self.header_version)
        sb.appendln('Save version: %d' % self.save_version)
        sb.appendln('Build version: %d' % self.build_version)
        sb.appendln('World type: %s' % self.world_type)
        sb.appendln('World properties: %s' % self.world_properties)
        sb.appendln('Session name: %s' % self.session_name)
        sb.appendln('Play Time: %d (%s)' % (self.play_time_sec, self.play_time_str))
        sb.appendln('Save date: %d (%s)' % (self.save_date_ticks, self.save_date_str))
        sb.appendln('Save visibility: %d' % self.save_visibility)

        return sb


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        fname = input('Input file> ')
    else:
        fname = sys.argv[1]

    file = SaveFile.from_file(fname)
    print(file)
