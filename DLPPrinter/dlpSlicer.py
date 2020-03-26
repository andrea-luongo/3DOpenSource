import numpy as np
from PySide2.QtWidgets import QOpenGLWidget
from PySide2.QtCore import Signal, Slot, QTimer, QTime, QFileInfo, QRect, Qt
from PySide2.QtGui import QVector3D, QOpenGLFunctions,\
    QQuaternion, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QImage, QMatrix4x4
from OpenGL import GL
import struct

class DLPSlicer(QOpenGLWidget, QOpenGLFunctions):

    update_physical_size = Signal(float, float, float)
    update_fps = Signal(float)
    update_slice_counts = Signal(float, float)

    vertex_shader = """
    #version 330
    in vec3 vin_position;
    in vec3 vin_normal;
    uniform vec3 light_direction;
    uniform mat4 camera_matrix;
    uniform mat4 model_matrix;
    uniform mat4 projection_matrix;
    uniform mat3 normal_matrix;
    out vec3 L;
    out vec3 N;
    void main(void)
    {
        vec4 pos = camera_matrix * model_matrix * vec4(vin_position, 1.0);
        L = - (camera_matrix * vec4(normalize(light_direction), 0.0)).xyz;
        N = normalize(normal_matrix * vin_normal);
        gl_Position =  projection_matrix * pos;
    }
    """

    fragment_shader = """
    #version 330
    in vec3 L;
    in vec3 N;
    out vec4 fout_color;
    uniform vec3 light_intensity;
    uniform vec3 ambient_color;
    uniform vec3 diffuse_color;
    void main(void)
    {
        
        vec3 f_N = normalize(N);
        vec3 f_L = normalize(L);
        float K_d = max(dot(f_L , f_N), 0.0);
        vec3 diffuse = K_d * diffuse_color * light_intensity;        
        
        fout_color = vec4(ambient_color + diffuse, 1.0);
        //fout_color = vec4(K_d, K_d, K_d, 1.0);
    }
    """

    slicer_vertex_shader = """
    #version 330
    in vec3 vin_position;
    uniform mat4 camera_matrix;
    uniform mat4 model_matrix;
    uniform mat4 projection_matrix;
    out vec3 vout_color;
    void main(void)
    {
        vout_color = vec3(1.0, 1.0, 1.0);
        gl_Position = projection_matrix * camera_matrix * model_matrix * vec4(vin_position, 1.0);
    }
    """
    slicer_fragment_shader = """
    #version 330
    in vec3 vout_color;
    uniform float alpha;
    out vec4 fout_color;
    void main(void)
    {
        fout_color = vec4(vout_color, alpha);
    }
    """

    def __init__(self, dlp_controller=None, parent=None):
        QOpenGLWidget.__init__(self, parent)

        QOpenGLFunctions.__init__(self)
        if dlp_controller:
            self.dlp_controller = dlp_controller

        # shader variables
        self.program_id = None
        self.slicer_program_id = None
        self.multisample_fbo = None
        self.temp_fbo = None
        self.camera_matrix_location = None
        self.model_matrix_location = None
        self.projection_matrix_location = None
        self.eye_position_location = None
        self.look_at_location = None
        self.light_intensity_location = None
        self.position_location = None
        self.normal_location = None
        self.normal_matrix_location = None
        self.light_location = None
        self.ambient_location = None
        self.diffuse_location = None
        self.slicer_position_location = None
        self.slicer_camera_matrix_location = None
        self.slicer_model_matrix_location = None
        self.slicer_projection_matrix_location = None
        self.slicer_alpha_location = None
        
        # camera variables
        self.w = 1
        self.h = 1
        self.camera_radius = 10
        self.camera_rotation = QQuaternion()
        self.eye = QVector3D(0.0, 0.50, 1.0)
        self.eye = self.camera_radius * self.camera_rotation.rotatedVector(self.eye)
        self.look_at = QVector3D(0.0, 0.0, 0.0)
        self.fov = 45
        self.up = QVector3D(0.0, 1.0, 0.0)
        self.camera_matrix = QMatrix4x4()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)
        self.perspective_matrix = QMatrix4x4()
        self.perspective_matrix_array = np.asarray(self.perspective_matrix.copyDataTo(), np.float32)

        # slicer variables
        self.slicer_eye = QVector3D(0.0, 0.0, 0.0)
        self.slicer_look_at = QVector3D(0.0, 0.0, 0.0)
        self.slicer_up = QVector3D(0.0, 0.0, 0.0)
        self.slicer_camera_matrix = QMatrix4x4()
        self.slicer_camera_matrix_array = np.asarray(self.slicer_camera_matrix.copyDataTo(), np.float32)
        self.ortho_matrix = QMatrix4x4()
        self.ortho_matrix_array = np.asarray(self.ortho_matrix.copyDataTo(), np.float32)
        self.pixel_size_microns = self.dlp_controller.projector_pixel_size * 1000  # microns
        self.projector_width = self.dlp_controller.projector_width
        self.projector_height = self.dlp_controller.projector_height
        self.slice_width = self.projector_width
        self.slice_height = self.projector_height
        self.samples_per_pixel = self.dlp_controller.samples_per_pixel
        self.slice_thickness_microns = self.dlp_controller.support_thickness * 1000  # microns
        self.current_slice = 0
        self.number_of_slices = 0
        self.is_slicing = False
        self.global_bbox_min = QVector3D(0.0, 0.0, 0.0)
        self.global_bbox_max = QVector3D(0.0, 0.0, 0.0)

        # quad plane variables
        self.quad_vertex_buffer = None
        self.quad_normal_buffer = None
        self.quad_vertices = None
        self.quad_normals = None
        self.quad_model_matrix = QMatrix4x4()
        self.quad_normal_matrix = self.quad_model_matrix.normalMatrix()
        self.quad_model_matrix_array = np.asarray(self.quad_model_matrix.copyDataTo(), np.float32)
        self.quad_normal_matrix_array = np.asarray(self.quad_normal_matrix.data(), np.float32)

        # geometry variables
        self.current_geometry_idx = 0
        self.geometries_loaded = 0
        self.vertices_list = []
        self.normals_list = []
        self.vertex_buffer_list = []
        self.normal_buffer_list = []
        self.translation_matrix_list = []
        self.bbox_translation_matrix_list = []
        self.rotation_matrix_list = []
        self.scale_matrix_list = []
        self.model_matrix_list = []
        self.normal_matrix_list = []
        self.model_matrix_array_list = []
        self.normal_matrix_array_list = []
        self.x_rot_list = []
        self.y_rot_list = []
        self.z_rot_list = []
        self.scale_x_list = []
        self.scale_y_list = []
        self.scale_z_list = []
        self.x_pos_list = []
        self.z_pos_list = []
        self.unit_of_measurement_list = [] # equal to 1 if in mm, equal to 0.001 if in microns
        self.uniform_scaling_list = []
        self.geometry_name_list = []
        self.bbox_min_list = []
        self.bbox_max_list = []
        self.transformed_bbox_min_list = []
        self.transformed_bbox_max_list = []
        self.bbox_width_mm_list = []
        self.bbox_depth_mm_list = []
        self.bbox_height_mm_list = []
        self.bbox_width_microns_list = []
        self.bbox_depth_microns_list = []
        self.bbox_height_microns_list = []
        self.is_bbox_defined_list = []
        self.is_bbox_refined_list = []

        # generic variables
        self.save_directory_name = ''
        self.previous_frame_count = 0
        self.previous_time = 0
        self.current_frame = 0
        self.__timer = None
        self.frameTimer = None
        self.mouse_last_pos = None

        # lighting variables
        self.light_intensity = QVector3D(1.0, 1.0, 1.0)
        self.light_direction = self.look_at - self.eye
        self.ambient_color = QVector3D(0.2, 0.2, 0.2)
        self.diffuse_color = QVector3D(0.7, 0.3, 0.0)
        self.selected_geometry_diffuse_color = QVector3D(1.0, 0.45, 0.45)
        self.quad_ambient_color = QVector3D(0.0, 0.3, 0.7)
        self.quad_diffuse_color = QVector3D(0.0, 0.0, 0.0)

        self.update_model_matrix()
        self.update_quad_scale()

    def append_geometries_default_parameters(self, geometry_idx=0):
        self.vertices_list.append([])
        self.normals_list.append([])
        self.translation_matrix_list.append(QMatrix4x4())
        self.bbox_translation_matrix_list.append(QMatrix4x4())
        self.rotation_matrix_list.append(QMatrix4x4())
        self.scale_matrix_list.append(QMatrix4x4())
        self.model_matrix_list.append(QMatrix4x4())
        self.normal_matrix_list.append(self.model_matrix_list[geometry_idx].normalMatrix())
        self.model_matrix_array_list.append(np.asarray(self.model_matrix_list[geometry_idx].copyDataTo(), np.float32))
        self.normal_matrix_array_list.append(np.asarray(self.normal_matrix_list[geometry_idx].data(), np.float32))
        self.x_rot_list.append(0)
        self.y_rot_list.append(0)
        self.z_rot_list.append(0)
        self.scale_x_list.append(1)
        self.scale_y_list.append(1)
        self.scale_z_list.append(1)
        self.x_pos_list.append(0)
        self.z_pos_list.append(0)
        self.unit_of_measurement_list.append(1)  # equal to 1 if in mm, equal to 0.001 if in microns
        self.uniform_scaling_list.append(True)
        self.geometry_name_list.append(None)
        self.bbox_min_list.append(QVector3D(0.0, 0.0, 0.0))
        self.bbox_max_list.append(QVector3D(0.0, 0.0, 0.0))
        self.transformed_bbox_min_list.append(QVector3D(0.0, 0.0, 0.0))
        self.transformed_bbox_max_list.append(QVector3D(0.0, 0.0, 0.0))
        self.bbox_width_mm_list.append(0.0)
        self.bbox_depth_mm_list.append(0.0)
        self.bbox_height_mm_list.append(0.0)
        self.bbox_width_microns_list.append(0)
        self.bbox_depth_microns_list.append(0)
        self.bbox_height_microns_list.append(0)
        self.is_bbox_defined_list.append(False)
        self.is_bbox_refined_list.append(False)

    @Slot(float)
    def set_pixel_size(self, value):
        self.pixel_size_microns = value
        self.update_quad_scale()

    @Slot(int)
    def set_projector_width(self, value):
        self.projector_width = value
        self.update_quad_scale()

    @Slot(int)
    def set_projector_height(self, value):
        self.projector_height = value
        self.update_quad_scale()

    def update_quad_scale(self):
        half_width_mm = self.projector_width * self.pixel_size_microns * 0.5 * 0.001
        half_height_mm = self.projector_height * self.pixel_size_microns * 0.5 * 0.001
        self.quad_model_matrix = QMatrix4x4()
        self.quad_model_matrix.scale(half_width_mm, 1.0, half_height_mm)
        self.quad_model_matrix_array = np.asarray(self.quad_model_matrix.copyDataTo(), np.float32)
        self.quad_normal_matrix = self.quad_model_matrix.normalMatrix()
        self.quad_normal_matrix_array = np.asarray(self.quad_normal_matrix.data(), np.float32)

    @Slot(float)
    def set_slice_thickness(self, value):
        self.slice_thickness_microns = value

    @Slot(int)
    def set_samples_per_pixel(self, value):
        self.samples_per_pixel = value

    @Slot(int)
    def set_x_rotation(self, value):
        if self.geometries_loaded > 0:
            self.x_rot_list[self.current_geometry_idx] = value
            new_rotation_matrix = QMatrix4x4()
            new_rotation_matrix.rotate(self.x_rot_list[self.current_geometry_idx], 1.0, 0.0, 0.0)
            new_rotation_matrix.rotate(self.y_rot_list[self.current_geometry_idx], 0.0, 1.0, 0.0)
            new_rotation_matrix.rotate(self.z_rot_list[self.current_geometry_idx], 0.0, 0.0, 1.0)
            self.rotation_matrix_list[self.current_geometry_idx] = new_rotation_matrix
            self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(int)
    def set_y_rotation(self, value):
        if self.geometries_loaded > 0:
            self.y_rot_list[self.current_geometry_idx] = value
            new_rotation_matrix = QMatrix4x4()
            new_rotation_matrix.rotate(self.x_rot_list[self.current_geometry_idx], 1.0, 0.0, 0.0)
            new_rotation_matrix.rotate(self.y_rot_list[self.current_geometry_idx], 0.0, 1.0, 0.0)
            new_rotation_matrix.rotate(self.z_rot_list[self.current_geometry_idx], 0.0, 0.0, 1.0)
            self.rotation_matrix_list[self.current_geometry_idx] = new_rotation_matrix
            self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(int)
    def set_z_rotation(self, value):
        if self.geometries_loaded > 0:
            self.z_rot_list[self.current_geometry_idx] = value
            new_rotation_matrix = QMatrix4x4()
            new_rotation_matrix.rotate(self.x_rot_list[self.current_geometry_idx], 1.0, 0.0, 0.0)
            new_rotation_matrix.rotate(self.y_rot_list[self.current_geometry_idx], 0.0, 1.0, 0.0)
            new_rotation_matrix.rotate(self.z_rot_list[self.current_geometry_idx], 0.0, 0.0, 1.0)
            self.rotation_matrix_list[self.current_geometry_idx] = new_rotation_matrix
            self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(float)
    def set_x_scale(self, value):
        if self.geometries_loaded > 0:
            self.scale_x_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(float)
    def set_y_scale(self, value):
        if self.geometries_loaded > 0:
            self.scale_y_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(float)
    def set_z_scale(self, value):
        if self.geometries_loaded > 0:
            self.scale_z_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(float)
    def set_x_pos(self, value):
        if self.geometries_loaded > 0:
            self.x_pos_list[self.current_geometry_idx] = value
            new_translation_matrix = QMatrix4x4()
            new_translation_matrix.translate(self.x_pos_list[self.current_geometry_idx], 0, self.z_pos_list[self.current_geometry_idx])
            self.translation_matrix_list[self.current_geometry_idx] = new_translation_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(float)
    def set_z_pos(self, value):
        if self.geometries_loaded > 0:
            self.z_pos_list[self.current_geometry_idx] = value
            new_translation_matrix = QMatrix4x4()
            new_translation_matrix.translate(self.x_pos_list[self.current_geometry_idx], 0, self.z_pos_list[self.current_geometry_idx])
            self.translation_matrix_list[self.current_geometry_idx] = new_translation_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    @Slot(float)
    def set_unit_of_measurement(self, value):
        if self.geometries_loaded > 0:
            self.unit_of_measurement_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.update_bbox(self.current_geometry_idx)
            self.update_model_matrix(self.current_geometry_idx)

    def get_x_rot(self):
        if self.geometries_loaded > 0:
            return self.x_rot_list[self.current_geometry_idx]

    def get_y_rot(self):
        if self.geometries_loaded > 0:
            return self.y_rot_list[self.current_geometry_idx]

    def get_z_rot(self):
        if self.geometries_loaded > 0:
            return self.z_rot_list[self.current_geometry_idx]

    def get_x_scale(self):
        if self.geometries_loaded > 0:
            return self.scale_x_list[self.current_geometry_idx]

    def get_y_scale(self):
        if self.geometries_loaded > 0:
            return self.scale_y_list[self.current_geometry_idx]

    def get_z_scale(self):
        if self.geometries_loaded > 0:
            return self.scale_z_list[self.current_geometry_idx]

    def get_x_pos(self):
        if self.geometries_loaded > 0:
            return self.x_pos_list[self.current_geometry_idx]

    def get_z_pos(self):
        if self.geometries_loaded > 0:
            return self.z_pos_list[self.current_geometry_idx]

    def get_unit_of_measurement(self):
        if self.geometries_loaded > 0:
            return self.unit_of_measurement_list[self.current_geometry_idx]

    def update_model_matrix(self, geometry_idx=0):
        if self.geometries_loaded > 0:
            self.model_matrix_list[geometry_idx] = self.bbox_translation_matrix_list[geometry_idx] \
                                                                * self.translation_matrix_list[geometry_idx] \
                                                                * self.rotation_matrix_list[geometry_idx] \
                                                                * self.scale_matrix_list[geometry_idx]
            self.model_matrix_array_list[geometry_idx] = np.asarray(self.model_matrix_list[geometry_idx].copyDataTo(), np.float32)
            self.normal_matrix_list[geometry_idx] = (self.camera_matrix * self.model_matrix_list[geometry_idx]).normalMatrix()
            self.normal_matrix_array_list[geometry_idx] = np.asarray(self.normal_matrix_list[geometry_idx].data(), np.float32)

    def refine_bbox(self, geometry_idx=0):
        if self.geometries_loaded > 0:
            if self.is_bbox_refined_list[geometry_idx]:
                return
            refined_bbox_max = QVector3D(0.0, 0.0, 0.0)
            refined_bbox_min = QVector3D(0.0, 0.0, 0.0)
            model_matrix = self.translation_matrix_list[geometry_idx] * self.rotation_matrix_list[geometry_idx]\
                           * self.scale_matrix_list[geometry_idx]
            for idx in range(int(len(self.vertices_list[geometry_idx]) / 3)):
                qv = model_matrix.map(
                    QVector3D(self.vertices_list[geometry_idx][3 * idx], self.vertices_list[geometry_idx][3 * idx + 1], self.vertices_list[geometry_idx][3 * idx + 2]))
                if idx > 0:
                    min_temp = np.minimum(refined_bbox_min.toTuple(), qv.toTuple())
                    max_temp = np.maximum(refined_bbox_max.toTuple(), qv.toTuple())
                    refined_bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                    refined_bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                else:
                    refined_bbox_max = qv
                    refined_bbox_min = qv
            self.transformed_bbox_max_list[geometry_idx] = refined_bbox_max
            self.transformed_bbox_min_list[geometry_idx] = refined_bbox_min
            self.bbox_translation_matrix_list[geometry_idx] = QMatrix4x4()
            self.bbox_translation_matrix_list[geometry_idx].translate(0.0, -self.transformed_bbox_min_list[geometry_idx].y(), 0.0)
            self.bbox_width_mm_list[geometry_idx] = (self.transformed_bbox_max_list[geometry_idx].x() - self.transformed_bbox_min_list[geometry_idx].x())
            self.bbox_depth_mm_list[geometry_idx] = (self.transformed_bbox_max_list[geometry_idx].z() - self.transformed_bbox_min_list[geometry_idx].z())
            self.bbox_height_mm_list[geometry_idx] = (self.transformed_bbox_max_list[geometry_idx].y() - self.transformed_bbox_min_list[geometry_idx].y())
            self.update_physical_size.emit(self.bbox_width_mm_list[geometry_idx], self.bbox_depth_mm_list[geometry_idx], self.bbox_height_mm_list[geometry_idx])
            self.is_bbox_refined_list[geometry_idx] = True
        self.update_model_matrix(geometry_idx)

    def update_bbox(self, geometry_idx=0):
        if self.geometries_loaded > 0:
            model_matrix = self.translation_matrix_list[geometry_idx] * self.rotation_matrix_list[geometry_idx] * self.scale_matrix_list[geometry_idx]
            x_a = (model_matrix.column(0).toVector3D() * self.bbox_min_list[geometry_idx].x()).toTuple()
            y_a = (model_matrix.column(1).toVector3D() * self.bbox_min_list[geometry_idx].y()).toTuple()
            z_a = (model_matrix.column(2).toVector3D() * self.bbox_min_list[geometry_idx].z()).toTuple()
            x_b = (model_matrix.column(0).toVector3D() * self.bbox_max_list[geometry_idx].x()).toTuple()
            y_b = (model_matrix.column(1).toVector3D() * self.bbox_max_list[geometry_idx].y()).toTuple()
            z_b = (model_matrix.column(2).toVector3D() * self.bbox_max_list[geometry_idx].z()).toTuple()
            min_temp = np.minimum(x_a, x_b) + np.minimum(y_a, y_b) + np.minimum(z_a, z_b)
            max_temp = np.maximum(x_a, x_b) + np.maximum(y_a, y_b) + np.maximum(z_a, z_b)
            self.transformed_bbox_min_list[geometry_idx] = QVector3D(min_temp[0], min_temp[1], min_temp[2]) + model_matrix.column(
                3).toVector3D()
            self.transformed_bbox_max_list[geometry_idx] = QVector3D(max_temp[0], max_temp[1], max_temp[2]) + model_matrix.column(
                3).toVector3D()
            self.bbox_translation_matrix_list[geometry_idx] = QMatrix4x4()
            self.bbox_translation_matrix_list[geometry_idx].translate(0.0, -self.transformed_bbox_min_list[geometry_idx].y(), 0.0)
            self.bbox_width_mm_list[geometry_idx] = (self.transformed_bbox_max_list[geometry_idx].x() - self.transformed_bbox_min_list[geometry_idx].x())
            self.bbox_depth_mm_list[geometry_idx] = (self.transformed_bbox_max_list[geometry_idx].z() - self.transformed_bbox_min_list[geometry_idx].z())
            self.bbox_height_mm_list[geometry_idx] = (self.transformed_bbox_max_list[geometry_idx].y() - self.transformed_bbox_min_list[geometry_idx].y())
            self.update_physical_size.emit(self.bbox_width_mm_list[geometry_idx], self.bbox_depth_mm_list[geometry_idx], self.bbox_height_mm_list[geometry_idx])

    def compute_global_bbox(self):
        is_defined = False
        for idx in range(self.geometries_loaded):
            # print('bbox', idx, self.transformed_bbox_min_list[idx], self.transformed_bbox_max_list[idx])
            if not is_defined:
                self.global_bbox_min = self.transformed_bbox_min_list[idx]
                self.global_bbox_max = self.transformed_bbox_max_list[idx]
                is_defined = True
            else:
                min_temp = np.minimum(self.global_bbox_min.toTuple(), self.transformed_bbox_min_list[idx].toTuple())
                max_temp = np.maximum(self.global_bbox_max.toTuple(), self.transformed_bbox_max_list[idx].toTuple())
                self.global_bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                self.global_bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
        min_temp = np.minimum(self.global_bbox_min.toTuple(), (-self.global_bbox_max).toTuple())
        max_temp = np.maximum((-self.global_bbox_min).toTuple(), self.global_bbox_max.toTuple())
        self.global_bbox_min = QVector3D(min_temp[0], self.global_bbox_min.y(), min_temp[2])
        self.global_bbox_max = QVector3D(max_temp[0], self.global_bbox_max.y(), max_temp[2])
        self.global_bbox_width_mm = self.global_bbox_max.x() - self.global_bbox_min.x()
        self.global_bbox_depth_mm = self.global_bbox_max.z() - self.global_bbox_min.z()
        self.global_bbox_height_mm = self.global_bbox_max.y() - self.global_bbox_min.y()
        # print('global', self.global_bbox_min, self.global_bbox_max)

    @Slot()
    def start_slicing(self, directory='./'):
        # TODO update this part, bbox should include all geometries
        for idx in range(self.geometries_loaded):
            self.refine_bbox(idx)
        self.compute_global_bbox()
        self.is_slicing = True
        self.current_slice = 0
        self.slicer_eye = QVector3D(0, 0, 0)
        self.slicer_look_at = self.slicer_eye + QVector3D(0.0, 1.0, 0.0)
        self.slicer_up = QVector3D(0.0, 0.0, 1.0)
        self.slicer_camera_matrix.setToIdentity()
        self.slicer_camera_matrix.lookAt(self.slicer_eye, self.slicer_look_at, self.slicer_up)
        self.slicer_camera_matrix_array = np.asarray(self.slicer_camera_matrix.copyDataTo(), np.float32)
        self.number_of_slices = np.ceil(1000 * self.global_bbox_height_mm / self.slice_thickness_microns)
        self.slice_width = np.ceil(1000 * self.global_bbox_width_mm / self.pixel_size_microns)
        self.slice_height = np.ceil(1000 * self.global_bbox_depth_mm / self.pixel_size_microns)
        self.save_directory_name = directory

    @Slot()
    def interrupt_slicing(self):
        if self.is_slicing:
            self.makeCurrent()
            self.is_slicing = False
            GL.glDisable(GL.GL_STENCIL_TEST)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_BLEND)
            self.multisample_fbo.bindDefault()
            self.glClearColor(0.65, 0.9, 1, 1)
            self.update_slice_counts.emit(self.current_slice, self.number_of_slices)

    def initializeGL(self):
        self.initializeOpenGLFunctions()
        self.glClearColor(0.65, 0.9, 1, 1)
        GL.glEnable(GL.GL_DEPTH_TEST)
        # print(self.glGetString(GL.GL_VERSION))
        quad_v0 = QVector3D(1.0, 0.0, 1.0)
        quad_v1 = QVector3D(1.0, 0.0, -1.0)
        quad_v2 = QVector3D(-1.0, 0.0, -1.0)
        quad_v3 = QVector3D(-1.0, 0.0, 1.0)
        self.quad_vertex_buffer = GL.glGenBuffers(1)
        self.quad_normal_buffer = GL.glGenBuffers(1)
        self.load_quad(quad_v0, quad_v1, quad_v2, quad_v3)
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.repaint)  # make it repaint when triggered
        self.__timer.start(0.0)
        self.previous_time = 0
        self.previous_frame_count = 0
        self.current_frame = 0
        self.frameTimer = QTime()
        self.frameTimer.start()
        self.init_shaders()

    def paintGL(self):
        if self.is_slicing:
            self.slice_next_layer()

        else:
            # if TEST_MODERN_GL:
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_STENCIL_BUFFER_BIT)

            # DRAW GEOMETRY
            GL.glUseProgram(self.program_id)
            GL.glUniform3fv(self.light_location, 1, np.asarray(self.light_direction.toTuple(), np.float32))
            GL.glUniform3fv(self.light_intensity_location, 1, np.asarray(self.light_intensity.toTuple(), np.float32))
            GL.glUniform3fv(self.ambient_location, 1, np.asarray(self.ambient_color.toTuple(), np.float32))

            GL.glUniformMatrix4fv(self.camera_matrix_location, 1, GL.GL_TRUE, self.camera_matrix_array)
            GL.glUniformMatrix4fv(self.projection_matrix_location, 1, GL.GL_TRUE, self.perspective_matrix_array)
            for geometry_idx in range(self.geometries_loaded):
                if geometry_idx == self.current_geometry_idx:
                    GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.selected_geometry_diffuse_color.toTuple(), np.float32))
                else:
                    GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.diffuse_color.toTuple(), np.float32))
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_list[geometry_idx])
                GL.glEnableVertexAttribArray(self.position_location)
                GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_buffer_list[geometry_idx])
                GL.glEnableVertexAttribArray(self.normal_location)
                GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                GL.glUniformMatrix4fv(self.model_matrix_location, 1, GL.GL_TRUE, self.model_matrix_array_list[geometry_idx])
                GL.glUniformMatrix3fv(self.normal_matrix_location, 1, GL.GL_FALSE, self.normal_matrix_array_list[geometry_idx])
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(len(self.vertices_list[geometry_idx]) / 3))
            # DRAW PLANE
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
            GL.glEnableVertexAttribArray(self.position_location)
            GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_normal_buffer)
            GL.glEnableVertexAttribArray(self.normal_location)
            GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glUniformMatrix4fv(self.camera_matrix_location, 1, GL.GL_TRUE, self.camera_matrix_array)
            GL.glUniformMatrix4fv(self.model_matrix_location, 1, GL.GL_TRUE, self.quad_model_matrix_array)
            GL.glUniformMatrix3fv(self.normal_matrix_location, 1, GL.GL_TRUE, self.quad_normal_matrix_array)
            GL.glUniformMatrix4fv(self.projection_matrix_location, 1, GL.GL_TRUE, self.perspective_matrix_array)
            GL.glUniform3fv(self.light_location, 1, np.asarray(self.light_direction.toTuple(), np.float32))
            GL.glUniform3fv(self.light_intensity_location, 1,
                            np.asarray(self.light_intensity.toTuple(), np.float32))
            GL.glUniform3fv(self.ambient_location, 1, np.asarray(self.quad_ambient_color.toTuple(), np.float32))
            GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.quad_diffuse_color.toTuple(), np.float32))
            GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, int(len(self.quad_vertices) / 3))

        current_time = self.frameTimer.elapsed()
        dt = current_time - self.previous_time
        if dt > 500:
            fps = 1000.0 * (self.current_frame - self.previous_frame_count) / dt
            self.previous_time = current_time
            self.previous_frame_count = self.current_frame
            self.update_fps.emit(fps)
            if self.is_slicing:
                self.update_slice_counts.emit(self.current_slice, self.number_of_slices)
        self.current_frame += 1

    def resizeGL(self, w, h):
        self.glViewport(0, 0, w, h)
        self.w = w
        self.h = h
        self.perspective_matrix.setToIdentity()
        self.perspective_matrix.perspective(self.fov, w / h, 0.01, 100000.0)
        self.perspective_matrix_array = np.asarray(self.perspective_matrix.copyDataTo(), np.float32)
        self.camera_matrix.setToIdentity()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)

    def slice_next_layer(self):
        # TODO fix slicer to slice multiple geometries
        if self.current_slice == 0:
            self.glClearColor(0, 0, 0, 1)
            fbo_format = QOpenGLFramebufferObjectFormat()
            fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
            fbo_format.setSamples(self.samples_per_pixel)
            self.multisample_fbo = QOpenGLFramebufferObject(self.slice_width, self.slice_height, fbo_format)
            fbo_format.setSamples(0)
            self.temp_fbo = QOpenGLFramebufferObject(self.slice_width, self.slice_height, fbo_format)
        if self.geometries_loaded > 0:
            self.multisample_fbo.bind()
            GL.glEnable(GL.GL_STENCIL_TEST)
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_MULTISAMPLE)

            self.glViewport(0, 0, self.slice_width, self.slice_height)
            GL.glUseProgram(self.slicer_program_id)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE, GL.GL_ZERO, GL.GL_ONE)

            self.glClear(GL.GL_COLOR_BUFFER_BIT)
            for sample in range(self.samples_per_pixel):
                self.glClear(GL.GL_STENCIL_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                self.ortho_matrix.setToIdentity()
                self.ortho_matrix.ortho(self.global_bbox_width_mm / 2.0, -self.global_bbox_width_mm / 2.0, -self.global_bbox_depth_mm / 2.0, self.global_bbox_depth_mm / 2.0,
                           0.0, self.slice_thickness_microns * ((sample + 1.0) / self.samples_per_pixel + self.current_slice) / 1000.0)
                self.ortho_matrix_array = np.asarray(self.ortho_matrix.copyDataTo(), np.float32)

                GL.glUniformMatrix4fv(self.slicer_camera_matrix_location, 1, GL.GL_TRUE, self.slicer_camera_matrix_array)
                GL.glUniformMatrix4fv(self.slicer_projection_matrix_location, 1, GL.GL_TRUE, self.ortho_matrix_array)
                GL.glUniform1f(self.slicer_alpha_location, 1.0/self.samples_per_pixel)
                # STENCIL SETUP
                for geometry_idx in range(self.geometries_loaded):
                    GL.glStencilMask(0xFF)
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_list[geometry_idx])
                    GL.glEnableVertexAttribArray(self.slicer_position_location)
                    GL.glVertexAttribPointer(self.slicer_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                    GL.glUniformMatrix4fv(self.slicer_model_matrix_location, 1, GL.GL_TRUE, self.model_matrix_array_list[geometry_idx])
                    GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)
                    GL.glStencilFunc(GL.GL_ALWAYS, 1, 0xFF)
                    GL.glStencilOpSeparate(GL.GL_FRONT, GL.GL_KEEP, GL.GL_KEEP, GL.GL_DECR_WRAP)
                    GL.glStencilOpSeparate(GL.GL_BACK, GL.GL_KEEP, GL.GL_KEEP, GL.GL_INCR_WRAP)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(len(self.vertices_list[geometry_idx]) / 3))

                    GL.glUniformMatrix4fv(self.slicer_model_matrix_location, 1, GL.GL_TRUE, self.model_matrix_array_list[geometry_idx])
                    GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
                    GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_KEEP)
                    GL.glStencilFunc(GL.GL_NOTEQUAL, 0, 0xFF)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(len(self.vertices_list[geometry_idx]) / 3))

            QOpenGLFramebufferObject.blitFramebuffer(self.temp_fbo, self.multisample_fbo, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
            fbo_image = QImage(self.temp_fbo.toImage()).convertToFormat(QImage.Format.Format_RGB32)

            # Render slice to screen
            aspect_ratio = self.slice_width / self.slice_height
            rect_height = self.h
            rect_width = rect_height * aspect_ratio
            if rect_width < self.w:
                buffer_rect = QRect(self.w * 0.5 - rect_width * 0.5, 0, rect_width, rect_height)
            else:
                rect_width = self.w
                rect_height = self.w / aspect_ratio
                buffer_rect = QRect(0, self.h * 0.5 - rect_height * 0.5, rect_width, rect_height)
            QOpenGLFramebufferObject.blitFramebuffer(None, buffer_rect, self.temp_fbo, QRect(0, 0, self.slice_width, self.slice_height), GL.GL_COLOR_BUFFER_BIT,
                                                     GL.GL_NEAREST)

            layer_name = self.save_directory_name + '/layer_' + str(self.current_slice) + '.png'
            fbo_image.save(layer_name)
            self.current_slice += 1
        if self.current_slice == self.number_of_slices:
            self.is_slicing = False
            GL.glDisable(GL.GL_STENCIL_TEST)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_BLEND)
            self.multisample_fbo.bindDefault()
            self.glClearColor(0.65, 0.9, 1, 1)
            self.update_slice_counts.emit(self.current_slice, self.number_of_slices)

    def mousePressEvent(self, event):
        self.mouse_last_pos = event.pos()

    def mouseMoveEvent(self, event):
        old_pos = self.__normalize_screen_coordinates__(self.mouse_last_pos)
        new_pos = self.__normalize_screen_coordinates__(event.pos())
        if event.buttons() & Qt.LeftButton:
            self.trackball_mapping(old_pos, new_pos, radius=0.8, method='bell')
            self.eye = self.camera_rotation.rotatedVector(self.eye)
            self.up = self.camera_rotation.rotatedVector(self.up)
        if event.buttons() & Qt.MiddleButton:
            zoom_factor = (new_pos.y() - old_pos.y())
            # bbox_extent = 0.5 * (self.model_matrix.map(self.bbox_min - self.bbox_max)).length()
            new_radius = np.fmax(1.0, self.camera_radius + zoom_factor)
            self.eye = new_radius / self.camera_radius * self.eye
            self.camera_radius = new_radius

        self.camera_matrix.setToIdentity()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)
        for geometry_idx in range(self.geometries_loaded):
            self.normal_matrix_list[geometry_idx] = (self.camera_matrix * self.model_matrix_list[geometry_idx]).normalMatrix()
            self.normal_matrix_array_list[geometry_idx] = np.asarray(self.normal_matrix_list[geometry_idx].data(), np.float32)
        self.light_direction = self.look_at - self.eye
        self.mouse_last_pos = event.pos()

    def trackball_mapping(self, point_a, point_c, radius=1, method='bell'):
        if method == 'bell':
            p_a = self.__bell_function__(point_a, radius)
            p_c = self.__bell_function__(point_c, radius)
        elif method == 'shoemake':
            p_a = self.__shoemake_function__(point_a, radius)
            p_c = self.__shoemake_function__(point_c, radius)
        q_a = QQuaternion(0, p_a.normalized())
        q_c = QQuaternion(0, p_c.normalized())
        new_rotation = -q_c * q_a
        self.camera_rotation = new_rotation

    @staticmethod
    def __shoemake_function__(point, radius=1):
        point_3d = QVector3D(-point.x(), point.y(), 0.0)
        sqr_sum = point_3d.x() * point_3d.x() + point_3d.y() * point_3d.y()
        if sqr_sum <= radius * radius:
            result = QVector3D(point_3d.x(), point_3d.y(), np.sqrt(radius * radius - sqr_sum))
        else:
            result = QVector3D(point_3d.x(), point_3d.y(), 0) * radius / (np.sqrt(sqr_sum))
        return result

    @staticmethod
    def __bell_function__(point, radius=1):
        point_3d = QVector3D(-point.x(), point.y(), 0.0)
        sqr_sum = point_3d.x() * point_3d.x() + point_3d.y() * point_3d.y()
        if sqr_sum <= radius * radius / 2:
            result = QVector3D(point_3d.x(), point_3d.y(), np.sqrt(radius * radius - sqr_sum))
        else:
            result = QVector3D(point_3d.x(), point_3d.y(), radius * radius / (2 * np.sqrt(sqr_sum)))
            result = result / np.sqrt(sqr_sum + result.z() * result.z())
        return result

    def __normalize_screen_coordinates__(self, pos):
        new_pos = QVector3D(0, 0, 0)
        new_pos.setX(2.0 * pos.x() / self.w - 1.0)
        if new_pos.x() < -1:
            new_pos.setX(-1)
        elif new_pos.x() > 1:
            new_pos.setX(1)
        new_pos.setY(2.0 * pos.y() / self.h - 1.0)
        if new_pos.y() < -1:
            new_pos.setY(-1)
        elif new_pos.y() > 1:
            new_pos.setY(1)
        return new_pos

    # load stl file detects if the file is a text file or binary file
    def load_stl(self, filename, swapyz=False):
        # read start of file to determine if its a binay stl file or a ascii stl file
        if not filename:
            return False
        fp = open(filename, 'rb')
        try:
            header = fp.read(80).decode('ASCII')
            stl_type = header[0:5]
        except UnicodeDecodeError:
            stl_type = 'binary'
        fp.close()
        if stl_type == 'solid':
            is_loaded = self.load_text_stl(filename, swapyz)
            if not is_loaded:
                return self.load_binary_stl(filename, swapyz)
            else:
                return is_loaded
        else:
            return self.load_binary_stl(filename, swapyz)

    # read text stl match keywords to grab the points to build the model
    def load_text_stl(self, filename, swapyz=False):
        self.append_geometries_default_parameters(self.geometries_loaded)
        self.geometry_name_list[self.geometries_loaded] = QFileInfo(filename).baseName()
        fp = open(filename, 'r')
        number_of_triangles = 0
        try:
            for line in fp.readlines():
                words = line.split()
                if len(words) > 0:
                    if words[0] == 'facet':
                        number_of_triangles += 1
                        v = [float(words[2]), float(words[3]), float(words[4])]
                        if swapyz:
                            v = [-v[0], v[2], v[1]]
                        self.normals_list[self.geometries_loaded].append(v)
                        self.normals_list[self.geometries_loaded].append(v)
                        self.normals_list[self.geometries_loaded].append(v)
                    if words[0] == 'vertex':
                        v = [float(words[1]), float(words[2]), float(words[3])]
                        if swapyz:
                            v = [-v[0], v[2], v[1]]
                        self.vertices_list[self.geometries_loaded].append(v)
                        q_v = QVector3D(v[0], v[1], v[2])
                        if self.is_bbox_defined_list[self.geometries_loaded]:
                            min_temp = np.minimum(self.bbox_min_list[self.geometries_loaded].toTuple(), v)
                            max_temp = np.maximum(self.bbox_max_list[self.geometries_loaded].toTuple(), v)
                            self.bbox_min_list[self.geometries_loaded] = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                            self.bbox_max_list[self.geometries_loaded] = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                        else:
                            self.bbox_max_list[self.geometries_loaded] = q_v
                            self.bbox_min_list[self.geometries_loaded] = q_v
                            self.is_bbox_defined_list[self.geometries_loaded] = True
        except UnicodeDecodeError:
            fp.close()
            return False
        fp.close()

        bbox_center = self.model_matrix_list[self.geometries_loaded].map(0.5 * (self.bbox_min_list[self.geometries_loaded] + self.bbox_max_list[self.geometries_loaded]))
        for idx in range(len(self.vertices_list[self.geometries_loaded])):
            self.vertices_list[self.geometries_loaded][idx] = self.vertices_list[self.geometries_loaded][idx] - np.array(bbox_center.toTuple())
        self.bbox_min_list[self.geometries_loaded] = self.bbox_min_list[self.geometries_loaded] - bbox_center
        self.bbox_max_list[self.geometries_loaded] = self.bbox_max_list[self.geometries_loaded] - bbox_center
        self.vertices_list[self.geometries_loaded] = np.array(self.vertices_list[self.geometries_loaded], dtype=np.float32).ravel()
        self.normals_list[self.geometries_loaded] = np.array(self.normals_list[self.geometries_loaded], dtype=np.float32).ravel()
        self.write_buffers(self.geometries_loaded)
        self.geometries_loaded += 1
        self.update_bbox(self.geometries_loaded-1)
        self.is_bbox_refined_list[self.geometries_loaded-1] = True
        self.update_model_matrix(self.geometries_loaded-1)
        return True

    # load binary stl file check wikipedia for the binary layout of the file
    # we use the struct library to read in and convert binary data into a format we can use
    def load_binary_stl(self, filename, swapyz=False):
        self.append_geometries_default_parameters(self.geometries_loaded)
        self.geometry_name_list[self.geometries_loaded] = QFileInfo(filename).baseName()
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
                    if swapyz:
                        normal = [-normal[0], normal[2], normal[1]]
                    self.normals_list[self.geometries_loaded].append(normal)
                    self.normals_list[self.geometries_loaded].append(normal)
                    self.normals_list[self.geometries_loaded].append(normal)
                v0_bytes = fp.read(12)
                if len(v0_bytes) == 12:
                    v0 = struct.unpack('f', v0_bytes[0:4])[0], struct.unpack('f', v0_bytes[4:8])[0], \
                             struct.unpack('f', v0_bytes[8:12])[0]
                    if swapyz:
                        v0 = [-v0[0], v0[2], v0[1]]
                    self.vertices_list[self.geometries_loaded].append(v0)
                    q_v0 = QVector3D(v0[0], v0[1], v0[2])
                    if self.is_bbox_defined_list[self.geometries_loaded]:
                        min_temp = np.minimum(self.bbox_min_list[self.geometries_loaded].toTuple(), v0)
                        max_temp = np.maximum(self.bbox_max_list[self.geometries_loaded].toTuple(), v0)
                        self.bbox_min_list[self.geometries_loaded] = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                        self.bbox_max_list[self.geometries_loaded] = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                    else:
                        self.bbox_max_list[self.geometries_loaded] = q_v0
                        self.bbox_min_list[self.geometries_loaded] = q_v0
                        self.is_bbox_defined_list[self.geometries_loaded] = True
                v1_bytes = fp.read(12)
                if len(v1_bytes) == 12:
                    v1 = struct.unpack('f', v1_bytes[0:4])[0], struct.unpack('f', v1_bytes[4:8])[0], \
                             struct.unpack('f', v1_bytes[8:12])[0]
                    if swapyz:
                        v1 = [-v1[0], v1[2], v1[1]]
                    self.vertices_list[self.geometries_loaded].append(v1)
                    q_v1 = QVector3D(v1[0], v1[1], v1[2])
                    if self.is_bbox_defined_list[self.geometries_loaded]:
                        min_temp = np.minimum(self.bbox_min_list[self.geometries_loaded].toTuple(), v1)
                        max_temp = np.maximum(self.bbox_max_list[self.geometries_loaded].toTuple(), v1)
                        self.bbox_min_list[self.geometries_loaded] = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                        self.bbox_max_list[self.geometries_loaded] = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                    else:
                        self.bbox_max_list[self.geometries_loaded] = q_v1
                        self.bbox_min_list[self.geometries_loaded] = q_v1
                        self.is_bbox_defined_list[self.geometries_loaded] = True
                v2_bytes = fp.read(12)
                if len(v2_bytes) == 12:
                    v2 = struct.unpack('f', v2_bytes[0:4])[0], struct.unpack('f', v2_bytes[4:8])[0], \
                             struct.unpack('f', v2_bytes[8:12])[0]
                    v2 = [-v2[0], v2[2], v2[1]]
                    self.vertices_list[self.geometries_loaded].append(v2)
                    q_v2 = QVector3D(v2[0], v2[1], v2[2])
                    if self.is_bbox_defined_list[self.geometries_loaded]:
                        min_temp = np.minimum(self.bbox_min_list[self.geometries_loaded].toTuple(), v2)
                        max_temp = np.maximum(self.bbox_max_list[self.geometries_loaded].toTuple(), v2)
                        self.bbox_min_list[self.geometries_loaded] = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                        self.bbox_max_list[self.geometries_loaded] = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                    else:
                        self.bbox_max_list[self.geometries_loaded] = q_v2
                        self.bbox_min_list[self.geometries_loaded] = q_v2
                        self.is_bbox_defined_list[self.geometries_loaded] = True

                attribute_bytes = fp.read(2)
                if len(attribute_bytes) == 0:
                    break
            except EOFError:
                break
        fp.close()
        bbox_center = self.model_matrix_list[self.geometries_loaded].map(0.5 * (self.bbox_min_list[self.geometries_loaded] + self.bbox_max_list[self.geometries_loaded]))
        for idx in range(len(self.vertices_list[self.geometries_loaded])):
            self.vertices_list[self.geometries_loaded][idx] = self.vertices_list[self.geometries_loaded][idx] - np.array(bbox_center.toTuple())
        self.bbox_min_list[self.geometries_loaded] = self.bbox_min_list[self.geometries_loaded] - bbox_center
        self.bbox_max_list[self.geometries_loaded] = self.bbox_max_list[self.geometries_loaded] - bbox_center
        self.vertices_list[self.geometries_loaded] = np.array(self.vertices_list[self.geometries_loaded], dtype=np.float32).ravel()
        self.normals_list[self.geometries_loaded] = np.array(self.normals_list[self.geometries_loaded], dtype=np.float32).ravel()
        self.write_buffers(self.geometries_loaded)
        self.geometries_loaded += 1
        self.update_bbox(self.geometries_loaded-1)
        self.is_bbox_refined_list[self.geometries_loaded-1] = True
        self.update_model_matrix(self.geometries_loaded-1)
        return True

    def load_obj(self, filename, swapyz=False):
        """Loads a Wavefront OBJ file. """
        self.append_geometries_default_parameters(self.geometries_loaded)
        self.geometry_name_list[self.geometries_loaded] = QFileInfo(filename).baseName()
        tmp_vertices = []
        tmp_normals = []
        tmp_texcoords = []
        tmp_faces = []
        number_of_triangles = 0
        for line in open(filename, "r"):
            if line.startswith('#'):
                continue
            values = line.split()
            if not values:
                continue
            if values[0] == 'v':
                v = [float(values[1]), float(values[2]), float(values[3])]
                if swapyz:
                    v = [-v[0], v[2], v[1]]
                tmp_vertices.append(v[0])
                tmp_vertices.append(v[1])
                tmp_vertices.append(v[2])
                q_v = QVector3D(v[0], v[1], v[2])
                if self.is_bbox_defined_list[self.geometries_loaded]:
                    min_temp = np.minimum(self.bbox_min_list[self.geometries_loaded].toTuple(), v)
                    max_temp = np.maximum(self.bbox_max_list[self.geometries_loaded].toTuple(), v)
                    self.bbox_min_list[self.geometries_loaded] = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                    self.bbox_max_list[self.geometries_loaded] = QVector3D(max_temp[0], max_temp[1], max_temp[2])
                else:
                    self.bbox_max_list[self.geometries_loaded] = q_v
                    self.bbox_min_list[self.geometries_loaded] = q_v
                    self.is_bbox_defined_list[self.geometries_loaded] = True
            elif values[0] == 'vn':
                v = [float(values[1]), float(values[2]), float(values[3])]
                if swapyz:
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

        bbox_center = self.model_matrix_list[self.geometries_loaded].map(0.5 * (self.bbox_min_list[self.geometries_loaded] + self.bbox_max_list[self.geometries_loaded]))
        for idx in range(int(len(tmp_vertices)/3)):
            tmp_vertices[3 * idx] = tmp_vertices[3 * idx] - bbox_center.x()
            tmp_vertices[3 * idx + 1] = tmp_vertices[3 * idx + 1] - bbox_center.y()
            tmp_vertices[3 * idx + 2] = tmp_vertices[3 * idx + 2] - bbox_center.z()

        self.bbox_min_list[self.geometries_loaded] = self.bbox_min_list[self.geometries_loaded] - bbox_center
        self.bbox_max_list[self.geometries_loaded] = self.bbox_max_list[self.geometries_loaded] - bbox_center

        tmp_vertices = np.array(tmp_vertices)
        tmp_normals = np.array(tmp_normals)
        for face in tmp_faces:
            vertices_idx, normals_idx, texture_idx = face
            for i in range(len(vertices_idx)):
                if normals_idx[i] > 0:
                    self.normals_list[self.geometries_loaded].append(tmp_normals[3*(normals_idx[i] - 1)])
                    self.normals_list[self.geometries_loaded].append(tmp_normals[3 * (normals_idx[i] - 1) + 1])
                    self.normals_list[self.geometries_loaded].append(tmp_normals[3 * (normals_idx[i] - 1) + 2])
                self.vertices_list[self.geometries_loaded].append(tmp_vertices[3*(vertices_idx[i] - 1)])
                self.vertices_list[self.geometries_loaded].append(tmp_vertices[3 * (vertices_idx[i] - 1) + 1])
                self.vertices_list[self.geometries_loaded].append(tmp_vertices[3 * (vertices_idx[i] - 1) + 2])
        self.vertices_list[self.geometries_loaded] = np.array(self.vertices_list[self.geometries_loaded], dtype=np.float32)
        self.normals_list[self.geometries_loaded] = np.array(self.normals_list[self.geometries_loaded], dtype=np.float32)
        self.write_buffers(self.geometries_loaded)
        self.geometries_loaded += 1
        self.update_bbox(self.geometries_loaded-1)
        self.is_bbox_refined_list[self.geometries_loaded-1] = True
        self.update_model_matrix(self.geometries_loaded-1)
        return True

    def write_buffers(self, geometry_idx=0):
        self.vertex_buffer_list.append(GL.glGenBuffers(1))
        self.normal_buffer_list.append(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_list[geometry_idx])
        a = self.vertices_list[geometry_idx]
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vertices_list[geometry_idx].nbytes, self.vertices_list[geometry_idx], GL.GL_STATIC_DRAW)
        GL.glEnableVertexAttribArray(self.position_location)
        GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        #
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_buffer_list[geometry_idx])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.normals_list[geometry_idx].nbytes, self.normals_list[geometry_idx], GL.GL_STATIC_DRAW)
        GL.glEnableVertexAttribArray(self.normal_location)
        GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

    def load_quad(self, v0, v1, v2, v3):
        self.quad_vertices = np.asarray(np.concatenate((v0.toTuple(), v1.toTuple(), v2.toTuple(), v3.toTuple())), np.float32)
        self.quad_normals = np.array((0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0), np.float32)
        self.update_bbox()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_vertices.nbytes, self.quad_vertices, GL.GL_STATIC_DRAW)
        #
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_normal_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_normals.nbytes, self.quad_normals, GL.GL_STATIC_DRAW)

    def init_shaders(self):
        self.program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, self.vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, self.fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.program_id, vs_id)
        GL.glAttachShader(self.program_id, frag_id)
        GL.glLinkProgram(self.program_id)
        self.position_location = GL.glGetAttribLocation(self.program_id, 'vin_position')
        self.normal_location = GL.glGetAttribLocation(self.program_id, 'vin_normal')
        self.camera_matrix_location = GL.glGetUniformLocation(self.program_id, 'camera_matrix')
        self.model_matrix_location = GL.glGetUniformLocation(self.program_id, 'model_matrix')
        self.projection_matrix_location = GL.glGetUniformLocation(self.program_id, 'projection_matrix')
        self.normal_matrix_location = GL.glGetUniformLocation(self.program_id, 'normal_matrix')
        self.light_location = GL.glGetUniformLocation(self.program_id, 'light_direction')
        self.light_intensity_location = GL.glGetUniformLocation(self.program_id, 'light_intensity')
        self.ambient_location = GL.glGetUniformLocation(self.program_id, 'ambient_color')
        self.diffuse_location = GL.glGetUniformLocation(self.program_id, 'diffuse_color')

        self.slicer_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, self.slicer_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, self.slicer_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.slicer_program_id, vs_id)
        GL.glAttachShader(self.slicer_program_id, frag_id)
        GL.glLinkProgram(self.slicer_program_id)
        self.slicer_position_location = GL.glGetAttribLocation(self.slicer_program_id, 'vin_position')
        self.slicer_camera_matrix_location = GL.glGetUniformLocation(self.slicer_program_id, 'camera_matrix')
        self.slicer_model_matrix_location = GL.glGetUniformLocation(self.slicer_program_id, 'model_matrix')
        self.slicer_projection_matrix_location = GL.glGetUniformLocation(self.slicer_program_id, 'projection_matrix')
        self.slicer_alpha_location = GL.glGetUniformLocation(self.slicer_program_id, 'alpha')

    def remove_geometry(self):
        if self.geometries_loaded > 0:
            self.geometries_loaded -= 1
            del self.vertices_list[self.current_geometry_idx]
            del self.normals_list[self.current_geometry_idx]
            del self.translation_matrix_list[self.current_geometry_idx]
            del self.bbox_translation_matrix_list[self.current_geometry_idx]
            del self.rotation_matrix_list[self.current_geometry_idx]
            del self.scale_matrix_list[self.current_geometry_idx]
            del self.model_matrix_list[self.current_geometry_idx]
            del self.normal_matrix_list[self.current_geometry_idx]
            del self.model_matrix_array_list[self.current_geometry_idx]
            del self.normal_matrix_array_list[self.current_geometry_idx]
            del self.x_rot_list[self.current_geometry_idx]
            del self.y_rot_list[self.current_geometry_idx]
            del self.z_rot_list[self.current_geometry_idx]
            del self.scale_x_list[self.current_geometry_idx]
            del self.scale_y_list[self.current_geometry_idx]
            del self.scale_z_list[self.current_geometry_idx]
            del self.x_pos_list[self.current_geometry_idx]
            del self.z_pos_list[self.current_geometry_idx]
            del self.unit_of_measurement_list[self.current_geometry_idx]
            del self.uniform_scaling_list[self.current_geometry_idx]
            del self.geometry_name_list[self.current_geometry_idx]
            del self.bbox_min_list[self.current_geometry_idx]
            del self.bbox_max_list[self.current_geometry_idx]
            del self.transformed_bbox_min_list[self.current_geometry_idx]
            del self.transformed_bbox_max_list[self.current_geometry_idx]
            del self.bbox_width_mm_list[self.current_geometry_idx]
            del self.bbox_depth_mm_list[self.current_geometry_idx]
            del self.bbox_height_mm_list[self.current_geometry_idx]
            del self.bbox_width_microns_list[self.current_geometry_idx]
            del self.bbox_depth_microns_list[self.current_geometry_idx]
            del self.bbox_height_microns_list[self.current_geometry_idx]
            del self.is_bbox_defined_list[self.current_geometry_idx]
            del self.is_bbox_refined_list[self.current_geometry_idx]
            GL.glDeleteBuffers(1, [self.vertex_buffer_list[self.current_geometry_idx]])
            GL.glDeleteBuffers(1, [self.normal_buffer_list[self.current_geometry_idx]])
            del self.vertex_buffer_list[self.current_geometry_idx]
            del self.normal_buffer_list[self.current_geometry_idx]
            self.current_geometry_idx = 0
