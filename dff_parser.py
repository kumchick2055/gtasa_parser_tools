import struct
from dataclasses import dataclass, field
from enum import Enum


def unpack_version(libid):
    if(libid & 0xFFFF0000):
        return (libid>>14 & 0x3FF00) + 0x30000 | (libid>>16 & 0x3F)
    
    return libid<<8


rpGEOMETRYTRISTRIP = 0x00000001
rpGEOMETRYPOSITIONS = 0x00000002
rpGEOMETRYTEXTURED = 0x00000004
rpGEOMETRYPRELIT = 0x00000008
rpGEOMETRYNORMALS = 0x00000010
rpGEOMETRYLIGHT = 0x00000020
rpGEOMETRYMODULATEMATERIALCOLOR = 0x00000040
rpGEOMETRYTEXTURED2 = 0x00000080
rpGEOMETRYNATIVE = 0x01000000


class SectionType(Enum):
    CLUMP = 0x10
    STRUCT = 0x1
    FRAME_LIST = 0xe
    EXTENSION = 0x3
    FRAME = 0x253f2fe # Node Name
    GEOMETRY_LIST = 0x1a
    GEOMETRY = 0xf
    MATERIAL_LIST = 0x8
    MATERIAL = 0x7
    TEXTURE = 0x6
    STRING = 0x2
    BIN_MESH_PLG = 0x50e
    BREAKABLE = 0x253f2fd
    EXTRA_VERT_COLOUR = 0x253f2f9
    ATOMIC = 0x14
    TWOD_EFFECT = 0x253f2f8


@dataclass
class RWSection:
    section_type: SectionType
    size: int
    size_2: int
    version: int


@dataclass
class ClumpSection:
    atomics: int
    lights:int 
    cameras: int

# TODO: переделать frame_data
@dataclass
class FrameListSection:
    frame_count: int
    frame_data: bytes


@dataclass
class FrameSection:
    node_name: str

@dataclass
class GeometryListSection:
    number_geometry_list: int


###############################
@dataclass
class RwRGBA:
    r: int
    g: int
    b: int
    a: int


@dataclass
class RwTexCoords:
    u: float
    v: float


@dataclass
class RpTriangle:
    vertex2: int
    vertex1: int
    material_id: int
    vertex_3: int


@dataclass
class RwSphere:
    x: float
    y: float
    z: float
    radius: float

@dataclass
class RwV3d:
    x: float
    y: float
    z: float
###############################

@dataclass
class GeometrySection:
    format: int
    flags_set: list
    num_of_triangles: int
    num_of_vertices: int
    number_of_morph_targets: int = 1

    has_vertices: bool = False
    has_normals: bool = False

    bounding_sphere: RwSphere | None = None

    prelitcolor: list[RwRGBA] | None = None

    tex_coords: list[RwTexCoords] = field(default_factory=list)
    triangles: list[RpTriangle] = field(default_factory=list)

    vertices: list[RwV3d] = field(default_factory=list)
    normals: list[RwV3d] = field(default_factory=list)


@dataclass
class MaterialListSection:
    number_of_materials: int
    data: list


@dataclass
class MaterialSection:
    ambient: float
    specular: float
    diffuse: float

    flags: int | None = None
    color: RwRGBA | None = None
    is_textured: bool = False


@dataclass
class TextureSection:
    texture_filtering: int
    u_addressing: int
    v_addressing: int
    use_mipmap: int
    padding: str


@dataclass
class StringSection:
    name: str


@dataclass
class BreakableSection:
    magic_number: int


@dataclass
class BinMeshPLGSection:
    flags: int
    number_of_meshes: int
    total_number_of_indices: int
    list_meshes: list = field(default_factory=list)

@dataclass
class AtomicStruct:
    frame_index: int
    geometry_index: int
    flags: int


@dataclass
class ExtraVertColourSection:
    magic_number: int
    night_vert_color: list[RwRGBA] = field(default_factory=list)


