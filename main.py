import struct
import os

IMG_ARCHIVE_PATH = r"C:\Games\GTA Criminal Russia\models\gamemod.img"

with open(IMG_ARCHIVE_PATH, 'rb') as f:
    version, files_count = struct.unpack('4sI',f.read(8))
    print(version, files_count)
    files_data = []
    for i in range(files_count):
        offset, streaming_size, _, name = struct.unpack('Ihh24s', f.read(32))
        files_data.append({
            'offset': offset, 
            'streaming_size': streaming_size, 
            'name': name.decode('utf-8').rstrip('\x00')
        })
    if not os.path.exists('./files_data'):
        os.mkdir('./files_data')
    for i in files_data:
        f.seek(i['offset'] * 2048)
        with open(f'./files_data/{i["name"]}', 'wb') as b:
            b.write(f.read(2048 * i['streaming_size']))
            print(f'Сохранен файл: {i["name"]}')
