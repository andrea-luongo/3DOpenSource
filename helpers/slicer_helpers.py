import numpy as np
from PySide2.QtCore import Signal, Slot, QJsonDocument


def sort_segments_list(segments):
    sorted_loops = []
    current_idx = 0
    to_visit_idxs = [idx for idx in range(1, len(segments))]
    visited_idxs = [current_idx]
    current_loop = [segments[current_idx]]
    current_segment = segments[current_idx]
    while True:
        found_new_segment = False
        for idx in to_visit_idxs:
            comparison_0 = np.abs(segments[idx][0] - current_segment[1]) < 0.00001
            comparison_1 = np.abs(segments[idx][1] - current_segment[1]) < 0.00001
            if comparison_0.all():
                current_loop.append(segments[idx])
                visited_idxs.append(idx)
                to_visit_idxs.remove(idx)
                found_new_segment = True
                current_segment = segments[idx]
                break
            if comparison_1.all():
                current_loop.append([segments[idx][1], segments[idx][0]])
                visited_idxs.append(idx)
                to_visit_idxs.remove(idx)
                found_new_segment = True
                current_segment = [segments[idx][1], segments[idx][0]]
                break
        if not found_new_segment:
            sorted_loops.append(current_loop)
            if len(to_visit_idxs) == 0:
                break
            else:
                current_loop = []
                current_idx = to_visit_idxs[0]
                current_loop.append(segments[current_idx])
                to_visit_idxs.remove(current_idx)
                current_segment = segments[current_idx]
    result = np.vstack(np.array(sorted_loops, dtype=object)).ravel()
    return result


def merge_sort_segments_list(segments):
    sorted_segments = merge_sort_segments_list2(segments)
    return np.vstack(np.array(sorted_segments, dtype=object)).ravel()


def merge_sort_segments_list2(segments):
    sorted_loops = []
    if len(segments) == 1:
        sorted_loops.append(segments)
        return sorted_loops
    else:
        half_idx = int(len(segments) * 0.5)
        left_segments = segments[0:half_idx]
        right_segments = segments[half_idx:len(segments)]
        left_loop = merge_sort_segments_list2(left_segments)
        right_loop = merge_sort_segments_list2(right_segments)
        merged_loops_idxs = []
        to_delete_idxs = []
        for left_idx in range(len(left_loop)):
            right_loop = [x for x_idx, x in enumerate(right_loop) if not (x_idx in to_delete_idxs)]
            to_delete_idxs = []
            for right_idx, right_list in enumerate(right_loop):
                is_merged, merged_list = __merge_segments_lists(left_loop[left_idx], right_list)
                if is_merged:
                    left_loop[left_idx] = merged_list
                    to_delete_idxs.append(right_idx)
                    merged_loops_idxs.append(left_idx)

        right_loop = [x for x_idx, x in enumerate(right_loop) if not (x_idx in to_delete_idxs)]
        to_delete_idxs = []
        for merged_idx in merged_loops_idxs:
            for list_idx, left_list in enumerate(left_loop):
                if list_idx in to_delete_idxs or merged_idx in to_delete_idxs:
                    continue
                if list_idx is not merged_idx:
                    is_merged, merged_list = __merge_segments_lists(left_loop[merged_idx], left_list)
                    if is_merged:
                        left_loop[merged_idx] = merged_list
                        to_delete_idxs.append(list_idx)

        left_loop = [x for x_idx, x in enumerate(left_loop) if not (x_idx in to_delete_idxs)]
        result = left_loop + right_loop
        return result


