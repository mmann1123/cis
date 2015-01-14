import unittest
from hamcrest import assert_that, is_
import numpy
import iris

from jasmin_cis.calc.calculator import Calculator
from jasmin_cis.test.util import mock


class TestCalculator(unittest.TestCase):

    def setUp(self):
        self.calc = Calculator()
        self.data = [mock.make_mock_cube()]
        self.data[0].var_name = 'var_name'

    def _make_two_cubes(self):
        cube_1 = mock.make_mock_cube()
        cube_2 = mock.make_mock_cube(data_offset=10)
        cube_1.var_name = 'var1'
        cube_2._var_name = 'var2'
        self.data = [cube_1, cube_2]

    def _make_two_ungridded_data(self):
        data1 = mock.make_regular_2d_ungridded_data_with_missing_values()
        data2 = mock.make_regular_2d_ungridded_data_with_missing_values()
        data1.metadata._name = 'var1'
        data2.metadata._name = 'var2'
        self.data = [data1, data2]

    def test_GIVEN_expr_with_double_underscores_WHEN_calculate_THEN_raises_ValueError(self):
        expr = "[c for c in ().__class__.__base__.__subclasses__() if c.__name__ " \
               "== 'catch_warnings'][0]()._module.__builtins__['__import__']('os')"
        with self.assertRaises(ValueError):
            self.calc.evaluate(self.data, expr)

    def test_GIVEN_expr_using_disallowed_builtins_WHEN_calculate_THEN_raises_NameError(self):
        expr = 'open("path")'
        with self.assertRaises(NameError):
            self.calc.evaluate(self.data, expr)

    def test_GIVEN_expr_using_numpy_WHEN_calculate_THEN_allowed(self):
        expr = 'numpy.log(var_name)'
        self.calc.evaluate(self.data, expr)

    def test_GIVEN_expr_using_allowed_builtins_WHEN_calculate_THEN_allowed(self):
        expr = 'var_name + sum(sum(var_name))'
        self.calc.evaluate(self.data, expr)

    def test_GIVEN_two_cubes_and_basic_addition_WHEN_calculate_THEN_addition_successful(self):
        self._make_two_cubes()
        expr = 'var1 + var2'

        res = self.calc.evaluate(self.data, expr)
        expected = numpy.array([[12, 14, 16], [18, 20, 22], [24, 26, 28], [30, 32, 34], [36, 38, 40]])

        assert_that(numpy.array_equal(res.data, expected))

    def test_GIVEN_two_cubes_basic_addition_WHEN_calculate_THEN_metadata_correct(self):
        self._make_two_cubes()
        expr = 'var1 + var2'

        res = self.calc.evaluate(self.data, expr)
        expected_var_name = 'calculated_variable'
        expected_standard_name = None
        expected_long_name = 'Calculated value for expression "%s"' % expr
        expected_history = ''

        assert_that(isinstance(res, iris.cube.Cube))
        assert_that(res.var_name, is_(expected_var_name))
        assert_that(res.standard_name, is_(expected_standard_name))
        assert_that(res.long_name, is_(expected_long_name))
        assert_that(res.history, is_(expected_history))

    def test_GIVEN_two_cubes_interpolated_WHEN_calculate_THEN_interpolation_successful(self):
        self._make_two_cubes()
        # Simulate the use case of interpolating between two wavelengths
        #550 -> [600] -> 670
        expr = 'var1 + (var2 - var1) * (600 - 550) / (670 - 550)'

        res = self.calc.evaluate(self.data, expr)
        expected = numpy.array([[5, 6, 7], [8, 9, 10], [11, 12, 13], [14, 15, 16], [17, 18, 19]]) + 1.0/6

        assert_that(numpy.allclose(res.data, expected))

    def test_GIVEN_ungridded_data_basic_addition_WHEN_calculate_THEN_addition_successful(self):
        data1 = mock.make_regular_2d_ungridded_data()
        data2 = mock.make_regular_2d_ungridded_data()
        data1.metadata._name = 'var1'
        data2.metadata._name = 'var2'
        self.data = [data1, data2]
        expr = 'var1 + var2'

        res = self.calc.evaluate(self.data, expr)
        expected = 2 * self.data[1].data

        assert_that(numpy.array_equal(res.data, expected))

    def test_GIVEN_ungridded_missing_values_WHEN_calculate_THEN_missing_values_preserved(self):
        data = mock.make_regular_2d_ungridded_data_with_missing_values()
        data.metadata._name = 'var1'
        self.data = [data]
        expr = 'var1 + 10'

        res = self.calc.evaluate(self.data, expr)
        expected = numpy.ma.masked_invalid([[11, 12, 13], [14, float('Nan'), 16], [17, 18, float('Nan')],
                                            [20, 21, 22], [float('Nan'), 24, 25]])
        self._compare_masked_arrays(res.data, expected)

    def _compare_masked_arrays(self, a1, a2):
        """
        Compare two masked arrays:
        - Masks should be the same
        - Unmasked data should be same
        - Shape should be same
        - Numeric values that are 'masked out' don't matter
        """
        flat_1 = a1.filled(numpy.inf)
        flat_2 = a2.filled(numpy.inf)
        assert_that(numpy.array_equal(flat_1, flat_2), 'Masked arrays have different values')
        assert_that(numpy.array_equal(a1.mask, a2.mask), 'Masked arrays have different masks')
        assert_that(a1.shape, is_(a2.shape), 'Masked arrays have different shapes')