class DffParser:
    def __init__(self, file_name):
        self.file = file_name


    def get_struct(self) -> RWSection | None:
        data = self.file_stream.read(12)
        if len(data) == 0:
            return None
        
        struct_id, size_2, version = struct.unpack('<3I', data)
        if struct_id == 0:
            return None
        if SectionType(struct_id) is SectionType.STRING or SectionType(struct_id) is SectionType.BREAKABLE or SectionType(struct_id) is SectionType.EXTRA_VERT_COLOUR:
            return RWSection(
                section_type=SectionType(struct_id),
                size=size_2,
                size_2=size_2,
                version=unpack_version(version)
            )
        data = self.file_stream.read(12)

        if len(data) == 0:
            return None
        
        struct_id_2, size, version = struct.unpack('<3I', data)
        if struct_id_2 == 0:
            return None
        
        if SectionType(struct_id) is SectionType.EXTENSION:
            struct_id = SectionType(struct_id_2)

        return RWSection(
            section_type=SectionType(struct_id),
            size=size,
            size_2=size_2,
            version=unpack_version(version)
        )

    def get_body(self, section_type: SectionType, data: int | None = None) -> ClumpSection:
        if section_type is SectionType.CLUMP:
            atomics, lights, cameras = struct.unpack('<III', self.file_stream.read(12))
            return ClumpSection(
                atomics=atomics,
                lights=lights,
                cameras=cameras
            )
        if section_type is SectionType.FRAME_LIST:
            frame_count = struct.unpack('<I', self.file_stream.read(4))[0]
            # print(frame_count, frame_count * 0x44, 'frame_count')
            frame_data = self.file_stream.read(frame_count * 0x38)
            return FrameListSection(
                frame_count=frame_count,
                frame_data=frame_data
            )
        if section_type is SectionType.FRAME:
            name = struct.unpack(f'{data}s', self.file_stream.read(data))[0]

            return FrameSection(
                node_name=name.decode('utf-8')
            )
        if section_type is SectionType.GEOMETRY_LIST:
            n = struct.unpack('<I', self.file_stream.read(4))[0]
            return GeometryListSection(
                number_geometry_list=n
            )
        if section_type is SectionType.GEOMETRY:
            flag_value = struct.unpack('<I', self.file_stream.read(4))[0]
            flags_set = []

            if flag_value & rpGEOMETRYPOSITIONS:
                flags_set.append(rpGEOMETRYPOSITIONS)
            if flag_value & rpGEOMETRYTEXTURED:
                flags_set.append(rpGEOMETRYTEXTURED)
            if flag_value & rpGEOMETRYPRELIT:
                prelit = True
                flags_set.append(rpGEOMETRYPRELIT)
            if flag_value & rpGEOMETRYLIGHT:
                flags_set.append(rpGEOMETRYLIGHT)
            if flag_value & rpGEOMETRYNATIVE:
                flags_set.append(rpGEOMETRYNATIVE)
            if flag_value & rpGEOMETRYTRISTRIP:
                flags_set.append(rpGEOMETRYTRISTRIP)
            if flag_value & rpGEOMETRYNORMALS:
                flags_set.append(rpGEOMETRYNORMALS)
            if flag_value & rpGEOMETRYMODULATEMATERIALCOLOR:
                flags_set.append(rpGEOMETRYMODULATEMATERIALCOLOR)
            if flag_value & rpGEOMETRYTEXTURED2:
                flags_set.append(rpGEOMETRYTEXTURED2)


            # numMorphTargets всегда равен 1
            numTriangles, geometryNumVertices,numMorphTarget = struct.unpack('<III', self.file_stream.read(12))
            # numMorphTarget = struct.unpack('<I', self.file_stream.read(4))[0]
            # print(numTriangles, geometryNumVertices, numMorphTarget)

            prelitcolor_list = []
            texcords_list = []
            triangles_list = []

            if flag_value & rpGEOMETRYNATIVE == 0:
                if prelit:
                    # for _ in range(geometryNumVertices):
                    #     data = struct.unpack(f'4B', self.file_stream.read(4))
                    #     prelitcolor_list.append(
                    #         RwRGBA(data[0],data[1],data[2],data[3])
                    #     )
                    data = struct.unpack(f'{4 * geometryNumVertices}B', self.file_stream.read(4 * geometryNumVertices))
                    prelitcolor_list = [
                       RwRGBA(data[i],data[i+1],data[i+2],data[i+3]) for i in range(0, 4 * geometryNumVertices, 4)
                    ]

                numTexSets = (flag_value & 0x00FF0000) >> 16

                # for _ in range(numTexSets):
                #     for _ in range(numTriangles):
                #         data = struct.unpack(f'ff', self.file_stream.read(8))
                #         texcords_list.append(
                #              RwTexCoords(data[0], data[1])
                #         )
                data = struct.unpack(f'{numTexSets * geometryNumVertices * 2}f', self.file_stream.read(numTexSets * geometryNumVertices * 8))
                texcords_list = [
                    RwTexCoords(data[i], data[i+1]) for i in range(0, numTexSets * geometryNumVertices * 2, 2)
                ]
                # for _ in range(numTriangles):
                #     data = struct.unpack(f'HHHH', self.file_stream.read(8))
                #     triangles_list.append(
                #         RpTriangle(data[0], data[1], data[2], data[3])
                #     )
                data = struct.unpack(f'{numTriangles * 4}H', self.file_stream.read(numTriangles * 8))
                triangles_list = [
                    RpTriangle(data[i], data[i+1], data[i+2], data[i+3]) for i in range(0, numTriangles * 4, 4)
                ]


            data = struct.unpack(f'4f', self.file_stream.read(16))
            bounding_sphere = RwSphere(x=data[0], y=data[1], z=data[2], radius=data[3])

            has_vertices, has_normals = struct.unpack('II', self.file_stream.read(8))

            vertices = []
            normals =  []

            if has_vertices:
                data = struct.unpack(f'{3 * geometryNumVertices}f', self.file_stream.read(geometryNumVertices * 12))
                vertices = [
                    RwV3d(data[i], data[i+1], data[i+2]) for i in range(0, geometryNumVertices * 3, 3)
                ]


            if has_normals:
                data = struct.unpack(f'{3 * geometryNumVertices}f', self.file_stream.read(geometryNumVertices * 12))
                normals = [
                    RwV3d(data[i], data[i+1], data[i+2]) for i in range(0, geometryNumVertices * 3, 3)
                ]


            return GeometrySection(
                format=flag_value,
                flags_set=flags_set,
                num_of_triangles=numTriangles,
                num_of_vertices=geometryNumVertices,
                number_of_morph_targets=numMorphTarget,

                has_vertices=has_vertices,
                has_normals=has_normals,
                normals=normals,
                vertices=vertices,
                bounding_sphere=bounding_sphere,

                prelitcolor=prelitcolor_list,
                triangles=triangles_list,
                tex_coords=texcords_list
            )
        if section_type is SectionType.MATERIAL_LIST:
            number_of_materials = struct.unpack('I', self.file_stream.read(4))[0]
            raw_data = struct.unpack(f'{number_of_materials}I', self.file_stream.read(4 * number_of_materials))

            return MaterialListSection(
                number_of_materials=number_of_materials,
                data=raw_data
            )
        if section_type is SectionType.MATERIAL:
            flags_material = struct.unpack('<I', self.file_stream.read(4))[0]
            
            #RwRGBA
            data = struct.unpack('BBBB', self.file_stream.read(4))
            color = RwRGBA(data[0], data[1], data[2], data[3])

            # unsued
            struct.unpack('<I', self.file_stream.read(4))

            # IsTextured
            is_textured  = bool(struct.unpack('<I', self.file_stream.read(4))[0])

            ambient, specular, diffuse = struct.unpack('<fff', self.file_stream.read(12))
            return MaterialSection(
                ambient=ambient,
                specular=specular,
                diffuse=diffuse,
                flags=flags_material,
                color=color,
                is_textured=is_textured
            )
        if section_type is SectionType.TEXTURE:
            # return self.file_stream.read(4)
            # texture_filtering, u_addressing, v_addressing = struct.unpack('<2BH', self.file_stream.read(4))
            # texture_filtering, u_addressing, v_addressing, use_mipmap = struct.unpack('<IIII', self.file_stream.read(16))
            # texture_filtering, u_addressing, v_addressing, use_mipmap = struct.unpack('IIII', self.file_stream.read(16))
            # print(texture_filtering, u_addressing, v_addressing, use_mipmap)
            # name = struct.unpack(f'{data - 40 - 16}s', self.file_stream.read(data - 40 - 16))[0]
            # print(len(name), name)
            return self.file_stream.read(4)
        if section_type is SectionType.STRING:
            name = struct.unpack(f'{data}s', self.file_stream.read(data))[0]
            return StringSection(
                name=name.decode('utf-8')
            )
        if section_type is SectionType.BREAKABLE:
            name = struct.unpack(f'<I', self.file_stream.read(data))[0]
            return BreakableSection(
                magic_number=name
            )
        if section_type is SectionType.BIN_MESH_PLG:
            flags, numMeshes, totalNumber = struct.unpack('<III', self.file_stream.read(12))


            list_meshes = []
            for i in range(numMeshes):
                numOfIndices, materialIndex = struct.unpack('<II', self.file_stream.read(8))
                indices = []
                for j in range(numOfIndices):
                    indices.append(struct.unpack('<I', self.file_stream.read(4))[0])
                
                list_meshes.append(
                    {
                        'number_of_indices': numOfIndices,
                        'material_index': materialIndex,
                        'indices': indices
                    }
                )

            return BinMeshPLGSection(
                flags=flags,
                number_of_meshes=numMeshes,
                total_number_of_indices=totalNumber,
                list_meshes=list_meshes
            )
        if section_type is SectionType.EXTRA_VERT_COLOUR:
            magic_number = struct.unpack('<I', self.file_stream.read(4))[0]
            night_vert_colours = []

            if magic_number > 0:
                p = struct.unpack(f'{4*data}B', self.file_stream.read(4*data))
                night_vert_colours = [
                    RwRGBA(p[i], p[i+1], p[i+2], p[i+3]) for i in range(0, 4*data, 4)
                ]

            return ExtraVertColourSection(
                magic_number=magic_number,
                night_vert_color=night_vert_colours
            )
        if section_type is SectionType.ATOMIC:
            frame_index, geometryIndex, flags,_ = struct.unpack('<4I', self.file_stream.read(16))
            return AtomicStruct(
                frame_index=frame_index,
                geometry_index=geometryIndex,
                flags=flags
            )
        if section_type is SectionType.TWOD_EFFECT:
            # pos = struct.unpack('fff', self.file_stream.read(12))
            # entry_type = struct.unpack('I', self.file_stream.read(4))
            # data_size = struct.unpack('I', self.file_stream.read(4))
            # print(pos, entry_type, data_size)
            ...
    def __enter__(self):
        self.file_stream = open(self.file, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file_stream.close()


def main() -> None:
    # # izbushka_psx
    # korobka
    with DffParser('./dff_files/izbushka_psx.dff') as f:
        data = f.get_struct()
        print(data)
        print(f.get_body(data.section_type))

        frame_list_section = f.get_struct()
        print(frame_list_section)
        frame_list = f.get_body(frame_list_section.section_type)
        print(frame_list)

        for i in range(frame_list.frame_count):
            data = f.get_struct()
            print(data)
            print(f.get_body(data.section_type, data.size))

        geometry_list = f.get_struct()
        print(geometry_list)
        print(f.get_body(geometry_list.section_type))

        data = f.get_struct()
        print(data)
        geometry_data: GeometrySection = f.get_body(data.section_type)
        # print(geometry_data)

        data = f.get_struct()
        # print(material_list_data)
        material_list_data = f.get_body(data.section_type)
        # print(material_list_data)
        for i in range(material_list_data.number_of_materials):
            # if data.section_type is SectionType.MATERIAL:
                # print(material_data)
            data = f.get_struct()
            print(data)
            material_data = f.get_body(data.section_type)
            print(material_data)

            data = f.get_struct()
            print(data)
            texture_data = f.get_body(data.section_type, data.size_2)
            print(texture_data)

            data = f.get_struct()
            print(data)
            string_name = f.get_body(data.section_type, data.size)
            data = f.get_struct()
            print(data)
            mask_name = f.get_body(data.section_type, data.size)
            print(string_name, mask_name)

            print(f.get_struct())
            # else:
                # data = f.get_struct()
            

            # data = f.get_struct()
            # print(data)
            # mask_name = f.get_body(data.section_type, data.size)
            # print(mask_name)

        data = f.get_struct()
        print(data)
        bin_meshes = f.get_body(data.section_type)
        print(bin_meshes)
        # exit()

        data = f.get_struct()
        print(data)
        breakable = f.get_body(data.section_type, data.size)
        print(breakable)

        data = f.get_struct()
        print(data)
        
        extra_vert_colour: ExtraVertColourSection = f.get_body(data.section_type, geometry_data.num_of_vertices)
        # print(extra_vert_colour.night_vert_color)
        # print(extra_vert_colour)
        # print(extra_vert_colour)
        # print(extra_vert_colour)

        data = f.get_struct()
        print(data)
        atomic_data = f.get_body(data.section_type)
        print(atomic_data)

        data = f.get_struct()
        print(data)
        data = f.get_struct()
        if data is None:
            print('Готово')
        # data = f.get_struct()
        # print(data)
        # print(texture_data)
        # print(f.get_struct())

if __name__ == '__main__':
    main()
    # exit()


# with open('./dff_files/izbushka_hand.dff', 'rb') as f:
#     # Header
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#     #struct
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#     #clump_data
#     atomics, lights, cameras = struct.unpack('<III', f.read(12))
#     print(atomics, lights, cameras)
#     # Frame list
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#     # Struct 
#     struct_id, size, version = struct.unpack('<III', f.read(12))
#     print(struct_id, size, version)


#     frame_count = struct.unpack('<I', f.read(4))[0]
#     print(frame_count, frame_count * 0x44, 'frame_count')
#     frame_data = f.read((frame_count * 0x38))
#     print(frame_data, 'frame_data')
#     # print([frame_data[i:i+0x44] for i in range(0, len(frame_data), 0x44)])

#     # exit()
#     # Node Name
#     struct_id, size, version = struct.unpack('<III', f.read(12))
#     print(struct_id, size, hex(unpack_version(version)), version)

#     struct_id, size, version = struct.unpack('<III', f.read(12))
#     print(struct_id, size, hex(unpack_version(version)), version)
#     # exit()
#     print(size)


#     t = struct.unpack(f'{size}s', f.read(size))
#     print(t[0])
#     # exit()
#     # exit()
    
#     # Geometry list
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ), 'geometry_list')
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ), 'bebra')
#     print(struct.unpack(f'{t[1]}s', f.read(t[1])))