def __merge_segments_lists(segments_list_0, segments_list_1):
    merged_list = []
    length_0 = len(segments_list_0)
    length_1 = len(segments_list_1)
    start_0 = segments_list_0[0]
    end_0 = segments_list_0[length_0-1]
    start_1 = segments_list_1[0]
    end_1 = segments_list_1[length_1-1]
    # Case 1:
    if __compare_segments(end_0, start_1):
        merged_list = segments_list_0 + segments_list_1
        return True, merged_list
    # Case 2:
    if __compare_segments(end_1, start_0):
        merged_list = segments_list_1 + segments_list_0
        return True, merged_list
    # Case 3:
    if __compare_segments(end_0, [end_1[1], end_1[0]]):
        segments_list_1 = list(reversed(segments_list_1))
        segments_list_1 = [[s[1], s[0]] for s in segments_list_1]
        merged_list = segments_list_0 + segments_list_1
        return True, merged_list
    # Case 4:
    if __compare_segments([start_1[1], start_1[0]], start_0):
        segments_list_1 = list(reversed(segments_list_1))
        segments_list_1 = [[s[1], s[0]] for s in segments_list_1]
        merged_list = segments_list_1 + segments_list_0
        return True, merged_list
    return False, merged_list


def __compare_segments(s0, s1, threshold=0.00001):
    comparison = np.abs(s0[1] - s1[0]) < threshold
    are_connected = False
    if comparison.all():
        are_connected = True
        return are_connected
    return are_connected


# debugging function to inspect content of binary image coming from a Qt FBO
def fbo_image_inspector(binary_image):
    width = binary_image.width()
    height = binary_image.height()
    ptr = binary_image.constBits()
    tmp = np.frombuffer(ptr, dtype=np.ushort)
    tmp = tmp.reshape(height, width, 4)


# 2d distance field computation based on lower envelopes of parabolas. The input binary image contains white pixels
# inside the geometry, and black pixels outside the geometry. To compute the distance of the outside pixels from the
# geometry we start by assigning a value of 0 to the white pixels, and a value of INF to the black pixels. To compute
# the distance of the geometry pixels from the boundary of the geometry we assign the value of INF to the white pixels,
# and 0 to the black pixels.
def compute_2D_distance_field(binary_image):
    width = binary_image.width()
    height = binary_image.height()
    ptr = binary_image.constBits()
    tmp = np.array(ptr, dtype=np.int)
    tmp = tmp.reshape(height, width, 4) / 255
    geometry_pixels = np.squeeze(tmp[:, :, 0:1])
    background_pixels = np.where(geometry_pixels < 1, 1, 0)
    inside_distance_field = geometry_pixels * np.iinfo(np.int).max
    outside_distance_field = background_pixels * np.iinfo(np.int).max
    # rows pass
    for row_idx in range(height):
        inside_grid = inside_distance_field[row_idx, :]
        outside_grid = outside_distance_field[row_idx, :]
        inside_parabola_locations, inside_parabola_boundaries = __compute_1d_lower_envelope__(inside_grid)
        outside_parabola_locations, outside_parabola_boundaries = __compute_1d_lower_envelope__(outside_grid)
        inside_1d_distance_transform = __compute_1d_distance_transform__(inside_grid, inside_parabola_locations, inside_parabola_boundaries)
        outside_1d_distance_transform = __compute_1d_distance_transform__(outside_grid, outside_parabola_locations, outside_parabola_boundaries)
        inside_distance_field[row_idx, :] = inside_1d_distance_transform
        outside_distance_field[row_idx, :] = outside_1d_distance_transform
    # column pass
    for col_idx in range(width):
        inside_grid = inside_distance_field[:, col_idx]
        outside_grid = outside_distance_field[:, col_idx]
        inside_parabola_locations, inside_parabola_boundaries = __compute_1d_lower_envelope__(inside_grid)
        outside_parabola_locations, outside_parabola_boundaries = __compute_1d_lower_envelope__(outside_grid)
        inside_1d_distance_transform = __compute_1d_distance_transform__(inside_grid, inside_parabola_locations, inside_parabola_boundaries)
        outside_1d_distance_transform = __compute_1d_distance_transform__(outside_grid, outside_parabola_locations, outside_parabola_boundaries)
        inside_distance_field[:, col_idx] = inside_1d_distance_transform
        outside_distance_field[:, col_idx] = outside_1d_distance_transform
    return inside_distance_field, outside_distance_field


