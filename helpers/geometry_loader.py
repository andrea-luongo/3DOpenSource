from PySide2.QtCore import QFileInfo, QTime
from PySide2.QtGui import QVector3D
import numpy as np
import struct


# load stl file detects if the file is a text file or binary file
def load_geometry(file_name, swap_yz=False):
    file_extension = QFileInfo(file_name).suffix()
    if file_extension.lower() == 'obj':
        return load_obj(file_name, swap_yz)
    elif file_extension.lower() == 'stl':
        return load_stl(file_name, swap_yz)
    
    
def load_stl(filename, swap_yz=False):
    # read start of file to determine if its a binay stl file or a ascii stl file
    if not filename:
        return False
    fp = open(filename, 'rb')
    try:
        header = fp.read(80 + 20).decode('ASCII')  # read 80 bytes for heade plus 20 bytes to avoid SolidWorks Binary files
        stl_type = header[0:5]
    except UnicodeDecodeError:
        stl_type = 'binary'
    fp.close()
    if stl_type == 'solid':
        is_loaded, vertices_list, normals_list, bbox_min, bbox_max = load_text_stl(filename, swap_yz)
        if not is_loaded:
            return load_binary_stl(filename, swap_yz)
        else:
            return is_loaded, vertices_list, normals_list, bbox_min, bbox_max
    else:
        return load_binary_stl(filename, swap_yz)


# read text stl match keywords to grab the points to build the model
def load_text_stl(filename, swap_yz=False, test=True):
    fp = open(filename, 'r')
    number_of_triangles = 0
    normals_list = []
    vertices_list = []
    is_bbox_defined = False
    bbox_min = None
    bbox_max = None
    try:
        for line in fp.readlines():
            words = line.split()
            if len(words) > 0:
                if words[0] == 'facet':
                    number_of_triangles += 1
                    v = [float(words[2]), float(words[3]), float(words[4])]
                    if swap_yz:
                        v = [-v[0], v[2], v[1]]
                    normals_list.append(v)
                    normals_list.append(v)
                    normals_list.append(v)
                if words[0] == 'vertex':
                    v = [float(words[1]), float(words[2]), float(words[3])]
                    if swap_yz:
                        v = [-v[0], v[2], v[1]]
                    vertices_list.append(v)
                    q_v = QVector3D(v[0], v[1], v[2])
                    if is_bbox_defined:
                        min_temp = np.minimum(bbox_min.toTuple(), v)
                        max_temp = np.maximum(bbox_max.toTuple(), v)
                        bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                        bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                    else:
                        bbox_max = q_v
                        bbox_min = q_v
                        is_bbox_defined = True
    except Exception as e:
        fp.close()
        return False, vertices_list, normals_list, bbox_min, bbox_max
    fp.close()
    # bbox recentering around origin
    bbox_center = 0.5 * (bbox_min + bbox_max)
    for idx in range(len(vertices_list)):
        vertices_list[idx] = vertices_list[idx] - np.array(bbox_center.toTuple())
    bbox_min = bbox_min - bbox_center
    bbox_max = bbox_max - bbox_center
    vertices_list = np.array(vertices_list, dtype=np.float32).ravel()
    normals_list = np.array(normals_list, dtype=np.float32).ravel()
    return True, vertices_list, normals_list, bbox_min, bbox_max


def load_binary_stl(filename, swap_yz=False):
    normals_list = []
    vertices_list = []
    is_bbox_defined = False
    bbox_min = None
    bbox_max = None
    fp = open(filename, 'rb')
    header = fp.read(80)
    # read 4 bytes describing the number of triangles, and convert them to integer
    number_of_triangles = struct.unpack('I', fp.read(4))[0]
    for idx in range(number_of_triangles):
        try:
            normal_bytes = fp.read(12)
            if len(normal_bytes) == 12:
                normal = struct.unpack('f', normal_bytes[0:4])[0], struct.unpack('f', normal_bytes[4:8])[0], \
                         struct.unpack('f', normal_bytes[8:12])[0]
                if swap_yz:
                    normal = [-normal[0], normal[2], normal[1]]
                normals_list.append(normal)
                normals_list.append(normal)
                normals_list.append(normal)
            v0_bytes = fp.read(12)
            if len(v0_bytes) == 12:
                v0 = struct.unpack('f', v0_bytes[0:4])[0], struct.unpack('f', v0_bytes[4:8])[0], \
                     struct.unpack('f', v0_bytes[8:12])[0]
                if swap_yz:
                    v0 = [-v0[0], v0[2], v0[1]]
                vertices_list.append(v0)
                q_v0 = QVector3D(v0[0], v0[1], v0[2])
                if is_bbox_defined:
                    min_temp = np.minimum(bbox_min.toTuple(), v0)
                    max_temp = np.maximum(bbox_max.toTuple(), v0)
                    bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                    bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                else:
                    bbox_max = q_v0
                    bbox_min = q_v0
                    is_bbox_defined = True
            v1_bytes = fp.read(12)
            if len(v1_bytes) == 12:
                v1 = struct.unpack('f', v1_bytes[0:4])[0], struct.unpack('f', v1_bytes[4:8])[0], \
                     struct.unpack('f', v1_bytes[8:12])[0]
                if swap_yz:
                    v1 = [-v1[0], v1[2], v1[1]]
                vertices_list.append(v1)
                q_v1 = QVector3D(v1[0], v1[1], v1[2])
                if is_bbox_defined:
                    min_temp = np.minimum(bbox_min.toTuple(), v1)
                    max_temp = np.maximum(bbox_max.toTuple(), v1)
                    bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                    bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                else:
                    bbox_max = q_v1
                    bbox_min = q_v1
                    is_bbox_defined = True
            v2_bytes = fp.read(12)
            if len(v2_bytes) == 12:
                v2 = struct.unpack('f', v2_bytes[0:4])[0], struct.unpack('f', v2_bytes[4:8])[0], \
                     struct.unpack('f', v2_bytes[8:12])[0]
                v2 = [-v2[0], v2[2], v2[1]]
                vertices_list.append(v2)
                q_v2 = QVector3D(v2[0], v2[1], v2[2])
                if is_bbox_defined:
                    min_temp = np.minimum(bbox_min.toTuple(), v2)
                    max_temp = np.maximum(bbox_max.toTuple(), v2)
                    bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                    bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                else:
                    bbox_max = q_v2
                    bbox_min = q_v2
                    is_bbox_defined = True
            attribute_bytes = fp.read(2)
            if len(attribute_bytes) == 0:
                break
        except EOFError:
            break
        except Exception as e:
            return False, vertices_list, normals_list, bbox_min, bbox_max
    fp.close()
    # bbox recentering around origin
    bbox_center = 0.5 * (bbox_min + bbox_max)
    for idx in range(len(vertices_list)):
        vertices_list[idx] = vertices_list[idx] - np.array(bbox_center.toTuple())
    bbox_min = bbox_min - bbox_center
    bbox_max = bbox_max - bbox_center
    vertices_list = np.array(vertices_list, dtype=np.float32).ravel()
    normals_list = np.array(normals_list, dtype=np.float32).ravel()
    return True, vertices_list, normals_list, bbox_min, bbox_max


