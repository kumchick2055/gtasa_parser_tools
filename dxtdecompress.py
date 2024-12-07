"""
S3TC DXT1/DXT5 Texture Decompression

Inspired by Benjamin Dobell

Original C++ code https://github.com/Benjamin-Dobell/s3tc-dxt-decompression
"""

import struct
from enum import Enum
from PIL import Image
from struct import unpack_from
import json

def make_fourcc(ch1, ch2, ch3, ch4):
    return (ord(ch1) & 0xFF) | ((ord(ch2) & 0xFF) << 8) | ((ord(ch3) & 0xFF) << 16) | ((ord(ch4) & 0xFF) << 24)

def unpack(_bytes):
    STRUCT_SIGNS = {
    1 : 'B',
    2 : 'H',
    4 : 'I',
    8 : 'Q'
    }
    return struct.unpack('<' + STRUCT_SIGNS[len(_bytes)], _bytes)[0]

# This function converts RGB565 format to raw pixels
def unpackRGB(packed):
    R = ((packed >> 11) & 0x1f) * 0xff // 0x1f
    G = ((packed >> 5) & 0x3f) * 0xff // 0x3f
    B = (packed & 0x1f) * 0xff // 0x1f

    return (R, G, B, 255)

class ImageDecoder:

    @staticmethod
    def _decode1555(bits):
        a = ((bits >> 15) & 0x1) * 0xff
        b = ((bits >> 10) & 0x1f) * 0xff // 0x1f
        c = ((bits >> 5) & 0x1f) * 0xff // 0x1f
        d = (bits & 0x1f) * 0xff // 0x1f
        return a, b, c, d

    @staticmethod
    def _decode4443(bits):
        a = ((bits >> 12) & 0x7) * 0xff // 0x7
        b = ((bits >> 8) & 0xf) * 0xff // 0xf
        c = ((bits >> 4) & 0xf) * 0xff // 0xf
        d = (bits & 0xf) * 0xff // 0xf
        return a, b, c, d

    @staticmethod
    def _decode4444(bits):
        a = ((bits >> 12) & 0xf) * 0xff // 0xf
        b = ((bits >> 8) & 0xf) * 0xff // 0xf
        c = ((bits >> 4) & 0xf) * 0xff // 0xf
        d = (bits & 0xf) * 0xff // 0xf
        return a, b, c, d

    @staticmethod
    def _decode565(bits):
        a = ((bits >> 11) & 0x1f) * 0xff // 0x1f
        b = ((bits >> 5) & 0x3f) * 0xff // 0x3f
        c = (bits & 0x1f) * 0xff // 0x1f
        return a, b, c

    @staticmethod
    def _decode555(bits):
        a = ((bits >> 10) & 0x1f) * 0xff // 0x1f
        b = ((bits >> 5) & 0x1f) * 0xff // 0x1f
        c = (bits & 0x1f) * 0xff // 0x1f
        return a, b, c

    @staticmethod
    def _c2a(a, b):
        return (2 * a + b) // 3

    @staticmethod
    def _c2b(a, b):
        return (a + b) // 2

    @staticmethod
    def _c3(a, b):
        return (2 * b + a) // 3

    @staticmethod
    def bc1(data, width, height, alpha_flag):
        pos = 0
        ret = bytearray(4 * width * height)

        for y in range(0, height, 4):
            for x in range(0, width, 4):
                color0, color1, bits = unpack_from("<HHI", data, pos)
                pos += 8

                r0, g0, b0 = ImageDecoder._decode565(color0)
                r1, g1, b1 = ImageDecoder._decode565(color1)

                # Decode this block into 4x4 pixels
                for j in range(4):
                    for i in range(4):
                        # Get next control op and generate a pixel
                        control = bits & 3
                        bits = bits >> 2
                        if control == 0:
                            r, g, b, a = r0, g0, b0, 0xff
                        elif control == 1:
                            r, g, b, a = r1, g1, b1, 0xff
                        elif control == 2:
                            if color0 > color1:
                                r, g, b, a = ImageDecoder._c2a(r0, r1), ImageDecoder._c2a(g0, g1), ImageDecoder._c2a(b0, b1), 0xff
                            else:
                                r, g, b, a = ImageDecoder._c2b(r0, r1), ImageDecoder._c2b(g0, g1), ImageDecoder._c2b(b0, b1), 0xff
                        elif control == 3:
                            if color0 > color1:
                                r, g, b, a = ImageDecoder._c3(r0, r1),ImageDecoder. _c3(g0, g1), ImageDecoder._c3(b0, b1), 0xff
                            else:
                                r, g, b, a = 0, 0, 0, 0

                        idx = 4 * ((y + j) * width + (x + i))
                        ret[idx:idx+4] = bytes([r, g, b, a | alpha_flag])

        return bytes(ret)

    @staticmethod
    def bc2(data, width, height, premultiplied):
        pos = 0
        ret = bytearray(4 * width * height)

        for y in range(0, height, 4):
            for x in range(0, width, 4):
                alpha0, alpha1, alpha2, alpha3, color0, color1, bits = unpack_from("<4H2HI", data, pos)
                pos += 16

                r0, g0, b0 = ImageDecoder._decode565(color0)
                r1, g1, b1 = ImageDecoder._decode565(color1)
                alphas = (alpha0, alpha1, alpha2, alpha3)

                # Decode this block into 4x4 pixels
                for j in range(4):
                    for i in range(4):
                        # Get next control op and generate a pixel
                        control = bits & 3
                        bits = bits >> 2
                        if control == 0:
                            r, g, b = r0, g0, b0
                        elif control == 1:
                            r, g, b = r1, g1, b1
                        elif control == 2:
                            if color0 > color1:
                                r, g, b = ImageDecoder._c2a(r0, r1), ImageDecoder._c2a(g0, g1), ImageDecoder._c2a(b0, b1)
                            else:
                                r, g, b = ImageDecoder._c2b(r0, r1), ImageDecoder._c2b(g0, g1), ImageDecoder._c2b(b0, b1)
                        elif control == 3:
                            if color0 > color1:
                                r, g, b = ImageDecoder._c3(r0, r1),ImageDecoder. _c3(g0, g1), ImageDecoder._c3(b0, b1)
                            else:
                                r, g, b = 0, 0, 0

                        a = ((alphas[j] >> (i * 4)) & 0xf) * 0x11
                        idx = 4 * ((y + j) * width + (x + i))
                        if premultiplied and a > 0:
                            r = min(round(r * 255 / a), 255)
                            g = min(round(g * 255 / a), 255)
                            b = min(round(b * 255 / a), 255)
                        ret[idx:idx+4] = bytes([r, g, b, a])

        return bytes(ret)

    @staticmethod
    def bc3(data, width, height, premultiplied):
        pos = 0
        ret = bytearray(4 * width * height)

        for y in range(0, height, 4):
            for x in range(0, width, 4):
                alpha0, alpha1, alpha2, alpha3, alpha4, color0, color1, bits = unpack_from("<2B3H2HI", data, pos)
                pos += 16

                r0, g0, b0 = ImageDecoder._decode565(color0)
                r1, g1, b1 = ImageDecoder._decode565(color1)

                if alpha0 > alpha1:
                    alphas = (
                        alpha0,
                        alpha1,
                        round(alpha0 * (6 / 7) + alpha1 * (1 / 7)),
                        round(alpha0 * (5 / 7) + alpha1 * (2 / 7)),
                        round(alpha0 * (4 / 7) + alpha1 * (3 / 7)),
                        round(alpha0 * (3 / 7) + alpha1 * (4 / 7)),
                        round(alpha0 * (2 / 7) + alpha1 * (5 / 7)),
                        round(alpha0 * (1 / 7) + alpha1 * (6 / 7))
                    )
                else:
                    alphas = (
                        alpha0,
                        alpha1,
                        round(alpha0 * (4 / 5) + alpha1 * (1 / 5)),
                        round(alpha0 * (3 / 5) + alpha1 * (2 / 5)),
                        round(alpha0 * (2 / 5) + alpha1 * (3 / 5)),
                        round(alpha0 * (1 / 5) + alpha1 * (4 / 5)),
                        0,
                        255
                    )

                alpha_indices = (alpha4, alpha3, alpha2)

                # Decode this block into 4x4 pixels
                for j in range(4):
                    for i in range(4):
                        # Get next control op and generate a pixel
                        control = bits & 3
                        bits = bits >> 2
                        if control == 0:
                            r, g, b = r0, g0, b0
                        elif control == 1:
                            r, g, b = r1, g1, b1
                        elif control == 2:
                            if color0 > color1:
                                r, g, b = ImageDecoder._c2a(r0, r1), ImageDecoder._c2a(g0, g1), ImageDecoder._c2a(b0, b1)
                            else:
                                r, g, b = ImageDecoder._c2b(r0, r1), ImageDecoder._c2b(g0, g1), ImageDecoder._c2b(b0, b1)
                        elif control == 3:
                            if color0 > color1:
                                r, g, b = ImageDecoder._c3(r0, r1),ImageDecoder. _c3(g0, g1), ImageDecoder._c3(b0, b1)
                            else:
                                r, g, b = 0, 0, 0

                        # Get alpha index
                        shift = 3 * (15 - ((3 - i) + (j * 4)))
                        shift_s = shift % 16
                        row_s = shift // 16
                        row_e = (shift + 2) // 16
                        alpha_index = (alpha_indices[2 - row_s] >> shift_s) & 7
                        if row_s != row_e:
                            shift_e = 16 - shift_s
                            alpha_index += (alpha_indices[2 - row_e] & ((2 ** (3 - shift_e)) - 1)) << shift_e
                        a = alphas[alpha_index]

                        idx = 4 * ((y + j) * width + (x + i))
                        if premultiplied and a > 0:
                            r = min(round(r * 255 / a), 255)
                            g = min(round(g * 255 / a), 255)
                            b = min(round(b * 255 / a), 255)
                        ret[idx:idx+4] = bytes([r, g, b, a])

        return bytes(ret)

    @staticmethod
    def bgra1555(data, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in range(0, len(data), 2):
            color = unpack_from("<H", data, i)[0]
            a, r, g, b = ImageDecoder._decode1555(color)
            ret[pos:pos+4] = r, g, b, a
            pos += 4
        return bytes(ret)

    @staticmethod
    def bgra4444(data, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in range(0, len(data), 2):
            color = unpack_from("<H", data, i)[0]
            a, r, g, b = ImageDecoder._decode4444(color)
            ret[pos:pos+4] = r, g, b, a
            pos += 4
        return bytes(ret)

    @staticmethod
    def bgra555(data, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in range(0, len(data), 2):
            color = unpack_from("<H", data, i)[0]
            r, g, b = ImageDecoder._decode555(color)
            ret[pos:pos+4] = r, g, b, 0xff
            pos += 4
        return bytes(ret)

    @staticmethod
    def bgra565(data, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in range(0, len(data), 2):
            color = unpack_from("<H", data, i)[0]
            r, g, b = ImageDecoder._decode565(color)
            ret[pos:pos+4] = r, g, b, 0xff
            pos += 4
        return bytes(ret)

    @staticmethod
    def bgra888(data, width, height):
        ret = bytearray(4 * width * height)
        for i in range(0, len(data), 4):
            ret[i:i+4] = data[i+2], data[i+1], data[i+0], 0xff
        return bytes(ret)

    @staticmethod
    def bgra8888(data, width, height):
        ret = bytearray(4 * width * height)
        for i in range(0, len(data), 4):
            ret[i:i+4] = data[i+2], data[i+1], data[i+0], data[i+3]
        return bytes(ret)

    @staticmethod
    def lum8(data, width, height):
        ret = bytearray(4 * width * height)
        for i, c in enumerate(data):
            pos = i * 4
            ret[pos:pos+4] = c, c, c, 0xff
        return bytes(ret)

    @staticmethod
    def lum8a8(data, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in range(0, len(data), 2):
            c, a = data[i], data[i+1]
            ret[pos:pos+4] = c, c, c, a
            pos += 4
        return bytes(ret)

    @staticmethod
    def pal4(data, palette, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in data:
            idx1, idx2 = (i >> 4) & 0xf, i & 0xf
            ret[pos+0:pos+4] = palette[idx1*4:idx1*4+4]
            ret[pos+4:pos+8] = palette[idx2*4:idx2*4+4]
            pos += 8

        return bytes(ret)

    @staticmethod
    def pal4_noalpha(data, palette, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for i in data:
            idx1, idx2 = (i >> 4) & 0xf, i & 0xf
            ret[pos+0:pos+4] = palette[idx1*4:idx1*4+3] + b'\xff'
            ret[pos+4:pos+8] = palette[idx2*4:idx2*4+3] + b'\xff'
            pos += 8

        return bytes(ret)

    @staticmethod
    def pal8(data, palette, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for idx in data:
            ret[pos:pos+4] = palette[idx*4:idx*4+4]
            pos += 4

        return bytes(ret)

    @staticmethod
    def pal8_noalpha(data, palette, width, height):
        pos = 0
        ret = bytearray(4 * width * height)

        for idx in data:
            ret[pos:pos+4] = palette[idx*4:idx*4+3] + b'\xff'
            pos += 4

        return bytes(ret)

class D3DFORMAT(Enum):
    D3D_8888 = 21
    D3D_888  = 22
    D3D_565  = 23
    D3D_555  = 24
    D3D_1555 = 25
    D3D_4444 = 26

    D3DFMT_L8   = 50
    D3DFMT_A8L8 = 51

    D3DFMT_UYVY                 = make_fourcc('U', 'Y', 'V', 'Y')
    D3DFMT_R8G8_B8G8            = make_fourcc('R', 'G', 'B', 'G')
    D3DFMT_YUY2                 = make_fourcc('Y', 'U', 'Y', '2')
    D3DFMT_G8R8_G8B8            = make_fourcc('G', 'R', 'G', 'B')
    D3DFMT_DXT1                 = make_fourcc('D', 'X', 'T', '1')
    D3DFMT_DXT2                 = make_fourcc('D', 'X', 'T', '2')
    D3DFMT_DXT3                 = make_fourcc('D', 'X', 'T', '3')
    D3DFMT_DXT4                 = make_fourcc('D', 'X', 'T', '4')
    D3DFMT_DXT5                 = make_fourcc('D', 'X', 'T', '5')



def main():
    txd_files = json.loads(open('./json_data.json', 'r', encoding='utf-8').read())
    for j in txd_files.keys():
        for file_data in txd_files[j]['textures']:
            # print(file_data)
            
            s3tc_format = D3DFORMAT(file_data['d3d_format'])
            # print(s3tc_format)

            with open(f'./txd_files_data/{file_data["name"]}.data', 'rb') as f:
                width = file_data['width']
                height = file_data['height']
                try:
                    if s3tc_format is D3DFORMAT.D3DFMT_DXT1:
                        bytes_data = ImageDecoder.bc1(f.read(), width, height, 0x00)
                    if s3tc_format is D3DFORMAT.D3DFMT_DXT3:
                        bytes_data = ImageDecoder.bc2(f.read(), width, height, False)
                except Exception as ex:
                    print(ex, j)
                    continue
                
                # bytes_data = buff.DXT1Decompress(f)

                img = Image.new('RGB', (width, height))
                pixels = img.load()
                set_pixel_x = 0
                set_pixel_y = 0

                try:
                    for y in range(0, height):
                        for x in range(0, width):
                            try:
                                data = struct.unpack('<4B', bytes_data[set_pixel_y * width + set_pixel_x:set_pixel_y * width + set_pixel_x + 4])
                            except:
                                data = (255, 0, 255, 255)
                            pixels[x,y] = data
                            set_pixel_x += 4

                        set_pixel_y += 4
                        set_pixel_x = 0

                    img.save(f'./decoded_files/{file_data["name"]}.png')
                    print("Image saved as output_image.png")
                except Exception as ex:
                    print(ex)
                    print(len(bytes_data), x, y)
                    continue

                
        
    
if __name__ == '__main__':
    main()