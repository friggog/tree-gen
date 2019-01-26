""" Default tree parameters """

import sys


class TreeParam(object):
    """parameter list for default tree (aspen)"""
    shape = 7
    g_scale = 13
    g_scale_v = 3
    levels = 3
    ratio = 0.015
    ratio_power = 1.2
    flare = 0.6
    floor_splits = 0
    base_splits = 0
    base_size = [0.3, 0.02, 0.02, 0.02]
    down_angle = [-0, 60, 45, 45]
    down_angle_v = [-0, -50, 10, 10]
    rotate = [-0, 140, 140, 77]
    rotate_v = [-0, 0, 0, 0]
    branches = [-0, 50, 30, 10]
    length = [1, 0.3, 0.6, 0]
    length_v = [0, 0, 0, 0]
    taper = [1, 1, 1, 1]
    seg_splits = [0, 0, 0, 0]
    split_angle = [40, 0, 0, 0]
    split_angle_v = [5, 0, 0, 0]
    curve_res = [5, 5, 3, 1]
    curve = [0, -40, -40, 0]
    curve_back = [0, 0, 0, 0]
    curve_v = [20, 50, 75, 0]
    bend_v = [-0, 50, 0, 0]
    branch_dist = [-0, 0, 0, 0]
    radius_mod = [1, 1, 1, 1]
    leaf_blos_num = 25
    leaf_shape = 0
    leaf_scale = 0.17
    leaf_scale_x = 1
    leaf_bend = 0
    blossom_shape = 0
    blossom_scale = 0
    blossom_rate = 0
    tropism = [0, 0, 0.5]
    prune_ratio = 0
    prune_width = 0.5
    prune_width_peak = 0.5
    prune_power_low = 0.5
    prune_power_high = 0.5

    def __init__(self, params):
        """initialize parameters from dictionary representation"""

        self.params = {}

        filtered = {}
        for k, v in params.items():
            try:
                # Ensure no methods are overwritten (prevent monkey-business)
                if str(type(self.__getattribute__(k))) != "<class 'method'>":
                    filtered[k] = v
            # Catch typos
            except AttributeError as ex:
                sys.stdout.write('TreeGen :: Warning: Unrecognized name in configuration "{}"'.format(k))
                sys.stdout.flush()

        # Copy parameters into instance
        self.params.update(filtered)

        # Specialized parameter formatting
        for var in ['shape', 'levels', 'floor_splits', 'leaf_shape', 'blossom_shape']:
            if var in filtered:
                self.params[var] = abs(int(filtered[var]))

        if 'base_splits' in filtered:
            self.params['base_splits'] = int(filtered['base_splits'])

        self.__dict__.update(self.params)

    def param_to_arr(self):
        """Convert usable parameters to array output for use with scikit-learn"""

        return [
            self.g_scale,
            self.g_scale_v,
            self.levels,
            self.ratio,
            self.ratio_power,
            self.flare,
            self.floor_splits,
            self.base_splits,
            *self.base_size,
            *self.down_angle[1:],
            *self.down_angle_v[1:],
            *self.rotate[1:],
            *self.rotate_v[1:],
            *self.branches[1:],
            *self.length,
            *self.length_v,
            *self.taper,
            *self.seg_splits,
            *self.split_angle,
            *self.split_angle_v,
            *self.curve_res,
            *self.curve,
            *self.curve_back,
            *self.curve_v,
            *self.bend_v[1:],
            *self.branch_dist[1:],
            *self.radius_mod,
            abs(self.leaf_blos_num),
            *self.tropism
        ]