def __compute_parabola_intersections__(grid, idx_0, idx_1):
    a = grid[idx_0] + idx_0 * idx_0
    b = grid[idx_1] + idx_1 * idx_1
    result = (a - b) / (idx_0 - idx_1) * 0.5
    return result


def __compute_1d_lower_envelope__(grid):
    rightmost_parabola_idx = 0
    parabola_locations = [0]
    parabola_boundaries = [np.iinfo(np.int).min,  np.iinfo(np.int).max]
    for idx in range(1, len(grid)):
        # print('q', idx)
        parabola_found = False
        while not parabola_found:
            s = __compute_parabola_intersections__(grid, idx, parabola_locations[rightmost_parabola_idx])
            if s > parabola_boundaries[rightmost_parabola_idx]:
                rightmost_parabola_idx += 1
                parabola_locations.append(idx)
                parabola_boundaries[rightmost_parabola_idx] = s
                parabola_boundaries.append(np.iinfo(np.uint).max)
                parabola_found = True
            else:
                rightmost_parabola_idx -= 1
    return parabola_locations, parabola_boundaries


def __compute_1d_distance_transform__(grid, parabola_locations, parabola_boundaries):
    k = 0
    distance_transform = np.zeros(len(grid))
    for idx in range(len(grid)):
        while parabola_boundaries[k + 1] < idx:
            k = k + 1
        distance_transform[idx] = (idx - parabola_locations[k])**2 + grid[parabola_locations[k]]
    return distance_transform


def read_marching_squares_table(origin, idx):
    if idx == 0 or idx == 15:
        return
    result = origin + marching_squares_table[idx]
    return result.tolist()


marching_squares_table = [
    None,
    [np.array([0, 0, -0.5]), np.array([-0.5, 0, 0])],
    [np.array([0.5, 0, 0]), np.array([0, 0, -0.5])],
    [np.array([0.5, 0, 0]), np.array([-0.5, 0, 0])],
    [np.array([0, 0, 0.5]), np.array([0.5, 0, 0])],
    [np.array([0.5, 0, 0]), np.array([0, 0, -0.5]), np.array([-0.5, 0, 0]), np.array([0, 0, 0.5])],
    [np.array([0, 0, 0.5]), np.array([0, 0, -0.5])],
    [np.array([-0.5, 0, 0]), np.array([0.5, 0, 0])],
    [np.array([-0.5, 0, 0]), np.array([0.5, 0, 0])],
    [np.array([0, 0, 0.5]), np.array([0, 0, -0.5])],
    [np.array([0, 0, 0.5]), np.array([0.5, 0, 0]), np.array([0, 0, -0.5]), np.array([-0.5, 0, 0])],
    [np.array([0, 0, 0.5]), np.array([0.5, 0, 0])],
    [np.array([-0.5, 0, 0]), np.array([0.5, 0, 0])],
    [np.array([0.5, 0, 0]), np.array([0, 0, -0.5])],
    [np.array([0, 0, -0.5]), np.array([-0.5, 0, 0])],
    None
]


