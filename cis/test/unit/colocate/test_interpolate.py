import unittest
import datetime as dt

import numpy as np

from cis.collocation.interpolate import collocate
from cis.test.util import mock
from cis.data_io.datalist import DataList
from numpy.testing import assert_almost_equal, assert_equal, assert_raises
from nose.tools import eq_


class TestGriddedUngriddedCollocator(unittest.TestCase):

    def test_gridded_ungridded_nn(self):
        data = mock.make_mock_cube()
        data.name = lambda: 'Name'
        data.var_name = 'var_name'
        data._standard_name = 'y_wind'
        sample = mock.make_dummy_sample_points(lat=[1.0, 3.0, -1.0], lon=[1.0, 3.0, -1.0], alt=[12.0, 7.0, 5.0],
                                               time=[dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34)])
        constraint = None

        output = collocate(sample, data, constraint, 'nn')

        expected_result = np.array([8, 12, 8])
        assert len(output) == 1
        assert isinstance(output, DataList)
        assert np.allclose(output[0].data, expected_result)

    def test_gridded_ungridded_lin(self):
        data = mock.make_mock_cube()
        data.name = lambda: 'Name'
        data.var_name = 'var_name'
        data._standard_name = 'y_wind'
        sample = mock.make_dummy_sample_points(lat=[1.0, 3.0, -1.0], lon=[1.0, 3.0, -1.0], alt=[12.0, 7.0, 5.0],
                                               time=[dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34)])
        constraint = None

        output = collocate(sample, data, constraint, 'lin')

        expected_result = np.array([8.8, 10.4, 7.2])
        assert len(output) == 1
        assert isinstance(output, DataList)
        assert np.allclose(output[0].data, expected_result)

    def test_missing_data_for_missing_sample(self):
        data = mock.make_mock_cube()
        data.name = lambda: 'Name'
        data.var_name = 'var_name'
        data._standard_name = 'y_wind'
        sample = mock.make_dummy_sample_points(lat=[1.0, 3.0, -1.0], lon=[1.0, 3.0, -1.0], alt=[12.0, 7.0, 5.0],
                                               time=[dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34)])
        constraint = None

        sample_mask = [False, True, False]
        sample.data = np.ma.array([0, 0, 0], mask=sample_mask)

        output = collocate(sample, data, constraint, 'nn', missing_data_for_missing_sample=True)

        assert len(output) == 1
        assert isinstance(output, DataList)
        assert np.array_equal(output[0].data.mask, sample_mask)

    def test_no_missing_data_for_missing_sample(self):
        data = mock.make_mock_cube()
        data.name = lambda: 'Name'
        data.var_name = 'var_name'
        data._standard_name = 'y_wind'
        sample = mock.make_dummy_sample_points(lat=[1.0, 3.0, -1.0], lon=[1.0, 3.0, -1.0], alt=[12.0, 7.0, 5.0],
                                               time=[dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34),
                                                     dt.datetime(1984, 8, 29, 8, 34)])
        constraint = None

        sample_mask = [False, True, False]
        sample.data = np.ma.array([0, 0, 0], mask=sample_mask)

        output = collocate(sample, data, constraint, 'nn', missing_data_for_missing_sample=False)

        assert len(output) == 1
        assert isinstance(output, DataList)
        assert not any(output[0].data.mask)

    def test_missing_data_for_missing_sample_with_no_extrapolation(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 4.0, -4.0], lon=[0.0, 4.0, -4.0],
                                                      alt=[5550.0, 6000.0, 6500.0],
                                                      time=[dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 27)])

        sample_mask = [False, True, False]
        sample_points.data = np.ma.array([0, 0, 0], mask=sample_mask)

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN, 
                             missing_data_for_missing_sample=True)[0]
        assert_almost_equal(new_data.data[0], 222.4814815, decimal=7)
        # This point should be masked because of the sampling
        assert np.ma.is_masked(new_data.data[1])
        # And this one because of the extrapolation
        assert np.ma.is_masked(new_data.data[2])

    def test_collocation_of_pres_points_on_hybrid_altitude_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[-4.0], lon=[-4.0], pres=[100.0],
                                                      time=[dt.datetime(1984, 8, 27)])

        # Since there is no corresponding pressure field in the source data a ValueError should be raised
        assert_raises(ValueError, collocate, sample_points, cube, None, 'lin', fill_value=np.NAN)

    def test_order_of_coords_doesnt_matter(self):
        from iris.cube import Cube
        from iris.coords import DimCoord
        import numpy as np

        cube_lat = DimCoord(np.linspace(-90, 90, 18), standard_name='latitude', units='degrees')
        cube_lon = DimCoord(np.linspace(0, 359, 36), standard_name='longitude', units='degrees', circular=True)
        cube_alt = DimCoord(np.linspace(0, 10000, 10), standard_name='altitude', units='meters')

        times = np.linspace(0, 30, 12)
        cube_time = DimCoord(times, standard_name='time', units='days since 1970-01-01 00:00:00')

        data = np.arange(12 * 18 * 36 * 10).reshape(12, 18, 36, 10)
        source = Cube(data, dim_coords_and_dims=[(cube_time, 0), (cube_lat, 1), (cube_lon, 2), (cube_alt, 3)])

        n = 10
        sample_lats = np.linspace(-9.1, 9.9, n)
        sample_longs = np.linspace(-9.1, 9.9, n)
        sample_alts = np.linspace(99, 599, n)
        sample_times = np.linspace(0, 30, n)

        sample = mock.make_dummy_sample_points(lat=sample_lats, lon=sample_longs, alt=sample_alts,
                                                      time=sample_times)

        output = collocate(sample, source, None, 'nn')[0]

        source.transpose()
        assert_equal(collocate(sample, source, None, 'nn')[0].data, output.data)

        source.transpose((2, 1, 0, 3))
        assert_equal(collocate(sample, source, None, 'nn')[0].data, output.data)


