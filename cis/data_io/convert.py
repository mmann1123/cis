"""Functions for converting to and from xarray objects
"""
import numpy as np

from xarray.core.dataarray import DataArray
from xarray.core.pycompat import OrderedDict
from xarray.conventions import (
    maybe_encode_timedelta, maybe_encode_datetime, decode_cf)


cdms2_ignored_attrs = {'name', 'tileIndex'}
iris_forbidden_keys = {'standard_name', 'long_name', 'units', 'bounds', 'axis',
     'calendar', 'leap_month', 'leap_year', 'month_lengths',
     'coordinates', 'grid_mapping', 'climatology',
     'cell_methods', 'formula_terms', 'compress',
     'missing_value', 'add_offset', 'scale_factor',
     'valid_max', 'valid_min', 'valid_range', '_FillValue'}
cell_methods_strings = {'point', 'sum', 'maximum', 'median', 'mid_range',
                            'minimum', 'mean', 'mode', 'standard_deviation',
                            'variance'}


def encode(var):
    return maybe_encode_timedelta(maybe_encode_datetime(var.variable))


def _filter_attrs(attrs, ignored_attrs):
    """ Return attrs that are not in ignored_attrs
    """
    return dict((k, v) for k, v in attrs.items() if k not in ignored_attrs)


def _pick_attrs(attrs, keys):
    """ Return attrs with keys in keys list
    """
    return dict((k, v) for k, v in attrs.items() if k in keys)


def _get_iris_args(attrs):
    """ Converts the xarray attrs into args that can be passed into Iris
    """
    # iris.unit is deprecated in Iris v1.9
    import cf_units
    args = {'attributes': _filter_attrs(attrs, iris_forbidden_keys)}
    args.update(_pick_attrs(attrs, ('standard_name', 'long_name',)))
    unit_args = _pick_attrs(attrs, ('calendar',))
    if 'units' in attrs:
        args['units'] = cf_units.Unit(attrs['units'], **unit_args)
    return args


# TODO: Add converting bounds from xarray to Iris and back
def to_iris(dataarray):
    """ Convert a DataArray into a Iris Cube
    """
    # Iris not a hard dependency
    import iris
    try:
        from iris.fileformats.netcdf import parse_cell_methods
    except ImportError:
        # prior to v1.10
        from iris.fileformats._pyke_rules.compiled_krb.fc_rules_cf_fc \
            import _parse_cell_methods as parse_cell_methods

    dim_coords = []
    aux_coords = []

    for coord_name in dataarray.coords:
        coord = encode(dataarray.coords[coord_name])
        coord_args = _get_iris_args(coord.attrs)
        coord_args['var_name'] = coord_name
        axis = None
        if coord.dims:
            axis = dataarray.get_axis_num(coord.dims)
        if coord_name in dataarray.dims:
            iris_coord = iris.coords.DimCoord(coord.values, **coord_args)
            dim_coords.append((iris_coord, axis))
        else:
            iris_coord = iris.coords.AuxCoord(coord.values, **coord_args)
            aux_coords.append((iris_coord, axis))

    args = _get_iris_args(dataarray.attrs)
    args['var_name'] = dataarray.name
    args['dim_coords_and_dims'] = dim_coords
    args['aux_coords_and_dims'] = aux_coords
    if 'cell_methods' in dataarray.attrs:
        args['cell_methods'] = parse_cell_methods(
            dataarray.name, dataarray.attrs['cell_methods'])

    cube = iris.cube.Cube(dataarray.to_masked_array(), **args)
    return cube


def _iris_obj_to_attrs(obj):
    """ Return a dictionary of attrs when given a Iris object
    """
    attrs = {'standard_name': obj.standard_name,
             'long_name': obj.long_name}
    if obj.units.calendar:
        attrs['calendar'] = obj.units.calendar
    if obj.units.origin != '1':
        attrs['units'] = obj.units.origin
    attrs.update(obj.attributes)
    return dict((k, v) for k, v in attrs.items() if v is not None)


def _iris_cell_methods_to_str(cell_methods_obj):
    """ Converts a Iris cell methods into a string
    """
    cell_methods = []
    for cell_method in cell_methods_obj:
        names = ''.join(['{}: '.format(n) for n in cell_method.coord_names])
        intervals = ' '.join(['interval: {}'.format(interval)
                              for interval in cell_method.intervals])
        comments = ' '.join(['comment: {}'.format(comment)
                             for comment in cell_method.comments])
        extra = ' '.join([intervals, comments]).strip()
        if extra:
            extra = ' ({})'.format(extra)
        cell_methods.append(names + cell_method.method + extra)
    return ' '.join(cell_methods)


def from_iris(cube):
    """ Convert a Iris cube into an DataArray
    """
    import iris.exceptions
    name = cube.var_name
    dims = []
    for i in xrange(cube.ndim):
        try:
            dim_coord = cube.coord(dim_coords=True, dimensions=(i,))
            dims.append(dim_coord.var_name)
        except iris.exceptions.CoordinateNotFoundError:
            dims.append("dim_{}".format(i))

    coords = OrderedDict()

    for coord in cube.coords():
        coord_attrs = _iris_obj_to_attrs(coord)
        coord_dims = [dims[i] for i in cube.coord_dims(coord)]
        if not coord.var_name:
            raise ValueError('Coordinate has no var_name')
        if coord_dims:
            coords[coord.var_name] = (coord_dims, coord.points, coord_attrs)
        else:
            coords[coord.var_name] = ((),
                                      np.asscalar(coord.points), coord_attrs)

    array_attrs = _iris_obj_to_attrs(cube)
    cell_methods = _iris_cell_methods_to_str(cube.cell_methods)
    if cell_methods:
        array_attrs['cell_methods'] = cell_methods
    dataarray = DataArray(cube.data, coords=coords, name=name,
                          attrs=array_attrs, dims=dims)
    decoded_ds = decode_cf(dataarray._to_temp_dataset())
    return dataarray._from_temp_dataset(decoded_ds)