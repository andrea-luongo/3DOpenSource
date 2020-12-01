from PyTracer.pyStructs import BBox, Ray, RayIntersectionInfo, Plane, PlaneIntersectionInfo
import numpy as np
from dataclasses import dataclass, field
import struct


@dataclass
class BVHBuildNode:
    first_node: None  # this should be a BVHBuildNode
    second_node: None  # this should be a BVHBuildNode
    bbox: BBox = None
    first_primitive_offset: int = -1
    number_of_primitives: int = 0
    split_axis: int = -1

    @staticmethod
    def init_leaf_node(first_primitive_offset, number_of_primitive, bbox):
        return BVHBuildNode(first_node=None, second_node=None, first_primitive_offset=first_primitive_offset, number_of_primitives=number_of_primitive, bbox=bbox)

    @staticmethod
    def init_interior_node(split_axis, node_0, node_1):
        new_bbox = BBox.union(node_0.bbox, node_1.bbox)
        return BVHBuildNode(split_axis=split_axis, first_node=node_0, second_node=node_1, bbox=new_bbox)


@dataclass
class PrimitiveInfo:
    primitive_bbox: BBox
    primitive_index: int = -1
    centroid: float = field(init=False, repr=False)

    def __post_init__(self):
        self.centroid = 0.5 * (self.primitive_bbox.m_min + self.primitive_bbox.m_max)


@dataclass
class BucketInfo:
    count: int = 0
    bucket_bbox: BBox = BBox()


@dataclass
class MortonPrimitive:
    primitive_index: int = 0
    morton_code: np.uint32 = 0


@dataclass
class LBVHTreelet:
    build_nodes: None
    start_index: int = 0
    number_of_primitives: int = 0


@dataclass
class LinearBVHNode:
    bbox: BBox = None
    primitives_offset: int = 0
    second_child_offset: int = 0
    number_of_primitives: int = 0
    axis: np.uint8 = 0
    pad: np.uint8 = 0


