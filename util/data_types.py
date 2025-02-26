NULL_CHAR = 0x00.to_bytes()

class uint:
    NUM_BYTES = 0
    def __init__(self, value: int=0):
        self.MAX_VALUE = 2**(self.NUM_BYTES * 8)

        if value > self.MAX_VALUE: raise OverflowError(f"Value {value} too large for {self.NUM_BYTES*8}-bit uint")
        if value < 0: raise TypeError(f"{value} is not an unsigned integer")

        self.value = value

    def __int__(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def encode(self):
        """Turn stored value into bytes"""
        return self.value.to_bytes(self.NUM_BYTES)

    @classmethod
    def decode(cls, value: bytes):
        """Turn bytes into this class"""
        if len(value) < cls.NUM_BYTES:
            raise ValueError("Wrong number of bytes")

        return (cls(int.from_bytes(value[:cls.NUM_BYTES])), cls.NUM_BYTES)

class uint8(uint):
    NUM_BYTES = 1

class uint16(uint):
    NUM_BYTES = 2

class uint24(uint):
    NUM_BYTES = 3

class uint32(uint):
    NUM_BYTES = 4

class lds:
    def __init__(self, value: str=""):
        if len(value) > 255:
            raise OverflowError("String too long for LDS, use NTS instead")

        self.value = value

    def __int__(self):
        return int(self.value)

    def __str__(self):
        return self.value

    def encode(self):
        """Turn stored value into bytes"""
        enc = len(self.value).to_bytes()
        enc += self.value.encode('unicode_escape')

        return enc

    @classmethod
    def decode(cls, value: bytes):
        """Turn bytes into this class"""
        length = value[0]

        if len(value)-1 < length:
            raise ValueError("Wrong number of bytes")

        return (cls(value[1:length+1].decode("unicode_escape")), length+1)

class nts:
    def __init__(self, value: str=""):
        self.value = value

    def __int__(self):
        return int(self.value)

    def __str__(self):
        return self.value

    def encode(self):
        """Turn stored value into bytes"""
        enc = self.value.encode('unicode_escape')
        enc += NULL_CHAR

        return enc

    @classmethod
    def decode(cls, value: bytes):
        """Turn bytes into this class"""
        if not NULL_CHAR in value:
            raise ValueError("No termination in NTS")

        return (cls(value.split(NULL_CHAR, 1)[0].decode("unicode_escape")), value.index(NULL_CHAR))