class MetalSlicingParameters():

    def __init__(self, infill_laser_power=0, infill_scan_speed=0, infill_duty_cycle=0, infill_frequency=0,
                 infill_density=0, infill_overlap=0, infill_rotation_angle=0, contour_laser_power=0,
                 contour_scan_speed=0, contour_duty_cycle=0, contour_frequency=0):
        self.infill_laser_power = infill_laser_power
        self.infill_scan_speed = infill_scan_speed
        self.infill_duty_cycle = infill_duty_cycle
        self.infill_frequency = infill_frequency
        self.infill_density = infill_density
        self.infill_overlap = infill_overlap
        self.infill_rotation_angle = infill_rotation_angle
        self.infill_strategy_idx = 0
        # self.infill_vertices = []
        self.contour_laser_power = contour_laser_power
        self.contour_scan_speed = contour_scan_speed
        self.contour_duty_cycle = contour_duty_cycle
        self.contour_frequency = contour_frequency
        self.contour_strategy_idx = 0
        # self.contour_vertices = []

    @Slot(int)
    def set_infill_strategy_idx(self, value):
        self.infill_strategy_idx = value

    def get_infill_strategy_idx(self):
        return self.infill_strategy_idx

    @Slot(int)
    def set_contour_strategy_idx(self, value):
        self.contour_strategy_idx = value

    def get_contour_strategy_idx(self):
        return self.contour_strategy_idx

    @Slot(int)
    def set_infill_density(self, value):
        self.infill_density = value

    def get_infill_density(self):
        return self.infill_density

    @Slot(int)
    def set_infill_overlap(self, value):
        self.infill_overlap = value

    def get_infill_overlap(self):
        return self.infill_overlap

    @Slot(int)
    def set_infill_rotation_angle(self, value):
        self.infill_rotation_angle = value

    def get_infill_rotation_angle(self):
        return self.infill_rotation_angle

    @Slot(float)
    def set_infill_laser_power(self, value):
        self.infill_laser_power = value

    def get_infill_laser_power(self):
        return self.infill_laser_power

    @Slot(float)
    def set_infill_scan_speed(self, value):
        self.infill_scan_speed = value

    def get_infill_scan_speed(self):
        return self.infill_scan_speed

    @Slot(float)
    def set_infill_duty_cycle(self, value):
        self.infill_duty_cycle = value

    def get_infill_duty_cycle(self):
        return self.infill_duty_cycle

    @Slot(float)
    def set_infill_frequency(self, value):
        self.infill_frequency = value

    def get_infill_frequency(self):
        return self.infill_frequency

    @Slot(float)
    def set_contour_laser_power(self, value):
        self.contour_laser_power = value

    def get_contour_laser_power(self):
        return self.contour_laser_power

    @Slot(float)
    def set_contour_scan_speed(self, value):
        self.contour_scan_speed = value

    def get_contour_scan_speed(self):
        return self.contour_scan_speed

    @Slot(float)
    def set_contour_duty_cycle(self, value):
        self.contour_duty_cycle = value

    def get_contour_duty_cycle(self):
        return self.contour_duty_cycle

    @Slot(float)
    def set_contour_frequency(self, value):
        self.contour_frequency = value

    def get_contour_frequency(self):
        return self.contour_frequency

    def get_parameters_dict(self):
        slicer_data = {
            'infill_laser_power': self.infill_laser_power,
            'infill_scan_speed': self.infill_scan_speed,
            'infill_duty_cycle': self.infill_duty_cycle,
            'infill_frequency': self.infill_frequency,
            'infill_density': self.infill_density,
            'infill_overlap': self.infill_overlap,
            'infill_rotation_angle': self.infill_rotation_angle,
            'infill_strategy_idx': self.infill_strategy_idx,
            'contour_laser_power': self.contour_laser_power,
            'contour_scan_speed': self.contour_scan_speed,
            'contour_duty_cycle': self.contour_duty_cycle,
            'contour_frequency': self.contour_frequency,
            'contour_strategy_idx': self.contour_strategy_idx
        }
        return slicer_data

    def set_parameters_from_dict(self, parameters):
        self.set_infill_laser_power(parameters['infill_laser_power'])
        self.set_infill_scan_speed(parameters['infill_scan_speed'])
        self.set_infill_duty_cycle(parameters['infill_duty_cycle'])
        self.set_infill_frequency(parameters['infill_frequency'])
        self.set_infill_density(parameters['infill_density'])
        self.set_infill_overlap(parameters['infill_overlap'])
        self.set_infill_rotation_angle(parameters['infill_rotation_angle'])
        self.set_infill_strategy_idx(parameters['infill_strategy_idx'])
        self.set_contour_laser_power(parameters['contour_laser_power'])
        self.set_contour_scan_speed(parameters['contour_scan_speed'])
        self.set_contour_duty_cycle(parameters['contour_duty_cycle'])
        self.set_contour_frequency(parameters['contour_frequency'])
        self.set_contour_strategy_idx(parameters['contour_strategy_idx'])