class BVH:

    def __init__(self, primitives=[], split_method='Middle', max_primitives_in_node=255):
        self.primitives = primitives
        self.split_method = split_method
        self.max_primitives_in_node = min(255, max_primitives_in_node)
        self.total_nodes = 0
        self.primitives_info = [PrimitiveInfo(primitive_index=idx, primitive_bbox=val.bbox) for idx, val in
                                enumerate(self.primitives)]
        self.ordered_primitives = []
        if len(self.primitives) == 0:
            return
        if self.split_method == 'HLBVH':
            #TODO not implemented yet!!!!
            self.bvh_root = self.__HLBVH_build()
        else:
            self.bvh_root = self.__recursive_build(0, len(self.primitives))

        self.primitives, self.ordered_primitives = self.ordered_primitives, self.primitives
        self.ordered_primitives = None
        del self.primitives_info[:]
        self.linear_nodes = [LinearBVHNode() for _ in range(self.total_nodes)]
        offset = 0
        self.__flatten_bvh_tree(self.bvh_root, offset)

    def __recursive_build(self, start_idx, end_idx):
        self.total_nodes += 1
        b_boxes = [self.primitives_info[idx].primitive_bbox for idx in range(start_idx, end_idx)]
        node_bbox = BBox.list_union(b_boxes)
        number_of_primitives = end_idx - start_idx
        if number_of_primitives == 1:
            node = self.__create_leaf_bvh_node(node_bbox, start_idx, end_idx)
            return node
        else:
            centroids = [self.primitives_info[idx].centroid for idx in range(start_idx, end_idx)]
            centroid_bounds = BBox.list_points_union(centroids)
            dim = centroid_bounds.maximum_extent()
            # dim = centroid_bounds.maximum_extent
            if centroid_bounds.m_max[dim] == centroid_bounds.m_min[dim]:
                node = self.__create_leaf_bvh_node(node_bbox, start_idx, end_idx)
                return node
            else:
                mid_idx = int(0.5 * (start_idx + end_idx))
                if self.split_method == 'Middle':
                    success, mid_idx = self.__midpoint_split_method(centroid_bounds, dim, start_idx, end_idx)
                    if not success:
                        _, mid_idx = self.__equal_points_split_method(dim, start_idx, end_idx)
                elif self.split_method == 'EqualCounts':
                    _, mid_idx = self.__equal_points_split_method(dim, start_idx, end_idx)
                elif self.split_method == 'SAH':
                    success, mid_idx = self.__surface_area_split_method(node_bbox, centroid_bounds, dim, start_idx, end_idx)
                    if not success:
                        node = self.__create_leaf_bvh_node(node_bbox, start_idx, end_idx)
                        return node
                return BVHBuildNode.init_interior_node(dim, self.__recursive_build(start_idx, mid_idx), self.__recursive_build(mid_idx, end_idx))

    def __create_leaf_bvh_node(self, node_bbox: BBox, start_idx, end_idx):
        number_of_primitives = end_idx - start_idx
        first_primitive_offset = len(self.ordered_primitives)
        for idx in range(start_idx, end_idx):
            primitive_idx = self.primitives_info[idx].primitive_index
            self.ordered_primitives.append(self.primitives[primitive_idx])
        node = BVHBuildNode.init_leaf_node(first_primitive_offset, number_of_primitives, node_bbox)
        return node

    def __midpoint_split_method(self, centroid_bounds: BBox, dim, start_idx, end_idx):
        mid_point = 0.5 * (centroid_bounds.m_min[dim] + centroid_bounds.m_max[dim])
        partitioned_primitives_info = [None] * (end_idx - start_idx)
        left_idx = 0
        right_idx = (end_idx - start_idx - 1)
        for idx in range(start_idx, end_idx):
            if self.primitives_info[idx].centroid[dim] < mid_point:
                partitioned_primitives_info[left_idx] = self.primitives_info[idx]
                left_idx += 1
            else:
                partitioned_primitives_info[right_idx] = self.primitives_info[idx]
                right_idx -= 1
        mid_idx = left_idx + start_idx
        self.primitives_info[start_idx:end_idx] = partitioned_primitives_info
        if mid_idx != start_idx and mid_idx != end_idx:
            return True, mid_idx
        else:
            return False, mid_idx

    def __equal_points_split_method(self, dim, start_idx, end_idx):
        # centroid_array = np.zeros(end_idx - start_idx)
        # for idx in range(0, end_idx - start_idx):
        #     centroid_array[idx] = self.primitives_info[start_idx + idx].centroid[dim]
        centroid_array = np.array([self.primitives_info[start_idx + idx].centroid[dim] for idx in range(0, end_idx - start_idx)])
        mid_idx = int(0.5 * (end_idx - start_idx))
        partition_idxs = np.argpartition(centroid_array, mid_idx)
        self.primitives_info[start_idx:end_idx] = [self.primitives_info[idx + start_idx] for idx in partition_idxs]
        return True, int(0.5 * (end_idx + start_idx))

    def __surface_area_split_method(self, node_bbox: BBox, centroid_bounds: BBox, dim, start_idx, end_idx):
        number_of_primitives = end_idx - start_idx
        if number_of_primitives < 5:
            return self.__equal_points_split_method(dim, start_idx, end_idx)
        else:
            # allocate bucketinfo
            number_of_buckets = 12
            buckets = [BucketInfo() for _ in range(number_of_buckets)]
            # buckets = [None] * number_of_buckets
            # for idx in range(len(buckets)):
            #     buckets[idx] = BucketInfo()

            # initialize bucketinfo
            for idx in range(start_idx, end_idx):
                b = int(number_of_buckets * centroid_bounds.offset(self.primitives_info[idx].centroid)[dim])
                if b == number_of_buckets:
                    b = number_of_buckets - 1
                buckets[b].count += 1
                buckets[b].bucket_bbox = BBox.union(buckets[b].bucket_bbox, self.primitives_info[idx].primitive_bbox)
            # compute costs
            traversal_cost = 0.125
            costs = np.zeros(number_of_buckets - 1)
            for idx_i in range(number_of_buckets - 1):
                b_0 = BBox()
                b_1 = BBox()
                count_0 = 0
                count_1 = 0
                for idx_j in range(idx_i + 1):
                    b_0 = BBox.union(b_0, buckets[idx_j].bucket_bbox)
                    count_0 += buckets[idx_j].count
                for idx_j in range(idx_i + 1, number_of_buckets):
                    b_1 = BBox.union(b_1, buckets[idx_j].bucket_bbox)
                    count_1 += buckets[idx_j].count
                costs[idx_i] = traversal_cost + (count_0 * b_0.surface_area() + count_1 * b_1.surface_area()) / node_bbox.surface_area()
            # find bucket
            min_cost = costs[0]
            min_cost_split_bucket = 0
            for idx in range(1, number_of_buckets - 1):
                if costs[idx] < min_cost:
                    min_cost = costs[idx]
                    min_cost_split_bucket = idx

            # create leaf or split
            leaf_cost = number_of_primitives
            if number_of_primitives > self.max_primitives_in_node or min_cost < leaf_cost:
                partitioned_primitives_info = [None] * (end_idx - start_idx)
                left_idx = 0
                right_idx = (end_idx - start_idx - 1)
                for idx in range(start_idx, end_idx):
                    b = int(number_of_buckets * centroid_bounds.offset(self.primitives_info[idx].centroid)[dim])
                    if b == number_of_buckets:
                        b = number_of_buckets - 1
                    if b <= min_cost_split_bucket:
                        partitioned_primitives_info[left_idx] = self.primitives_info[idx]
                        left_idx += 1
                    else:
                        partitioned_primitives_info[right_idx] = self.primitives_info[idx]
                        right_idx -= 1
                self.primitives_info[start_idx:end_idx] = partitioned_primitives_info
                mid_idx = left_idx + start_idx
                return True, mid_idx
            else:
                return False, -1

    @staticmethod
    def __left_shift3(x):
        if x == (1 << 10):
            x -= 1
        x = (x | (x << 16)) & 0b00000011000000000000000011111111
        x = (x | (x <<  8)) & 0b00000011000000001111000000001111
        x = (x | (x <<  4)) & 0b00000011000011000011000011000011
        x = (x | (x <<  2)) & 0b00001001001001001001001001001001
        return x

    def __encode_morton3(self, v):
        v_int = np.array([struct.pack('>f', v[0]), struct.pack('>f', v[1]), struct.pack('>f', v[2])])
        v_int = np.array([struct.unpack('>l', v_int[0])[0], struct.unpack('>l', v_int[1])[0], struct.unpack('>l', v_int[2])[0]])
        return (self.__left_shift3(v_int[2]) << 2) | (self.__left_shift3(v_int[1]) << 1) | self.__left_shift3(v_int[0])

    @staticmethod
    def __radix_sort(morton_primitives):
        temp_vector = [MortonPrimitive() for _ in range(len(morton_primitives))]
        bits_per_pass = 6
        n_bits = 30
        n_passes = n_bits // bits_per_pass
        for pass_idx in range(n_passes):
            low_bit = pass_idx * bits_per_pass
            in_vector = temp_vector if (pass_idx & 1) else morton_primitives
            out_vector = morton_primitives if (pass_idx & 1) else temp_vector
            n_buckets = 1 << bits_per_pass
            bucket_count = np.zeros(n_buckets)
            bit_mask = (1 << bits_per_pass) - 1
            for mp in in_vector:
                bucket = (mp.morton_code >> low_bit) & bit_mask
                bucket_count[bucket] += 1
            out_index = np.zeros(n_buckets)
            for idx in range(1, n_buckets):
                out_index[idx] = out_index[idx - 1] + bucket_count[idx - 1]
            for mp in in_vector:
                bucket = (mp.morton_code >> low_bit) & bit_mask
                out_vector[out_index[bucket]] = mp
                out_index[bucket] += 1
        if n_passes & 1:
            morton_primitives, temp_vector = temp_vector, morton_primitives
        return morton_primitives

    def emit_LBVH(self, build_nodes, morton_primitives, n_primitives, total_nodes, bit_index):
        if bit_index == -1 or n_primitives < self.max_primitives_in_node:
            # create and return leaf node of lbvh treelet
            total_nodes += 1
            first_prim_offset = self.ordered_primitives_offset
            self.ordered_primitives += n_primitives
            node = build_nodes
            # to check: node = build_nodes++
            b_box = BBox()
            for idx in range(n_primitives):
                primitive_idx = morton_primitives[idx].primitive_index
                self.ordered_primitives[first_prim_offset + idx] = self.primitives[primitive_idx]
                b_box = BBox.union(b_box, self.primitives_info[primitive_idx].primitive_bbox)
            node = BVHBuildNode.init_leaf_node(first_prim_offset, n_primitives, b_box)
            return node, total_nodes
        else:
            mask = 1 << bit_index
            # advance to next subtree level
            if (morton_primitives[0].morton_code & mask) == (morton_primitives[n_primitives - 1].morton_code & mask):
                return self.emit_LBVH(build_nodes, morton_primitives, n_primitives, total_nodes, bit_index - 1)
            # find lbvh split point
            search_start = 0
            search_end = n_primitives - 1
            while (search_start + 1) != search_end:
                mid = (search_start + search_end) // 2
                if (morton_primitives[search_start].morton_code & mask) == (morton_primitives[mid].morton_code & mask):
                    search_start = mid
                else:
                    search_end = mid
            split_offset = search_end
            # create and return interior lbvh node
            total_nodes += 1
            node = build_nodes
            # to check: node = build_nodes++
            lbvh_0, total_nodes = self.emit_LBVH(build_nodes, morton_primitives, split_offset, total_nodes, bit_index - 1)
            lbvh_1, total_nodes = self.emit_LBVH(build_nodes, morton_primitives, n_primitives - split_offset, total_nodes, bit_index - 1)
            axis = bit_index % 3
            node = BVHBuildNode.init_interior_node(axis, lbvh_0, lbvh_1)
            return node, total_nodes

    def __HLBVH_build(self):
        # compute bbox of all centroids
        centroids = [self.primitives_info[idx].centroid for idx in range(len(self.primitives_info))]
        centroid_bounds = BBox.list_points_union(centroids)
        # compute morton code
        morton_primitives = [MortonPrimitive() for _ in range(len(self.primitives_info))]
        # TODO convert to parallel for and optimize
        morton_bits = 10
        morton_scale = 1 << morton_bits
        for idx in range(len(morton_primitives)):
            morton_primitives[idx].primitive_index = self.primitives_info[idx].primitive_index
            centroid_offset = centroid_bounds.offset(self.primitives_info[idx].centroid)
            morton_primitives[idx].morton_code = self.__encode_morton3(centroid_offset * morton_scale)
        # radix sort
        morton_primitives = self.__radix_sort(morton_primitives)
        # create lbvh treelets
        treelets_to_build = []
        start = 0
        for end in range(1, len(morton_primitives + 1)):
            t_mask = 0b00111111111111000000000000000000
            if end == len(morton_primitives) or (morton_primitives[start].morton_code & t_mask) != (morton_primitives[end].morton_code & t_mask):
                n_primitives = end - start
                max_bvh_nodes = n_primitives + n_primitives
                nodes = [BVHBuildNode() for _ in range(max_bvh_nodes)]
                treelets_to_build.append(LBVHTreelet(nodes, start, n_primitives))
                start = end
        self.ordered_primitives = [None] * len(self.primitives)
        atomic_total = 0
        self.ordered_primitives_offset = 0
        # TODO parallelize and optimize
        for idx in range(len(treelets_to_build)):
            first_bit_index = 29 - 12
            nodes_created = 0
            treelet = treelets_to_build[idx]
            treelet.build_nodes, nodes_created = self.emit_LBVH(treelet.build_nodes, morton_primitives, treelet.number_of_primitives, nodes_created, first_bit_index)
            atomic_total += nodes_created
        self.total_nodes = atomic_total
        finished_treelets = []
        for treelet in treelets_to_build:
            finished_treelets.append(treelet.build_nodes)
        # create and return sah bvh
        return []

    def __flatten_bvh_tree(self, node: BVHBuildNode, offset=0):
        linear_node = self.linear_nodes[offset]
        linear_node.bbox = node.bbox
        my_offset = offset
        offset += 1
        if node.number_of_primitives > 0:
            linear_node.primitives_offset = node.first_primitive_offset
            linear_node.number_of_primitives = node.number_of_primitives
        else:
            linear_node.axis = node.split_axis
            linear_node.number_of_primitives = 0
            _, offset = self.__flatten_bvh_tree(node.first_node, offset)
            linear_node.second_child_offset, offset = self.__flatten_bvh_tree(node.second_node, offset)
            # linear_node.second_child_offset = a
        return my_offset, offset

    def intersect(self, ray: Ray, info: RayIntersectionInfo):
        hit = False
        inv_dir = np.divide(1.0, ray.direction)
        dir_is_neg = inv_dir < 0
        to_visit_offset = 0
        current_node_idx = 0
        nodes_to_visit = [0] * 100000
        while True:
            node = self.linear_nodes[current_node_idx]
            if node.bbox.any_intersect(ray, inv_dir, dir_is_neg):
                if node.number_of_primitives > 0:
                    for idx in range(node.number_of_primitives):
                        if self.primitives[node.primitives_offset+idx].intersect(ray, info):
                            hit = True
                    if to_visit_offset == 0:
                        break
                    to_visit_offset -= 1
                    current_node_idx = nodes_to_visit[to_visit_offset]
                else:
                    try:
                        if dir_is_neg[node.axis]:
                            nodes_to_visit[to_visit_offset] = current_node_idx + 1
                            to_visit_offset += 1
                            current_node_idx = node.second_child_offset
                        else:
                            nodes_to_visit[to_visit_offset] = node.second_child_offset
                            to_visit_offset += 1
                            current_node_idx = current_node_idx + 1
                    except:
                        a=1
            else:
                if to_visit_offset == 0:
                    break
                to_visit_offset -= 1
                current_node_idx = nodes_to_visit[to_visit_offset]
        return hit

    def any_intersect(self, ray: Ray):
        hit = False
        inv_dir = np.divide(1.0, ray.direction)
        dir_is_neg = inv_dir < 0
        to_visit_offset = 0
        current_node_idx = 0
        nodes_to_visit = [0] * 1024
        while True:
            node = self.linear_nodes[current_node_idx]
            if node.bbox.any_intersect(ray, inv_dir, dir_is_neg):
                if node.number_of_primitives > 0:
                    for idx in range(node.number_of_primitives):
                        if self.primitives[node.primitives_offset+idx].any_intersect(ray):
                            hit = True
                            return hit
                    if to_visit_offset == 0:
                        break
                    to_visit_offset -= 1
                    current_node_idx = nodes_to_visit[to_visit_offset]
                else:
                    if dir_is_neg[node.axis]:
                        nodes_to_visit[to_visit_offset] = current_node_idx + 1
                        to_visit_offset += 1
                        current_node_idx = node.second_child_offset
                    else:
                        nodes_to_visit[to_visit_offset] = node.second_child_offset
                        to_visit_offset += 1
                        current_node_idx = current_node_idx + 1
            else:
                if to_visit_offset == 0:
                    break
                to_visit_offset -= 1
                current_node_idx = nodes_to_visit[to_visit_offset]
        return hit

    def all_intersections(self, ray: Ray, info: RayIntersectionInfo):
        hit = False
        inv_dir = np.true_divide(1.0, ray.direction)
        dir_is_neg = inv_dir < 0
        to_visit_offset = 0
        current_node_idx = 0
        nodes_to_visit = [0] * 1024
        while True:
            node = self.linear_nodes[current_node_idx]
            if node.bbox.any_intersect(ray, inv_dir, dir_is_neg):
                if node.number_of_primitives > 0:
                    for idx in range(node.number_of_primitives):
                        if self.primitives[node.primitives_offset+idx].all_intersect(ray, info):
                            hit = True
                    if to_visit_offset == 0:
                        break
                    to_visit_offset -= 1
                    current_node_idx = nodes_to_visit[to_visit_offset]
                else:
                    if dir_is_neg[node.axis]:
                        nodes_to_visit[to_visit_offset] = current_node_idx + 1
                        to_visit_offset += 1
                        current_node_idx = node.second_child_offset
                    else:
                        nodes_to_visit[to_visit_offset] = node.second_child_offset
                        to_visit_offset += 1
                        current_node_idx = current_node_idx + 1
            else:
                if to_visit_offset == 0:
                    break
                to_visit_offset -= 1
                current_node_idx = nodes_to_visit[to_visit_offset]
        return hit

    def plane_all_intersections(self, plane: Plane, info: PlaneIntersectionInfo):
        hit = False
        to_visit_offset = 0
        current_node_idx = 0
        # print(len(self.linear_nodes))
        nodes_to_visit = [0] * len(self.linear_nodes)
        try:
            while True:
                node = self.linear_nodes[current_node_idx]
                if node.bbox.plane_any_intersect(plane):
                    if node.number_of_primitives > 0:
                        for idx in range(node.number_of_primitives):
                            if self.primitives[node.primitives_offset+idx].intersect_plane(plane, info):
                                hit = True
                        if to_visit_offset == 0:
                            break
                        to_visit_offset -= 1
                        current_node_idx = nodes_to_visit[to_visit_offset]
                    else:
                        nodes_to_visit[to_visit_offset] = node.second_child_offset
                        to_visit_offset += 1
                        current_node_idx = current_node_idx + 1
                else:
                    if to_visit_offset == 0:
                        break
                    to_visit_offset -= 1
                    current_node_idx = nodes_to_visit[to_visit_offset]
            return hit
        except:
            return hit