#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ), 'geometry_list')
    

#     # Geometry
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#     t = struct.unpack('<III', f.read(12))
#     print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#     flag_value = struct.unpack('<I', f.read(4))[0]

#     exit()

#     prelit = False

#     if flag_value & rpGEOMETRYPOSITIONS:
#         print("rpGEOMETRYPOSITIONS is set")
#     if flag_value & rpGEOMETRYTEXTURED:
#         print("rpGEOMETRYTEXTURED is set")
#     if flag_value & rpGEOMETRYPRELIT:
#         prelit = True
#         print("rpGEOMETRYPRELIT is set")
#     if flag_value & rpGEOMETRYLIGHT:
#         print("rpGEOMETRYLIGHT is set")
#     if flag_value & rpGEOMETRYNATIVE:
#         print("rpGEOMETRYNATIVE is set")
#     if flag_value & rpGEOMETRYTRISTRIP:
#         print("rpGEOMETRYTRISTRIP is set")
#     if flag_value & rpGEOMETRYNORMALS:
#         print("rpGEOMETRYNORMALS is set")
#     if flag_value & rpGEOMETRYMODULATEMATERIALCOLOR:
#         print("rpGEOMETRYMODULATEMATERIALCOLOR is set")
#     if flag_value & rpGEOMETRYTEXTURED2:
#         print("rpGEOMETRYTEXTURED2 is set")

