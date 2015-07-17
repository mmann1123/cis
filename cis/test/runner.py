from setuptools.command.test import test as TestCommand
import multiprocessing

def run(test_set='cis/test/unit', n_processors=1, stop=False):
    import nose

    args = ['', test_set, '--processes=%s' % n_processors, '--verbosity=2',]

    if stop:
        args.append('--stop')

    nose.run(argv=args)


class nose_test(TestCommand):
    """
    Command to run unit tests
    """
    description = "Run CIS tests. By default this will run all of the unit tests. Optionally the integration tests can" \
                  " be run instead."
    user_options = [('integration-tests', 'i', 'Run the integration tests.'),
                    ('stop', 'x', 'Stop running tests after the first error or failure.'),
                    ('num-processors=', 'p', 'The number of processors used for running the tests.')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.integration_tests = False
        self.stop = False
        self.num_processors = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
        if self.integration_tests:
            self.test_set = 'cis/test/integration'
        else:
            self.test_set = 'cis/test/unit'

        if self.num_processors is None:
            self.num_processors = multiprocessing.cpu_count() - 1
        else:
            self.num_processors = int(self.num_processors)

    def run_tests(self):
        run(self.test_set, self.num_processors, self.stop)

        # nose.run_exit(argv=['nosetests',os.path.join(os.path.dirname(__file__), 'unit')])

