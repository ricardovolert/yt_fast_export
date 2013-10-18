"""
This module contains a routine to search for topologically connected sets



"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from itertools import chain
import numpy as np

from yt.funcs import *
import yt.utilities.data_point_utilities as data_point_utilities
import yt.utilities.lib as amr_utils

def identify_contours(data_source, field, min_val, max_val,
                          cached_fields=None):
    tree = amr_utils.ContourTree()
    gct = amr_utils.TileContourTree(min_val, max_val)
    total_contours = 0
    contours = {}
    empty_mask = np.ones((1,1,1), dtype="uint8")
    node_ids = []
    for (g, node, (sl, dims, gi)) in data_source.tiles.slice_traverse():
        node.node_ind = len(node_ids)
        nid = node.node_id
        node_ids.append(nid)
        values = g[field][sl].astype("float64")
        contour_ids = np.zeros(dims, "int64") - 1
        gct.identify_contours(values, contour_ids, total_contours)
        new_contours = tree.cull_candidates(contour_ids)
        total_contours += new_contours.shape[0]
        tree.add_contours(new_contours)
        # Now we can create a partitioned grid with the contours.
        pg = amr_utils.PartitionedGrid(g.id,
            [contour_ids.view("float64")],
            empty_mask, g.dds * gi, g.dds * (gi + dims),
            dims.astype("int64"))
        contours[nid] = (g.Level, node.node_ind, pg, sl)
    node_ids = np.array(node_ids)
    trunk = data_source.tiles.tree.trunk
    mylog.info("Linking node (%s) contours.", len(contours))
    amr_utils.link_node_contours(trunk, contours, tree, node_ids)
    #joins = tree.cull_joins(bt)
    #tree.add_joins(joins)
    joins = tree.export()
    contour_ids = defaultdict(list)
    pbar = get_pbar("Updating joins ... ", len(contours))
    for i, nid in enumerate(sorted(contours)):
        level, node_ind, pg, sl = contours[nid]
        ff = pg.my_data[0].view("int64")
        amr_utils.update_joins(joins, ff)
        contour_ids[pg.parent_grid_id].append((sl, ff))
        pbar.update(i)
    pbar.finish()
    return dict(contour_ids.items())