class TestNN(unittest.TestCase):

    def test_basic_col_gridded_to_ungridded_in_2d(self):
        cube = mock.make_square_5x3_2d_cube()

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0])

        new_data = collocate(sample_points, cube, None, 'nn')[0]
        eq_(new_data.data[0], 8.0)  # float(cube[2,1].data))
        eq_(new_data.data[1], 12.0)  # float(cube[3,2].data))
        eq_(new_data.data[2], 4.0)  # float(cube[1,0].data))

    def test_basic_col_with_circular_lon(self):
        cube = mock.make_dummy_2d_cube_with_circular_lon()

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 0.0, 0.0, 80.0, 85.0, 90.0, -80.0, -85.0, -90.0],
                                                      lon=[0.0, 355.0, 360.0, 0.0, 355.0, 360.0, 0.0, 355.0, 360.0])

        new_data = collocate(sample_points, cube, None, 'nn')[0]
        wanted = np.asarray([325.0, 360.0, 325.0,
                             613.0, 648.0, 649.0,
                             37.0, 36.0, 1.0])
        assert_almost_equal(new_data.data, wanted)

    def test_negative_lon_points_dont_matter_with_0_360_grid_in_2d(self):
        # This cube is defined over a 0-360 longitude grid
        cube = mock.make_dummy_2d_cube()

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 19.0, -4.0, -4.0], lon=[1.0, 44.0, -14.0, -44.0])

        new_data = collocate(sample_points, cube, None, 'nn')[0]
        eq_(new_data.data[0], 325.0)  # float(cube[9,0].data)
        eq_(new_data.data[1], 365.0)  # float(cube[10,4].data))
        eq_(new_data.data[2], 324.0)  # float(cube[8,35].data))
        eq_(new_data.data[3], 321.0)  # float(cube[8,32].data))

    def test_guessing_the_bounds_on_a_cube_doesnt_matter_for_negative_lon_points_on_a_0_360_grid_in_2d(self):
        """This should be identical to above but there was an issue in iris where this caused a problem"""

        # This cube is defined over a 0-360 longitude grid
        cube = mock.make_dummy_2d_cube()
        cube.coord(standard_name='longitude').guess_bounds()

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 19.0, -4.0, -4.0], lon=[1.0, 44.0, -14.0, -44.0])

        new_data = collocate(sample_points, cube, None, 'nn')[0]
        eq_(new_data.data[0], 325.0)  # float(cube[9,0].data)
        eq_(new_data.data[1], 365.0)  # float(cube[10,4].data))
        eq_(new_data.data[2], 324.0)  # float(cube[8,35].data))
        eq_(new_data.data[3], 321.0)  # float(cube[8,32].data))

    def test_lon_points_over_360_dont_matter_with_0_360_grid_in_2d(self):
        # This cube is defined over a 0-360 longitude grid
        cube = mock.make_dummy_2d_cube()

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 1.0, 1.0, 1.0], lon=[0.0, 20.0, 361.0, 381.0])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], 325.0)  # float(cube[9,0].data))
        eq_(new_data.data[1], 327.0)  # float(cube[9,0].data))
        eq_(new_data.data[2], 325.0)  # float(cube[9,0].data))
        eq_(new_data.data[3], 327.0)  # float(cube[9,2].data))

    def test_already_collocated_in_col_gridded_to_ungridded_in_2d(self):
        cube = mock.make_square_5x3_2d_cube()
        # This point already exists on the cube with value 5 - which shouldn't be a problem
        sample_points = mock.make_dummy_sample_points(lat=[0.0], lon=[0.0])
        new_data = collocate(sample_points, cube, None, 'nn')[0]
        eq_(new_data.data[0], 8.0)

    def test_collocation_of_alt_points_on_hybrid_altitude_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10, geopotential_height=True)

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      alt=[5000.0, 6000.0, 6500.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 27, 2, 18, 52)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], 221.0)  # float(cube[2,1,1,0].data))
        eq_(new_data.data[1], 345.0)  # float(cube[3,2,1,4].data))
        eq_(new_data.data[2], 100.0)  # float(cube[1,0,0,9].data))

    def test_negative_lon_points_on_hybrid_altitude_coordinates_dont_matter(self):
        """This should give the same results as above"""
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0], lon=[1.0, 4.0],
                                                      # One point below and inside the source altitude bounds
                                                      alt=[5000.0, 6000.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34)])

        new_data = collocate(sample_points, cube, None, 'nn')[0]
        eq_(new_data.data[0], 221.0)  # float(cube[2,1,1,0].data))
        eq_(new_data.data[1], 345.0)  # float(cube[3,2,1,4].data))

    def test_collocation_of_alt_points_on_hybrid_altitude_coordinates_on_0_360_grid(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10, lon_dim_length=36, lon_range=(0., 350.))

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0], lon=[111.0, 141.0],
                                                      alt=[5000.0, 12000.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], 2501.0)  # float(cube[2,11,1,0].data))
        eq_(new_data.data[1], 3675.0)  # float(cube[3,14,1,4].data))

    def test_negative_lon_points_on_hybrid_altitude_coordinates_with_0_360_grid(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10, lon_dim_length=36, lon_range=(0., 350.))

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[111.0, 141.0, -14.0],
                                                      alt=[5000.0, 12000.0, 10000.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 27, 2, 18, 52)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], 2501.0)  # float(cube[2,11,1,0].data))
        eq_(new_data.data[1], 3675.0)  # float(cube[3,14,1,4].data))
        eq_(new_data.data[2], 2139.0)  # float(cube[1,35,0,8].data))

    def test_collocation_of_alt_pres_points_on_hybrid_altitude_coordinates(self):
        """
        Redundant pressure coordinates should be ignored by the kernel
        """
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      alt=[5000.0, 6000.0, 6500.0],
                                                      pres=[10000.0, 10000.0, 10000.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 27, 2, 18, 52)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], float(cube[2, 1, 1, 0].data))
        eq_(new_data.data[1], float(cube[3, 2, 1, 4].data))
        eq_(new_data.data[2], float(cube[1, 0, 0, 9].data))

    def test_collocation_of_pres_points_on_hybrid_pressure_coordinates_and_altitude_coordinates(self):
        """
            When only pressure coordinate is present this should be used for the collocation
        """
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      pres=[1100000.0, 184600000.0, 63100049.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 27, 2, 18, 52)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], float(cube[2, 1, 1, 0].data))
        eq_(new_data.data[1], float(cube[3, 2, 1, 4].data))
        eq_(new_data.data[2], float(cube[1, 0, 0, 9].data))

    def test_collocation_of_alt_pres_points_on_hybrid_pressure_and_altitude_coordinates(self):
        """
            When altitude and pressure coordinates are present only the altitude coordinates should be used for the
            collocation
        """
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, geopotential_height=True)

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      pres=[110000.0, 11000000.0, 63100049.0],
                                                      alt=[10, 354, 1000],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 27, 2, 18, 52)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], float(cube[2, 1, 1, 0].data))
        eq_(new_data.data[1], float(cube[3, 2, 1, 4].data))
        eq_(new_data.data[2], float(cube[1, 0, 0, 9].data))

    def test_collocation_of_alt_points_on_hybrid_pressure_and_altitude_coordinates(self):
        """
            Kernel should use the auxilliary altitude dimension when altitude is present in the coordinates
        """
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, geopotential_height=True)

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      alt=[10, 354, 1000],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 27, 2, 18, 52)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], float(cube[2, 1, 1, 0].data))
        eq_(new_data.data[1], float(cube[3, 2, 1, 4].data))
        eq_(new_data.data[2], float(cube[1, 0, 0, 9].data))

    def test_coordinates_exactly_between_points_in_col_gridded_to_ungridded_in_2d(self):
        """
            This works out the edge case where the points are exactly in the middle or two or more datapoints.
                Iris seems to count a point as 'belonging' to a datapoint if it is greater than a datapoint cell's lower
                bound and less than or equal to it's upper bound. Where a cell is an imaginary boundary around a
                datapoint which divides the grid.
        """
        cube = mock.make_square_5x3_2d_cube()
        sample_points = mock.make_dummy_sample_points(lat=[2.5, -2.5, 2.5, -2.5], lon=[2.5, 2.5, -2.5, -2.5])
        new_data = collocate(sample_points, cube, None, 'nn')[0]
        eq_(new_data.data[0], 8.0)
        eq_(new_data.data[1], 5.0)
        eq_(new_data.data[2], 7.0)
        eq_(new_data.data[3], 4.0)

    def test_coordinates_outside_grid_in_col_gridded_to_ungridded_in_2d(self):
        cube = mock.make_square_5x3_2d_cube()
        sample_points = mock.make_dummy_sample_points(lat=[5.5, -5.5, 5.5, -5.5], lon=[5.5, 5.5, -5.5, -5.5])
        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], 12.0)
        eq_(new_data.data[1], 6.0)
        eq_(new_data.data[2], 10.0)
        eq_(new_data.data[3], 4.0)

    def test_basic_col_gridded_to_ungridded_in_2d_with_time(self):
        cube = mock.make_square_5x3_2d_cube_with_time()

        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      time=[dt.datetime(1984, 8, 28, 8, 34),
                                                            dt.datetime(1984, 8, 31, 1, 23),
                                                            dt.datetime(1984, 9, 2, 15, 54)])

        new_data = collocate(sample_points, cube, None, 'nn', extrapolate=True)[0]
        eq_(new_data.data[0], 51.0)
        eq_(new_data.data[1], 82.0)
        eq_(new_data.data[2], 28.0)


