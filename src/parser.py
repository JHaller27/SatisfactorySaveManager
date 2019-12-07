from strbuilder import StringBuilder, UsesStringBuilder
import io


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


class CSSSavFile(io.BufferedReader):
    def read_int(self, bytecount: int = 4) -> int:
        return int.from_bytes(self.read(bytecount), 'little', signed=False)

    def get_presized_block(self, presize_len: int = 4) -> 'CSSSavFile':
        size_len = self.read_int(presize_len)
        return CSSSavFile(self.read(size_len))

    def get_array(self, item_size: int, precount_len: int = 4) -> 'CSSSavFile':
        count = self.read_int(precount_len)
        return CSSSavFile(self.read(item_size * count))

    def read_varlen_str(self) -> str:
        s = ''
        i = self.read_int(1)
        while i != 0:
            s += chr(i)
            i = self.read_int(1)
        return s

    def read_str(self, bytecount: int = -1) -> str:
        s = ''

        if bytecount == -1:
            bytecount = self.read_int()

        for _ in range(bytecount - 1):
            s += chr(self.read_int(1))
        self.read(1)

        return s


class ZlibChunk(CSSSavFile, UsesStringBuilder):
    def __init__(self, compressed_data: CSSSavFile):
        decompressed_data_stream = self.decompress(compressed_data)

        super().__init__(decompressed_data_stream)

    def decompress(self, data: CSSSavFile) -> io.BytesIO:
        import zlib

        self.PACKAGE_FILE_TAG = data.read_int(4)
        self.maximum_chunk_size = data.read_int(8)
        self.current_chunk_compressed_len = data.read_int(8)
        self.current_chunk_uncompressed_len = data.read_int(8)
        data.read_int(8)  # Dupe of current_chunk_compressed_len
        data.read_int(8)  # Dupe of current_chunk_decompressed_len

        compressed_data = data.read(self.current_chunk_compressed_len)
        byte_data = zlib.decompress(compressed_data, bufsize=self.current_chunk_uncompressed_len)
        if len(byte_data) != self.current_chunk_uncompressed_len:
            raise RuntimeWarning('ZlibChunk bytes length != decompressed length from metadata')
        return io.BytesIO(byte_data)

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        sb.appendln('PACKAGE_FILE_TAG: %d' % self.PACKAGE_FILE_TAG)
        sb.appendln('Max chunk size: %d' % self.maximum_chunk_size)
        sb.appendln('Chunk size (compressed -> uncompressed): %d -> %d' % (self.current_chunk_compressed_len, self.current_chunk_uncompressed_len))

        return sb


class ZlibData(CSSSavFile):
    def __init__(self, data: CSSSavFile):
        self.compressed_bytes = data
        super().__init__(ZlibChunk(self.compressed_bytes))

    def _set_next_chunk(self) -> None:
        self.bytes = ZlibChunk(self.compressed_bytes)
        self.mark = 0

    def read(self, bytecount: int = -1) -> bytes:
        b = bytearray()

        if bytecount == -1:
            while self.compressed_bytes.mark < len(self.compressed_bytes):
                b.extend(self.bytes.bytes)
                self._set_next_chunk()

            return bytes(b)

        while len(b) < bytecount:
            b.extend(self.bytes.bytes)
            self._set_next_chunk()

        return bytes(b)


class SaveFile(UsesStringBuilder):
    def __init__(self, data: CSSSavFile):
        self.header = HeaderData(data)
        self.body = BodyData(data)

    @classmethod
    def from_file(cls, fname: str) -> 'SaveFile':
        return cls(CSSSavFile.from_file(fname))

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        sb.appendln('Header')
        sb.indent()
        self.header.to_sb(sb)
        sb.unindent()

        sb.appendln('Body')
        sb.indent()
        self.body.to_sb(sb)
        sb.unindent()

        return sb


class HeaderData(UsesStringBuilder):
    def __init__(self, data: CSSSavFile):
        self.header_version = data.read_int()
        self.save_version = data.read_int()
        self.build_version = data.read_int()
        self.world_type = data.read_str()
        self.world_properties = data.read_str().split('?')[1:]
        self.session_name = data.read_str()
        self.play_time_sec = data.read_int()
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


class BodyData(UsesStringBuilder):
    def __init__(self, data: CSSSavFile):
        self.world_object_list = WorldObjectDataArray(data)

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        self.world_object_list.to_sb(sb)

        return sb


class WorldObjectDataArray(UsesStringBuilder):
    def __init__(self, data: CSSSavFile):
        self.count = data.read_int()
        self.zlib_data = ZlibData(data)

        self.world_objects = []
        zlib_data = ZlibData(data)

        for _ in range(1):
            item = WorldObject(zlib_data)

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        sb.appendln('Count: %d' % self.count)

        for idx, item in enumerate(self.world_objects):
            sb.appendln('World object[%d]' % idx)
            sb.indent()
            item.to_sb(sb)
            sb.unindent()

        return sb


class WorldObject(UsesStringBuilder):
    def __init__(self, data: CSSSavFile):
        self.name = data.read_str()
        self.property_type = data.read_str()
        self.value_len = data.read_int()
        self.index = data.read_int()

    def to_sb(self, sb: StringBuilder = StringBuilder()) -> StringBuilder:
        sb.appendln('Name: %s' % self.name)
        sb.appendln('Property type: %s' % self.property_type)
        sb.appendln('Value length: %d' % self.value_len)
        sb.appendln('Index: %d' % self.index)

        return sb


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        fname = input('Input file> ')
    else:
        fname = sys.argv[1]

    with open(fname, 'rb') as raw_fin:
        fin = CSSSavFile(raw_fin)
        file = SaveFile(fin)
        print(file)