#     # struct_id, size, version = struct.unpack('<III', f.read(12))
#     # print(struct_id, size, hex(unpack_version(version)), version)
#     # exit()

#     # Triangles
#     numTriangles = struct.unpack('<I', f.read(4))[0]
#     print(numTriangles)
#     # Vertices
#     geometryNumVertices = struct.unpack('<I', f.read(4))[0]
#     print('num vertices', geometryNumVertices)

#     # numMorphTargets всегда равен 1
#     print(struct.unpack('<I', f.read(4))[0])

#     if flag_value & rpGEOMETRYNATIVE == 0:
#         if prelit:
#             # prelitcolor
#             for i in range(geometryNumVertices):
#                 data = f.read(4)
#                 try:
#                     struct.unpack('BBBB', data), flag_value
#                 except Exception as ex:
#                     print(data, geometryNumVertices)
#                     # print(f.read(30))
#                     exit()

#             numTexSets = (flag_value & 0x00FF0000) >> 16
#             print('tex_sets', numTexSets)

#             # texCoords
#             for i in range(numTexSets):
#                 for j in range(geometryNumVertices):
#                     data_read = f.read(8)
#                     data = struct.unpack('ff', data_read)
#                     print(data, data_read)

#             # triangles
#             for i in range(numTriangles):
#                 vertex2, vertex1, materialId, vertex3 = struct.unpack('HHHH', f.read(8))
#                 # print(vertex2, vertex1, materialId, vertex3)
#                 print(vertex2, vertex1, materialId, vertex3)