class TestLinear(unittest.TestCase):
    def test_basic_col_gridded_to_ungridded_using_li_in_2d(self):
        cube = mock.make_square_5x3_2d_cube()
        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0])

        new_data = collocate(sample_points, cube, None, 'lin')[0]
        assert_almost_equal(new_data.data[0], 8.8)
        assert_almost_equal(new_data.data[1], 11.2)
        assert_almost_equal(new_data.data[2], 4.8)

    def test_basic_col_with_circular_lon(self):
        cube = mock.make_dummy_2d_cube_with_circular_lon()

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 0.0, 0.0, 80.0, 85.0, 90.0, -80.0, -85.0, -90.0],
                                                      lon=[0.0, 355.0, 360.0, 0.0, 355.0, 360.0, 0.0, 355.0, 360.0])

        new_data = collocate(sample_points, cube, None, 'lin')[0]
        wanted = np.asarray([325.0, 342.5, 325.0,
                             613.0, (630.5 + 666.5) / 2, 649.0,
                             37.0, (54.5 + 18.5) / 2, 1.0])
        assert_almost_equal(new_data.data, wanted)

    def test_negative_lon_points_in_2d_dont_matter(self):
        """
            This is exactly the same test as above, except we ommit the point with negative longitude, this makes the
            collocator wrap the longitude coordinate and gives a slightly different interpolation result...
        """
        cube = mock.make_square_5x3_2d_cube()
        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0], lon=[1.0, 4.0])
        new_data = collocate(sample_points, cube, None, 'lin')[0]
        assert_almost_equal(new_data.data[0], 8.8)
        assert_almost_equal(new_data.data[1], 11.2)

    def test_collocation_of_points_on_hybrid_altitude_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 4.0, -4.0], lon=[0.0, 4.0, -4.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      alt=[5550.0, 6000.0, 6500.0],
                                                      time=[dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN)[0]
        assert_almost_equal(new_data.data[0], 222.4814815, decimal=7)
        assert_almost_equal(new_data.data[1], 321.0467626, decimal=7)
        # Test that points outside the cell are returned as masked, rather than extrapolated by default
        assert np.ma.is_masked(new_data.data[2])

    def test_negative_lon_points_on_hybrid_altitude_coordinates_dont_matter(self):
        """
            This is exactly the same test as above, except we ommit the point with negative longitude, this makes the
            collocator wrap the longitude coordinate and gives a slightly different interpolation result...
        """
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[4.0, 0.0], lon=[4.0, 0.0],
                                                      # One point below, inside and above the source altitude bounds
                                                      alt=[6000.0, 5550.0],
                                                      time=[dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 28)])

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN)[0]
        assert_almost_equal(new_data.data[0], 321.0467626, decimal=7)
        assert_almost_equal(new_data.data[1], 222.4814815, decimal=7)

    def test_wrapping_of_alt_points_on_hybrid_height_coordinates_on_0_360_grid(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10, lon_dim_length=36, lon_range=(0., 350.))

        # Shift the cube around so that the dim which isn't hybrid (time) is at the front. This breaks the fix we used
        #  for air pressure...
        cube.transpose([2, 0, 1, 3])
        # Ensure the longitude coord is circular
        cube.coord(standard_name='longitude').circular = True

        sample_points = mock.make_dummy_sample_points(lat=[4.0, 0.0], lon=[355.0, 2.0],
                                                      alt=[11438.0, 10082.0],
                                                      time=[dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 28)])

        new_data = collocate(sample_points, cube, None, 'lin', extrapolate=False)[0]
        eq_(new_data.data[0], 3563.0)
        eq_(new_data.data[1], 2185.0)

    def test_collocation_of_alt_pres_points_on_hybrid_altitude_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 4.0, -4.0], lon=[0.0, 4.0, -4.0],
                                                      alt=[5550.0, 6000.0, 6500.0],
                                                      pres=[10000.0, 1000.0, 100.0],
                                                      time=[dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 28),
                                                            dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN)[0]
        assert_almost_equal(new_data.data[0], 222.4814815, decimal=7)
        assert_almost_equal(new_data.data[1], 321.0467626, decimal=7)
        # Test that points outside the cell are returned as masked, rather than extrapolated by default
        assert np.ma.is_masked(new_data.data[2])

    def test_alt_extrapolation(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_ht_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[-4.0], lon=[-4.0], alt=[6382.8],
                                                      time=[dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN, extrapolate=True)[0]
        assert_almost_equal(new_data.data[0], 126.0, decimal=7)

    def test_collocation_of_pres_points_on_hybrid_pressure_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 0.0, 5.0, -4.0], lon=[0.0, 0.0, 2.5, -4.0],
                                                      pres=[111100040.0, 113625040.0, 177125044.0, 166600039.0],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 28, 12, 0, 0),
                                                            dt.datetime(1984, 8, 27, 0, 0, 0),
                                                            dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin')[0]
        # Exactly on the lat, lon, time points, interpolated over pressure
        assert_almost_equal(new_data.data[0], 221.5, decimal=5)
        # Exactly on the lat, lon, points, interpolated over time and pressure
        assert_almost_equal(new_data.data[1], 226.5, decimal=7)
        # Exactly on the lat, time points, interpolated over longitude and pressure
        assert_almost_equal(new_data.data[2], 330.5, decimal=7)
        # Outside of the pressure bounds - extrapolation off
        assert np.ma.is_masked(new_data.data[3])

    def test_collocation_of_pres_alt_points_on_hybrid_pressure_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 0.0, 5.0, -4.0], lon=[0.0, 0.0, 2.5, -4.0],
                                                      pres=[111100040.0, 113625040.0, 177125044.0, 166600039.0],
                                                      alt=[5000, 4000, 3000, 3500],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 28, 12, 0, 0),
                                                            dt.datetime(1984, 8, 27, 0, 0, 0),
                                                            dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin')[0]
        # Exactly on the lat, lon, time points, interpolated over pressure
        assert_almost_equal(new_data.data[0], 221.5, decimal=5)
        # Exactly on the lat, lon, points, interpolated over time and pressure
        assert_almost_equal(new_data.data[1], 226.5, decimal=7)
        # Exactly on the lat, time points, interpolated over longitude and pressure
        assert_almost_equal(new_data.data[2], 330.5, decimal=7)
        # Outside of the pressure bounds - extrapolation off
        assert np.ma.is_masked(new_data.data[3])

    def test_collocation_of_pres_alt_points_on_hybrid_pressure_coordinates_nn(self):
        cube = mock.make_mock_cube(time_dim_length=3)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 0.0, 5.0, -4.0], lon=[0.0, 0.0, 2.5, -4.0],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 28, 12, 0, 0),
                                                            dt.datetime(1984, 8, 27, 0, 0, 0),
                                                            dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin')[0]
        # Exactly on the lat, lon, time points, interpolated over pressure
        assert_almost_equal(new_data.data[0], 23.0, decimal=5)
        # Exactly on the lat, lon, points, interpolated over time and pressure
        assert_almost_equal(new_data.data[1], 23.5, decimal=7)
        # Exactly on the lat, time points, interpolated over longitude and pressure
        assert_almost_equal(new_data.data[2], 33.5, decimal=7)
        # Outside of the pressure bounds - extrapolation off
        assert_almost_equal(new_data.data[3], 12.4, decimal=7)

    def test_collocation_of_pres_alt_points_on_hybrid_pressure_coordinates_multi_var(self):
        cube_list = [mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10),
                     mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, data_offset=100)]

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 0.0, 5.0, -4.0], lon=[0.0, 0.0, 2.5, -4.0],
                                                      pres=[111100040.0, 113625040.0, 177125044.0, 166600039.0],
                                                      alt=[5000, 4000, 3000, 3500],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 28, 12, 0, 0),
                                                            dt.datetime(1984, 8, 27, 0, 0, 0),
                                                            dt.datetime(1984, 8, 27)])

        outlist = collocate(sample_points, cube_list, None, 'lin')
        # First data set:
        new_data = outlist[0]
        # Exactly on the lat, lon, time points, interpolated over pressure
        assert_almost_equal(new_data.data[0], 221.5, decimal=5)
        # Exactly on the lat, lon, points, interpolated over time and pressure
        assert_almost_equal(new_data.data[1], 226.5, decimal=7)
        # Exactly on the lat, time points, interpolated over longitude and pressure
        assert_almost_equal(new_data.data[2], 330.5, decimal=7)
        # Outside of the pressure bounds - extrapolation off
        assert np.ma.is_masked(new_data.data[3])

        # Second dataset:
        new_data = outlist[1]
        # Exactly on the lat, lon, time points, interpolated over pressure
        assert_almost_equal(new_data.data[0], 321.5, decimal=5)
        # Exactly on the lat, lon, points, interpolated over time and pressure
        assert_almost_equal(new_data.data[1], 326.5, decimal=7)
        # Exactly on the lat, time points, interpolated over longitude and pressure
        assert_almost_equal(new_data.data[2], 430.5, decimal=7)
        # Outside of the pressure bounds - extrapolation off
        assert np.ma.is_masked(new_data.data[3])

    def test_negative_lon_points_on_hybrid_pressure_coordinates_dont_matter(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10)

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 5.0], lon=[0.0, 2.5],
                                                      pres=[111100040.0, 177125044.0],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 27, 0, 0, 0)])

        new_data = collocate(sample_points, cube, None, 'lin')[0]
        # Exactly on the lat, lon, time points, interpolated over pressure
        assert_almost_equal(new_data.data[0], 221.5, decimal=5)
        # Exactly on the lat, time points, interpolated over latitude and pressure
        assert_almost_equal(new_data.data[1], 330.5, decimal=7)

    def test_wrapping_of_pres_points_on_hybrid_pressure_coordinates_on_0_360_grid(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, lon_dim_length=36, lon_range=(0., 350.))

        # Ensure the longitude coord is circular
        cube.coord(standard_name='longitude').circular = True

        sample_points = mock.make_dummy_sample_points(lat=[0.0, 5.0], lon=[355.0, 2.5],
                                                      pres=[1482280045.0, 1879350048.0],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 27, 0, 0, 0)])

        new_data = collocate(sample_points, cube, None, 'lin', extrapolate=False)[0]
        eq_(new_data.data[0], 2701.0011131725005)
        eq_(new_data.data[1], 3266.1930161260775)

    def test_extrapolation_of_pres_points_on_hybrid_pressure_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10)

        # Point interpolated in the horizontal and then extrapolated past the top vertical layer (by one layer)
        sample_points = mock.make_dummy_sample_points(lat=[-4.0], lon=[-4.0], pres=[68400050.0],
                                                      time=[dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube, None, 'lin', extrapolate=True)[0]
        assert_almost_equal(new_data.data[0], 125.0, decimal=7)

    def test_extrapolation_of_pres_points_on_hybrid_pressure_coordinates_multi_var(self):
        cube_list = [mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10),
                     mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, data_offset=100)]

        # Point interpolated in the horizontal and then extrapolated past the top vertical layer (by one layer)
        sample_points = mock.make_dummy_sample_points(lat=[-4.0], lon=[-4.0], pres=[68400050.0],
                                                      time=[dt.datetime(1984, 8, 27)])

        new_data = collocate(sample_points, cube_list, None, 'lin', extrapolate=True)
        assert_almost_equal(new_data[0].data[0], 125.0, decimal=7)
        assert_almost_equal(new_data[1].data[0], 225.0, decimal=7)

    def test_collocation_of_alt_points_on_hybrid_altitude_and_pressure_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, geopotential_height=True)

        # Test point with both pressure and altitude should interpolate over the altitude only (since that is also
        #  present in the data cube)
        sample_points = mock.make_dummy_sample_points(lat=[0.0, 5.0], lon=[0.0, 5.0],
                                                      alt=[234.5, 355.5],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 8, 28, 0, 0, 0)])

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN)[0]
        assert_almost_equal(new_data.data[0], 225.5, decimal=7)
        assert_almost_equal(new_data.data[1], 346.5, decimal=7)

    def test_collocation_of_alt_pres_points_on_hybrid_altitude_and_pressure_coordinates(self):
        cube = mock.make_mock_cube(time_dim_length=3, hybrid_pr_len=10, geopotential_height=True)

        # Test point with both pressure and altitude should interpolate over the altitude only (since that is also
        #  present in the data cube)
        sample_points = mock.make_dummy_sample_points(lat=[0.0], lon=[0.0], alt=[234.5], pres=[1000],
                                                      time=[dt.datetime(1984, 8, 28, 0, 0, 0)])

        new_data = collocate(sample_points, cube, None, 'lin', fill_value=np.NAN)[0]
        assert_almost_equal(new_data.data[0], 225.5, decimal=7)

    def test_collocation_over_scalar_coord(self):
        # A scalar time coordinate should make no difference when collocating points with a time value.
        cube = mock.make_square_5x3_2d_cube_with_scalar_time()

        # Note that it doesn't even matter if the point is outside the bounds of the scalar time...
        # TODO: Is this correct behaviour?
        sample_points = mock.make_dummy_sample_points(lat=[1.0, 4.0, -4.0], lon=[1.0, 4.0, -4.0],
                                                      time=[dt.datetime(1984, 8, 22, 0, 0, 0),
                                                            dt.datetime(1984, 8, 28, 0, 0, 0),
                                                            dt.datetime(1984, 10, 1, 0, 0, 0)])

        new_data = collocate(sample_points, cube, None, 'lin')[0]

        assert_almost_equal(new_data.data[0], 8.8)
        assert_almost_equal(new_data.data[1], 11.2)
        assert_almost_equal(new_data.data[2], 4.8)