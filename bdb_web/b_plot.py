import logging
_log = logging.getLogger("bdb-web")


import StringIO

from flask import make_response

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

import numpy as np


from bdb_web.structure import get_b_factors, get_structure


def calc_fig_size(b_num, ca=True):
    """Calculate figure size.

    If Calpha, return standard figure size, otherwise take number of B-factors
    into account.

    Figure size is a (width, height) tuple
    Also return boolean indicating that downscaling is necessary
    """
    fig_size = (23, 12)
    downscale = False

    if not ca:
        fig_size = (b_num*0.2, 12)
        if fig_size[0] > 2417:
            _log.debug("Figure width ({}) too large. Setting max width".
                       format(fig_size[0]))
            fig_size = (409, 12)
            downscale = True

    return fig_size, downscale


def show(pdb_id, ca=True):
    """Create B-factor plots for both BDB and PDB entries.

    If ca is false, show a bigger plot with all atoms

    If the pdb_id is invalid return None.
    If both PDB and BDB entries do not exist, return None.
    If only the BDB entry does not exist, only plot the PDB B-factors.
    """
    response = None
    minor = ca

    # Create Bio.PDB structures
    sp = get_structure(pdb_id, "pdb")
    if not sp:
        return None
    sb = get_structure(pdb_id, "bdb")

    # PDB
    # Get a list of (full atom id, B-factor) tuples
    bp = get_b_factors(sp)

    # Calculate figure size
    fig_size, minor = calc_fig_size(b_num=len(bp), ca=ca)

    # Create the figure
    fig = Figure(figsize=fig_size)
    ax = fig.add_subplot(111)

    # Set title, ylabel and grid
    ax.set_title(pdb_id)
    ax.set_ylabel('B-factor')
    ax.grid(True)
    ax.set_axisbelow(True)

    # PDB B-factors
    b_fac_p, b_ind_p = get_xdata(b_list=bp, ca=ca)
    p_line, = ax.plot(b_fac_p, color='grey', ls='-', lw=2)

    # BDB B-factors
    if sb:
        bb = get_b_factors(sb)
        b_fac_b, b_ind_b = get_xdata(b_list=bb, ca=ca)
        b_line, = ax.plot(b_fac_b, color='black', ls='-', lw=2)
        ax.legend(('pdb', 'bdb'))
    else:
        ax.legend('pdb')

    # X-axis ticks and labels
    sub_bp = [bp[i] for i in b_ind_p]
    xt, xtl, xtm = get_xticks(b_list=sub_bp, ca=ca, minor=minor)
    ax.xaxis.set_ticks(xt)
    ax.xaxis.set_ticklabels(xtl, rotation='vertical')
    if len(xtm) > 0:
        ax.xaxis.set_ticks(xtm, minor=True)

    # Create a response
    canvas = FigureCanvas(fig)
    output = StringIO.StringIO()
    canvas.print_png(output)
    response = make_response(output.getvalue())
    response.mimetype = "image/png"

    return response


def get_xdata(b_list, ca=False):
    """Return B-factor values to plot and selected indices from b_list."""

    b_inds = []
    if ca:
        b_inds = [i for i, b in enumerate(b_list) if b[0][4][0] == 'CA']
    else:
        b_inds = np.arange(0, len(b_list))

    b_vals = [b[1] for b in b_list]
    b_vals = np.take(b_vals, b_inds)

    return b_vals, b_inds


def get_xticks(b_list, ca=False, minor=False):
    """Create major ticks and labels and minor tick locations for X-axis.

    Full atom ids are used to create tick labels

    If minor is true, return fewer major and minor ticks
    If minor is false, return only major ticks at every atom position in b_list
    """
    maj_loc = []
    maj_lab = []
    min_loc = []

    bl = len(b_list)

    # Full atom id as x-tick labels
    maj_lab = [''.join((lb[0][2], ''.join(str(l) for l in lb[0][3]),
               ''.join(str(m) for m in lb[0][4]))) for lb in b_list]

    # Default major ticks: all atoms
    maj_loc = np.arange(0, bl)
    if ca:
        scale = int(bl/300)
        maj_loc = np.arange(0, bl, 5*scale if scale > 0 else 1)
        min_loc = np.arange(0, bl, scale if scale > 0 else 1)
    elif minor:
        scale = int(bl/1000)
        maj_loc = np.arange(0, bl, 2*scale if scale > 0 else 1)
        min_loc = np.arange(0, bl, scale if scale > 0 else 1)

    maj_lab = np.take(maj_lab, maj_loc)

    return maj_loc, maj_lab, min_loc
