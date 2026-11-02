
import zlib
def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF 
#bnta2ked en el packet 32 bit unsigned