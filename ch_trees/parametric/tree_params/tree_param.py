""" Default tree parameters """


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
        if 'shape' in params:
            self.shape = abs(int(params['shape']))
        if 'g_scale' in params:
            self.g_scale = params['g_scale']
        if 'g_scale_v' in params:
            self.g_scale_v = params['g_scale_v']
        if 'levels' in params:
            self.levels = abs(int(params['levels']))
        if 'ratio' in params:
            self.ratio = params['ratio']
        if 'ratio_power' in params:
            self.ratio_power = params['ratio_power']
        if 'flare' in params:
            self.flare = params['flare']
        if 'floor_splits' in params:
            self.floor_splits = abs(int(params['floor_splits']))
        if 'base_splits' in params:
            self.base_splits = int(params['base_splits'])
        if 'base_size' in params:
            self.base_size = params['base_size']
        if 'down_angle' in params:
            self.down_angle = params['down_angle']
        if 'down_angle_v' in params:
            self.down_angle_v = params['down_angle_v']
        if 'rotate' in params:
            self.rotate = params['rotate']
        if 'rotate_v' in params:
            self.rotate_v = params['rotate_v']
        if 'branches' in params:
            self.branches = params['branches']
        if 'length' in params:
            self.length = params['length']
        if 'length_v' in params:
            self.length_v = params['length_v']
        if 'taper' in params:
            self.taper = params['taper']
        if 'seg_splits' in params:
            self.seg_splits = params['seg_splits']
        if 'split_angle' in params:
            self.split_angle = params['split_angle']
        if 'split_angle_v' in params:
            self.split_angle_v = params['split_angle_v']
        if 'curve_res' in params:
            self.curve_res = params['curve_res']
        if 'curve' in params:
            self.curve = params['curve']
        if 'curve_back' in params:
            self.curve_back = params['curve_back']
        if 'curve_v' in params:
            self.curve_v = params['curve_v']
        if 'bend_v' in params:
            self.bend_v = params['bend_v']
        if 'branch_dist' in params:
            self.branch_dist = params['branch_dist']
        if 'radius_mod' in params:
            self.radius_mod = params['radius_mod']
        if 'leaf_blos_num' in params:
            self.leaf_blos_num = params['leaf_blos_num']
        if 'leaf_shape' in params:
            self.leaf_shape = params['leaf_shape']
        if 'leaf_scale' in params:
            self.leaf_scale = params['leaf_scale']
        if 'leaf_scale_x' in params:
            self.leaf_scale_x = params['leaf_scale_x']
        if 'leaf_bend' in params:
            self.leaf_bend = params['leaf_bend']
        if 'blossom_shape' in params:
            self.blossom_shape = params['blossom_shape']
        if 'blossom_scale' in params:
            self.blossom_scale = params['blossom_scale']
        if 'blossom_rate' in params:
            self.blossom_rate = params['blossom_rate']
        if 'tropism' in params:
            self.tropism = params['tropism']
        if 'prune_ratio' in params:
            self.prune_ratio = params['prune_ratio']
        if 'prune_width' in params:
            self.prune_width = params['prune_width']
        if 'prune_width_peak' in params:
            self.prune_width_peak = params['prune_width_peak']
        if 'prune_power_low' in params:
            self.prune_power_low = params['prune_power_low']
        if 'prune_power_high' in params:
            self.prune_power_high = params['prune_power_high']

    def param_to_arr(self):
        """convert usable paramters to array output for use with scikit-learn"""
        res = [self.g_scale,
               self.g_scale_v,
               self.levels,
               self.ratio,
               self.ratio_power,
               self.flare,
               self.floor_splits,
               self.base_splits]
        res.extend(self.base_size)
        res.extend(self.down_angle[1:])
        res.extend(self.down_angle_v[1:])
        res.extend(self.rotate[1:])
        res.extend(self.rotate_v[1:])
        res.extend(self.branches[1:])
        res.extend(self.length)
        res.extend(self.length_v)
        res.extend(self.taper)
        res.extend(self.seg_splits)
        res.extend(self.split_angle)
        res.extend(self.split_angle_v)
        res.extend(self.curve_res)
        res.extend(self.curve)
        res.extend(self.curve_back)
        res.extend(self.curve_v)
        res.extend(self.bend_v[1:])
        res.extend(self.branch_dist[1:])
        res.extend(self.radius_mod)
        res.append(abs(self.leaf_blos_num))
        res.extend(self.tropism)
        return res