def load_obj(filename, swap_yz=False):
    """Loads a Wavefront OBJ file. """
    number_of_triangles = 0
    normals_list = []
    vertices_list = []
    texcoords_list = []
    is_bbox_defined = False
    bbox_min = None
    bbox_max = None
    tmp_vertices = []
    tmp_normals = []
    tmp_texcoords = []
    tmp_faces = []
    for line in open(filename, "r"):
        if line.startswith('#'):
            continue
        values = line.split()
        if not values:
            continue
        if values[0] == 'v':
            v = [float(values[1]), float(values[2]), float(values[3])]
            if swap_yz:
                v = [-v[0], v[2], v[1]]
            tmp_vertices.append(v[0])
            tmp_vertices.append(v[1])
            tmp_vertices.append(v[2])
            q_v = QVector3D(v[0], v[1], v[2])
            if is_bbox_defined:
                min_temp = np.minimum(bbox_min.toTuple(), v)
                max_temp = np.maximum(bbox_max.toTuple(), v)
                bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
            else:
                bbox_max = q_v
                bbox_min = q_v
                is_bbox_defined = True
        elif values[0] == 'vn':
            v = [float(values[1]), float(values[2]), float(values[3])]
            if swap_yz:
                v = [-v[0], v[2], v[1]]
            tmp_normals.append(v[0])
            tmp_normals.append(v[1])
            tmp_normals.append(v[2])
        elif values[0] == 'vt':
            tmp_texcoords.append([float(values[1]), float(values[2])])
        elif values[0] == 'f':
            number_of_triangles += 1
            face = []
            tmp_texcoords = []
            norms = []
            for v in values[1:]:
                w = v.split('/')
                face.append(int(w[0]))
                if len(w) >= 2 and len(w[1]) > 0:
                    tmp_texcoords.append(int(w[1]))
                else:
                    tmp_texcoords.append(0)
                if len(w) >= 3 and len(w[2]) > 0:
                    norms.append(int(w[2]))
                else:
                    norms.append(0)
            tmp_faces.append((face, norms, tmp_texcoords))
    # bbox recentering around origin
    bbox_center = 0.5 * (bbox_min + bbox_max)
    bbox_min = bbox_min - bbox_center
    bbox_max = bbox_max - bbox_center
    tmp_vertices = np.array(tmp_vertices)
    tmp_normals = np.array(tmp_normals)
    tmp_texcoords = np.array(tmp_normals)
    for face in tmp_faces:
        vertices_idx, normals_idx, texture_idx = face
        for i in range(len(vertices_idx)):
            if normals_idx[i] > 0:
                normals_list.append(tmp_normals[3 * (normals_idx[i] - 1)])
                normals_list.append(tmp_normals[3 * (normals_idx[i] - 1) + 1])
                normals_list.append(tmp_normals[3 * (normals_idx[i] - 1) + 2])
            if texture_idx[i] > 0:
                texcoords_list.append(tmp_texcoords[3 * (texture_idx[i] - 1)])
                texcoords_list.append(tmp_texcoords[3 * (texture_idx[i] - 1) + 1])
                texcoords_list.append(tmp_texcoords[3 * (texture_idx[i] - 1) + 2])
            vertices_list.append(tmp_vertices[3 * (vertices_idx[i] - 1)] - bbox_center.x())
            vertices_list.append(tmp_vertices[3 * (vertices_idx[i] - 1) + 1] - bbox_center.y())
            vertices_list.append(tmp_vertices[3 * (vertices_idx[i] - 1) + 2] - bbox_center.z())
    vertices_list = np.array(vertices_list, dtype=np.float32).ravel()
    normals_list = np.array(normals_list, dtype=np.float32).ravel()
    return True, vertices_list, normals_list, bbox_min, bbox_max