#         print()
#         # boundingSphere
#         print(struct.unpack('ffff', f.read(16)))
#         has_vertices, has_normals = struct.unpack('II', f.read(8))


#         if has_vertices:
#             for i in range(geometryNumVertices):
#                 print(struct.unpack('fff', f.read(12)))

#         if has_normals:
#             print('normals...')

#             for i in range(geometryNumVertices):
#                 print(struct.unpack('fff', f.read(12)))


#         # Struct  Material List
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#         # Struct
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#         number_of_material = struct.unpack('<I', f.read(4))
#         print(number_of_material)
#         for i in range(number_of_material[0]):
#             print(struct.unpack('I', f.read(4)), 'gvxno')

#         for i in range(number_of_material[0]):
#             # Struct
#             t = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#             # Material
#             t = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#             flags_material = struct.unpack('<I', f.read(4))
#             print(flags_material)
#             #RwRGBA
#             print(struct.unpack('BBBB', f.read(4)), flag_value)
#             print(struct.unpack('<I', f.read(4)))
#             # IsTextured
#             is_textured  = struct.unpack('<I', f.read(4))
#             print(is_textured)

#             ambient, specular, diffuse = struct.unpack('<fff', f.read(12))
#             print(ambient, specular, diffuse)

#             # print(f.read(23))
#             # Struct
#             struct_id, size, version = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#             # Material
#             t = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))


