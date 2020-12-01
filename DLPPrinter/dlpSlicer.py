import numpy as np
from PySide2.QtWidgets import QOpenGLWidget
from PySide2.QtCore import Signal, Slot, QTimer, QTime, QFileInfo, QRect, Qt
from PySide2.QtGui import QVector3D, QOpenGLFunctions,\
    QQuaternion, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QImage, QMatrix4x4
from OpenGL import GL
import struct
from helpers import my_shaders as ms
from helpers import geometry_loader

class DLPSlicer(QOpenGLWidget, QOpenGLFunctions):

    update_physical_size = Signal(float, float, float)
    update_fps = Signal(float)
    update_slice_counts = Signal(float, float)

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
        self.slicer_color_location = None
        self.slicer_camera_matrix_location = None
        self.slicer_model_matrix_location = None
        self.slicer_projection_matrix_location = None
        self.slicer_alpha_location = None
        
        # camera variables
        self.w = 1
        self.h = 1
        self.camera_radius = 20
        self.camera_rotation = QQuaternion()
        self.eye = QVector3D(0.0, 1.50, 1.0)
        self.eye = self.camera_radius * self.camera_rotation.rotatedVector(self.eye)
        self.look_at = QVector3D(0.0, 1.0, 0.0)
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

        self.__update_model_matrix__()
        self.update_quad_scale()

    def __append_geometries_default_parameters__(self, geometry_idx=0):
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
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

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
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

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
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

    @Slot(float)
    def set_x_scale(self, value):
        if self.geometries_loaded > 0:
            self.scale_x_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

    @Slot(float)
    def set_y_scale(self, value):
        if self.geometries_loaded > 0:
            self.scale_y_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

    @Slot(float)
    def set_z_scale(self, value):
        if self.geometries_loaded > 0:
            self.scale_z_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

    @Slot(float)
    def set_x_pos(self, value):
        if self.geometries_loaded > 0:
            self.x_pos_list[self.current_geometry_idx] = value
            new_translation_matrix = QMatrix4x4()
            new_translation_matrix.translate(self.x_pos_list[self.current_geometry_idx], 0, self.z_pos_list[self.current_geometry_idx])
            self.translation_matrix_list[self.current_geometry_idx] = new_translation_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

    @Slot(float)
    def set_z_pos(self, value):
        if self.geometries_loaded > 0:
            self.z_pos_list[self.current_geometry_idx] = value
            new_translation_matrix = QMatrix4x4()
            new_translation_matrix.translate(self.x_pos_list[self.current_geometry_idx], 0, self.z_pos_list[self.current_geometry_idx])
            self.translation_matrix_list[self.current_geometry_idx] = new_translation_matrix
            # self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

    @Slot(float)
    def set_unit_of_measurement(self, value):
        if self.geometries_loaded > 0:
            self.unit_of_measurement_list[self.current_geometry_idx] = value
            new_scale_matrix = QMatrix4x4()
            new_scale_matrix.scale(self.scale_x_list[self.current_geometry_idx], self.scale_y_list[self.current_geometry_idx], self.scale_z_list[self.current_geometry_idx])
            new_scale_matrix.scale(self.unit_of_measurement_list[self.current_geometry_idx])
            self.scale_matrix_list[self.current_geometry_idx] = new_scale_matrix
            self.is_bbox_refined_list[self.current_geometry_idx] = False
            self.__update_bbox__(self.current_geometry_idx)
            self.__update_model_matrix__(self.current_geometry_idx)

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

    def __update_model_matrix__(self, geometry_idx=0):
        if self.geometries_loaded > 0:
            self.model_matrix_list[geometry_idx] = self.bbox_translation_matrix_list[geometry_idx] \
                                                                * self.translation_matrix_list[geometry_idx] \
                                                                * self.rotation_matrix_list[geometry_idx] \
                                                                * self.scale_matrix_list[geometry_idx]
            self.model_matrix_array_list[geometry_idx] = np.asarray(self.model_matrix_list[geometry_idx].copyDataTo(), np.float32)
            self.normal_matrix_list[geometry_idx] = (self.camera_matrix * self.model_matrix_list[geometry_idx]).normalMatrix()
            self.normal_matrix_array_list[geometry_idx] = np.asarray(self.normal_matrix_list[geometry_idx].data(), np.float32)

    def __refine_bbox__(self, geometry_idx=0):
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
        self.__update_model_matrix__(geometry_idx)

    def __update_bbox__(self, geometry_idx=0):
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

    def __compute_global_bbox__(self):
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
    def prepare_for_slicing(self, directory='./'):
        for idx in range(self.geometries_loaded):
            self.__refine_bbox__(idx)
        self.__compute_global_bbox__()
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
        self.__initialize_slicer_opengl__()

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
        self.load_quad()
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
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_STENCIL_BUFFER_BIT)
            GL.glUseProgram(self.program_id)
            GL.glUniform3fv(self.light_location, 1, np.asarray(self.light_direction.toTuple(), np.float32))
            GL.glUniform3fv(self.light_intensity_location, 1, np.asarray(self.light_intensity.toTuple(), np.float32))

            GL.glUniformMatrix4fv(self.camera_matrix_location, 1, GL.GL_TRUE, self.camera_matrix_array)
            GL.glUniformMatrix4fv(self.projection_matrix_location, 1, GL.GL_TRUE, self.perspective_matrix_array)
            # DRAW PLANE
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
            GL.glEnableVertexAttribArray(self.position_location)
            GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_normal_buffer)
            GL.glEnableVertexAttribArray(self.normal_location)
            GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glUniformMatrix4fv(self.model_matrix_location, 1, GL.GL_TRUE, self.quad_model_matrix_array)
            GL.glUniformMatrix3fv(self.normal_matrix_location, 1, GL.GL_TRUE, self.quad_normal_matrix_array)
            GL.glUniform3fv(self.ambient_location, 1, np.asarray(self.quad_ambient_color.toTuple(), np.float32))
            GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.quad_diffuse_color.toTuple(), np.float32))
            GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, int(len(self.quad_vertices) / 3))
            # DRAW GEOMETRY
            GL.glUniform3fv(self.ambient_location, 1, np.asarray(self.ambient_color.toTuple(), np.float32))
            for geometry_idx in range(self.geometries_loaded):
                if geometry_idx == self.current_geometry_idx:
                    GL.glUniform3fv(self.diffuse_location, 1,
                                    np.asarray(self.selected_geometry_diffuse_color.toTuple(), np.float32))
                else:
                    GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.diffuse_color.toTuple(), np.float32))
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_list[geometry_idx])
                GL.glEnableVertexAttribArray(self.position_location)
                GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_buffer_list[geometry_idx])
                GL.glEnableVertexAttribArray(self.normal_location)
                GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                GL.glUniformMatrix4fv(self.model_matrix_location, 1, GL.GL_TRUE,
                                      self.model_matrix_array_list[geometry_idx])
                GL.glUniformMatrix3fv(self.normal_matrix_location, 1, GL.GL_FALSE,
                                      self.normal_matrix_array_list[geometry_idx])
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(len(self.vertices_list[geometry_idx]) / 3))

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
        if self.geometries_loaded > 0:
            self.glViewport(0, 0, self.slice_width, self.slice_height)
            self.multisample_fbo.bind()
            self.glClear(GL.GL_COLOR_BUFFER_BIT)
            GL.glEnable(GL.GL_STENCIL_TEST)
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_MULTISAMPLE)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE, GL.GL_ZERO, GL.GL_ONE)
            GL.glUseProgram(self.slicer_program_id)
            self.__set_slicer_uniform_variables__()
            for sample in range(self.samples_per_pixel):
                self.glClear(GL.GL_STENCIL_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                self.ortho_matrix.setToIdentity()
                self.ortho_matrix.ortho(self.global_bbox_width_mm / 2.0, -self.global_bbox_width_mm / 2.0, -self.global_bbox_depth_mm / 2.0, self.global_bbox_depth_mm / 2.0,
                           0.0, self.slice_thickness_microns * ((sample + 1.0) / self.samples_per_pixel + self.current_slice) / 1000.0)
                self.ortho_matrix_array = np.asarray(self.ortho_matrix.copyDataTo(), np.float32)
                GL.glUniformMatrix4fv(self.slicer_projection_matrix_location, 1, GL.GL_TRUE, self.ortho_matrix_array)
                for geometry_idx in range(self.geometries_loaded):
                    self.__bind_geometry_buffer__(geometry_idx)
                    self.__draw_geometry_slice__(geometry_idx)
            QOpenGLFramebufferObject.blitFramebuffer(self.temp_fbo, self.multisample_fbo, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
            self.__render_slice_to_screen__(self.temp_fbo)
            self.__save_slice_to_disk__(self.temp_fbo)
            self.current_slice += 1
        if self.current_slice == self.number_of_slices:
            self.__reset_default_opengl_buffer__()
            self.update_slice_counts.emit(self.current_slice, self.number_of_slices)

    def __initialize_slicer_opengl__(self):
        self.makeCurrent()
        self.glClearColor(0, 0, 0, 1)
        fbo_format = QOpenGLFramebufferObjectFormat()
        fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
        fbo_format.setSamples(self.samples_per_pixel)
        if self.samples_per_pixel == 1:
            fbo_format.setSamples(0)
        self.multisample_fbo = QOpenGLFramebufferObject(self.slice_width, self.slice_height, fbo_format)
        fbo_format.setSamples(0)
        self.temp_fbo = QOpenGLFramebufferObject(self.slice_width, self.slice_height, fbo_format)

    def __set_slicer_uniform_variables__(self):
        GL.glUniformMatrix4fv(self.slicer_camera_matrix_location, 1, GL.GL_TRUE, self.slicer_camera_matrix_array)
        GL.glUniform3fv(self.slicer_color_location, 1, np.array([1.0, 1.0, 1.0], np.float32))
        GL.glUniform1f(self.slicer_alpha_location, 1.0 / self.samples_per_pixel)

    def __bind_geometry_buffer__(self, geometry_idx):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_list[geometry_idx])
        GL.glEnableVertexAttribArray(self.slicer_position_location)
        GL.glVertexAttribPointer(self.slicer_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glUniformMatrix4fv(self.slicer_model_matrix_location, 1, GL.GL_TRUE,
                              self.model_matrix_array_list[geometry_idx])

    def __draw_geometry_slice__(self, geometry_idx):
        # STENCIL SETUP
        GL.glDrawBuffers(1, [GL.GL_COLOR_ATTACHMENT0])
        GL.glStencilMask(0xFF)
        GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)
        GL.glStencilFunc(GL.GL_ALWAYS, 1, 0xFF)
        GL.glStencilOpSeparate(GL.GL_FRONT, GL.GL_KEEP, GL.GL_KEEP, GL.GL_DECR_WRAP)
        GL.glStencilOpSeparate(GL.GL_BACK, GL.GL_KEEP, GL.GL_KEEP, GL.GL_INCR_WRAP)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(len(self.vertices_list[geometry_idx]) / 3))
        GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
        GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_KEEP)
        GL.glStencilFunc(GL.GL_NOTEQUAL, 0, 0xFF)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, int(len(self.vertices_list[geometry_idx]) / 3))

    def __render_slice_to_screen__(self, fbo, colorAttachmentIdx=0):
        aspect_ratio = self.slice_width / self.slice_height
        rect_height = self.h
        rect_width = rect_height * aspect_ratio
        if rect_width < self.w:
            buffer_rect = QRect(self.w * 0.5 - rect_width * 0.5, 0, rect_width, rect_height)
        else:
            rect_width = self.w
            rect_height = self.w / aspect_ratio
            buffer_rect = QRect(0, self.h * 0.5 - rect_height * 0.5, rect_width, rect_height)
        QOpenGLFramebufferObject.blitFramebuffer(None, buffer_rect, fbo,
                                                 QRect(0, 0, self.slice_width, self.slice_height),
                                                 GL.GL_COLOR_BUFFER_BIT,
                                                 GL.GL_NEAREST, colorAttachmentIdx, 0)

    def __save_slice_to_disk__(self, fbo, colorAttachmentIdx=0, extra_name=''):
        fbo_image = QImage(fbo.toImage(True, colorAttachmentIdx)).convertToFormat(QImage.Format_RGB32)
        layer_name = self.save_directory_name + '/layer_' + str(self.current_slice) + extra_name + '.png'
        fbo_image.save(layer_name)

    def __reset_default_opengl_buffer__(self):
        self.is_slicing = False
        GL.glDisable(GL.GL_STENCIL_TEST)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_BLEND)
        self.multisample_fbo.bindDefault()
        self.glClearColor(0.65, 0.9, 1, 1)

    def load_geometry(self, filename, swapyz=False):
        is_loaded, vertices_list, normals_list, bbox_min, bbox_max = geometry_loader.load_geometry(filename, swapyz)
        if is_loaded:
            geometry_idx = self.geometries_loaded
            self.geometries_loaded += 1
            self.__append_geometries_default_parameters__(geometry_idx)
            self.geometry_name_list[geometry_idx] = QFileInfo(filename).baseName()
            self.bbox_min_list[geometry_idx] = bbox_min
            self.bbox_max_list[geometry_idx] = bbox_max
            self.vertices_list[geometry_idx] = np.array(vertices_list, dtype=np.float32).ravel()
            self.normals_list[geometry_idx] = np.array(normals_list, dtype=np.float32).ravel()
            self.is_bbox_defined_list[geometry_idx] = True
            self.write_buffers(geometry_idx)
            self.__update_bbox__(geometry_idx)
            self.is_bbox_refined_list[geometry_idx] = True
            self.__update_model_matrix__(geometry_idx)
            return True
        return False

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

    def load_quad(self):
        self.quad_vertex_buffer = GL.glGenBuffers(1)
        self.quad_normal_buffer = GL.glGenBuffers(1)
        v0 = QVector3D(1.0, 0.0, 1.0)
        v1 = QVector3D(1.0, 0.0, -1.0)
        v2 = QVector3D(-1.0, 0.0, -1.0)
        v3 = QVector3D(-1.0, 0.0, 1.0)
        n0 = QVector3D(0.0, 1.0, 0.0)
        n1 = QVector3D(0.0, 1.0, 0.0)
        n2 = QVector3D(0.0, 1.0, 0.0)
        n3 = QVector3D(0.0, 1.0, 0.0)
        self.quad_vertices = np.asarray(np.concatenate((v0.toTuple(), v1.toTuple(), v2.toTuple(), v3.toTuple())),
                                        np.float32)
        self.quad_normals = np.asarray(np.concatenate((n0.toTuple(), n1.toTuple(), n2.toTuple(), n3.toTuple())),
                                        np.float32)
        self.__update_bbox__()
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_vertices.nbytes, self.quad_vertices, GL.GL_STATIC_DRAW)
        #
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_normal_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_normals.nbytes, self.quad_normals, GL.GL_STATIC_DRAW)

    def init_shaders(self):
        self.program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.fragment_shader)
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
        GL.glShaderSource(vs_id, ms.slicer_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.slicer_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.slicer_program_id, vs_id)
        GL.glAttachShader(self.slicer_program_id, frag_id)
        GL.glLinkProgram(self.slicer_program_id)
        self.slicer_position_location = GL.glGetAttribLocation(self.slicer_program_id, 'vin_position')
        self.slicer_color_location = GL.glGetUniformLocation(self.slicer_program_id, 'vin_color')
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
            zoom_factor = (new_pos.y() - old_pos.y()) * 50
            new_radius = np.fmax(1.0, self.camera_radius + zoom_factor)
            zoom_direction = self.eye - self.look_at
            zoom_direction.normalize()
            self.eye = self.look_at + zoom_direction * new_radius
            self.camera_radius = new_radius
        if event.buttons() & Qt.RightButton:
            x_translation = -(new_pos.x() - old_pos.x()) * 50
            y_translation = (new_pos.y() - old_pos.y()) * 50
            right = QVector3D.crossProduct(self.look_at - self.eye, self.up)
            right.normalize()
            self.eye = self.eye + self.up * y_translation + right * x_translation
            self.look_at = self.look_at + self.up * y_translation + right * x_translation
        self.camera_matrix.setToIdentity()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)
        for geometry_idx in range(self.geometries_loaded):
            self.normal_matrix_list[geometry_idx] = (
                        self.camera_matrix * self.model_matrix_list[geometry_idx]).normalMatrix()
            self.normal_matrix_array_list[geometry_idx] = np.asarray(self.normal_matrix_list[geometry_idx].data(),
                                                                     np.float32)
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