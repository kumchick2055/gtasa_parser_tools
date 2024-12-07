import struct
import glob
from traceback import format_exc
from pathlib import Path
import json
from enum import Enum



def unpack_version(libid):
    if(libid & 0xFFFF0000):
        return (libid>>14 & 0x3FF00) + 0x30000 | (libid>>16 & 0x3F)
    
    return libid<<8

def make_fourcc(ch1, ch2, ch3, ch4):
    return (ord(ch1) & 0xFF) | ((ord(ch2) & 0xFF) << 8) | ((ord(ch3) & 0xFF) << 16) | ((ord(ch4) & 0xFF) << 24)


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


class FilterMode(Enum):
    FILTER_NONE                = 0x00
    FILTER_NEAREST             = 0x01
    FILTER_LINEAR              = 0x02
    FILTER_MIP_NEAREST         = 0x03
    FILTER_MIP_LINEAR          = 0x04
    FILTER_LINEAR_MIP_NEAREST  = 0x05
    FILTER_LINEAR_MIP_LINEAR   = 0x06


class AddressingMode(Enum):
    WRAP_NONE     = 0x00
    WRAP_WRAP     = 0x01
    WRAP_MIRROR   = 0x02
    WRAP_CLAMP    = 0x03


class RasterFormat(Enum):
    FORMAT_DEFAULT         = 0x0000 #
    FORMAT_1555            = 0x0100 # (1 bit alpha, RGB 5 bits each; also used for DXT1 with alpha)
    FORMAT_565             = 0x0200 # (5 bits red, 6 bits green, 5 bits blue; also used for DXT1 without alpha)
    FORMAT_4444            = 0x0300 # (RGBA 4 bits each; also used for DXT3)
    FORMAT_LUM8            = 0x0400 # (gray scale, D3DFMT_L8)
    FORMAT_8888            = 0x0500 # (RGBA 8 bits each)
    FORMAT_888             = 0x0600 # (RGB 8 bits each, D3DFMT_X8R8G8B8)
    FORMAT_555             = 0x0A00 # (RGB 5 bits each - rare, use 565 instead, D3DFMT_X1R5G5B5)

    FORMAT_EXT_AUTO_MIPMAP = 0x1000 # (RW generates mipmaps, see special section below)
    FORMAT_EXT_PAL8        = 0x2000 # (2^8 = 256 palette colors)
    FORMAT_EXT_PAL4        = 0x4000 # (2^4 = 16 palette colors)
    FORMAT_EXT_MIPMAP      = 0x8000 # (mipmaps included)



class TxdReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def get_section(self):
        data = self.file_stream.read(12)
        try:
            type_section, size, library_id = struct.unpack('<III', data)
        except:

            if self.file_stream.read(1) == b'':
                return None

        return {
            'type': hex(type_section),
            'size': size,
            'library_id': hex(
                unpack_version(library_id)
            )
        }

    def get_header(self):
        data = self.file_stream.read(12)
        try:
            type_section, size, library_id = struct.unpack('<III', data)
        except:
            return None

        return {
            'type': hex(type_section),
            'size': size,
            'library_id': hex(
                unpack_version(library_id)
            )
        }
    
    def get_texture_dictionary_data(self):
        textureCount, deviceId = struct.unpack('HH', self.file_stream.read(4))

        return {
            'texture_count': textureCount,
            'device_id': deviceId
        }
    
    def get_raster_data(self):
        # - Texture Format ----------------------------------------------
        platform_id, filter_mode  = struct.unpack('<hh', self.file_stream.read(4))
        UAddressing,VAddressing = struct.unpack('2B', self.file_stream.read(2)) 

        pad_texture_format = struct.unpack('h', self.file_stream.read(2))
        # name
        try:
            name = struct.unpack('32s', self.file_stream.read(32))[0].decode('utf-8')
        except:
            name = Path(self.file_path).stem
        
        # mask name
        mask_name = struct.unpack('32s', self.file_stream.read(32))[0]
        # ---------------------------------------------------------------


        # - Raster Format -----------------------------------------------
        raster_format = hex( 
            struct.unpack('I', self.file_stream.read(4))[0]
        )

        # формат d3d 
        bebra = struct.unpack('I', self.file_stream.read(4))[0]
        try:
            d3dformat = D3DFORMAT(bebra)
        except:
            d3dformat = D3DFORMAT.D3DFMT_UNKNOWN

        # Ширина и высота
        width, height = struct.unpack('2h', self.file_stream.read(4))
        
        # print(struct.unpack('8s', self.file_stream.read(8)))
        #depth
        depth, num_levels, raster_type, \
        alpha, cube_texture, auto_mip_maps, \
        compressed, pad_raster_format = struct.unpack('8B', self.file_stream.read(8))
        # ---------------------------------------------------------------

        return {
            'platform_id': platform_id, 
            'filter_mode': filter_mode,
            'u_addressing': UAddressing,
            'v_addressing': VAddressing,
            'pad_texture_format': pad_texture_format[0],
            'name': name.replace('\x00', ''),
            'mask_name': mask_name.decode('utf-8', errors='replace').replace('\x00', ''),
            'raster_format': raster_format,
            'd3d_format': d3dformat.value,
            'width': width,
            'height': height,
            'depth': depth,
            'num_levels': num_levels,
            'raster_type': raster_type,
            'alpha': alpha,
            'cube_texture': cube_texture,
            'auto_mip_maps': auto_mip_maps,
            'compressed': compressed,
            'pad_raster_format': pad_raster_format
        }
    
    def get_file_data(self, size):
        return self.file_stream.read(size)


    def __enter__(self):
        self.file_stream = open(self.file_path, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file_stream.close()



json_data = {}

for i in glob.glob('./txd_files/*.txd'):
    try:
        json_data[i] = {'info': {}, 'textures': []}

        with TxdReader(i) as f:
            # Texture Dictionary
            header_data = f.get_header()
            if header_data is None:
                print(f'File {i} is have the broken header')
                continue

            f.get_section()

            texture_dictionary = f.get_texture_dictionary_data()
            json_data[i]['info'] = texture_dictionary
            # Raster
            f.get_section()
            
            section_raster_data = f.get_section()

            for _ in range(texture_dictionary['texture_count']):
                raster_data = f.get_raster_data()
                json_data[i]['textures'].append(raster_data)
                # print(raster_data)

                # print(raster_data['name'], raster_data['d3d_format'], raster_data['raster_format'])

                
                with open(f'./txd_files_data/{raster_data["name"]}.data', 'wb') as d:
                    d.write(f.get_file_data(section_raster_data['size'] - 68))

                section_raster_data = f.get_section()
                print(section_raster_data)

                if section_raster_data is None:
                    continue

        # print('-----------------')
    except Exception as ex:
        print(ex, f'File: {i} {format_exc()}')
    
with open('json_data.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(json_data))