#             texture_filtering = struct.unpack('I', f.read(4))
#             print(texture_filtering)
#             u_addressing, v_addressing = struct.unpack('<II', f.read(8))
#             # print(u_addressing, v_addressing)
#             print(struct.unpack('I', f.read(4)))
#             name_ponos = struct.unpack(f'{size - 40 - 16}s', f.read(size - 40 - 16))
#             print(name_ponos)


#             t = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#             #string
#             print(struct.unpack('4s', f.read(4))) # name
#             # print(struct.unpack('4s', f.read(4))) # mask name

#             # Extension
#             t = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#             t = struct.unpack('<III', f.read(12))
#             print(t, hex(t[0]), hex( unpack_version(t[2]) ))


#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#         # Bin Mesh PLG
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))
        
#         flags, numMeshes, totalNumber = struct.unpack('<III', f.read(12))
#         print(flags, numMeshes, totalNumber)


#         for i in range(numMeshes):
#             numOfIndices, materialIndex = struct.unpack('<II', f.read(8))
#             indices = []
#             for j in range(numOfIndices):
#                 indices.append(struct.unpack('<I', f.read(4)))

#         print(indices)

#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#         # Breakable
#         # t = struct.unpack('<III', f.read(12))
#         # print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#         magicNumber = struct.unpack('<I', f.read(4))
#         print(magicNumber)
#         # Extra Vert Colour
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#         magicNumber = struct.unpack('<I', f.read(4))
#         print(magicNumber,geometryNumVertices * 4)
#         unpacked_data = struct.unpack(f'{geometryNumVertices * 4}B', f.read(geometryNumVertices * 4))
#         nightVertColours = [
#             unpacked_data[i:i+4] for i in range(0, len(unpacked_data), 4)
#         ]
#         # print(nightVertColours)

#         # Atomic
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))

#         frameIndex, geometryIndex, flags, _ = struct.unpack('<IIII', f.read(16))
#         print(frameIndex, geometryIndex, hex(flags))

#         # Extension
#         t = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#         struct_id, size, version = struct.unpack('<III', f.read(12))
#         print(t, hex(t[0]), hex( unpack_version(t[2]) ))
#         if size == 0:
#             print('Готово сучка')
#         else:
#             print(f.read())
