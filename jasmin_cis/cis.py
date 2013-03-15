#!/bin/env python2.7
'''
Command line interface for the Climate Intercomparison Suite (CIS)
'''
import sys
import logging

from jasmin_cis.exceptions import CISError

logger = logging.getLogger(__name__)

__author__ = "David Michel, Daniel Wallis and Duncan Watson-Parris"
__version__ = "V0R4M4"
__status__ = "Development"
__website__ = "http://proj.badc.rl.ac.uk/cedaservices/wiki/JASMIN/CommunityIntercomparisonSuite"


def __setup_logging(log_file, log_level):
    '''
    Set up the logging used throughout cis
    
    @param log_file:    The filename of the file to store the logs
    @param log_level:   The level at which to log 
    '''

    logging.basicConfig(format='%(levelname)s: %(message)s',filename=log_file, level=log_level)

    # This sends warnings straight to the logger, this is used as iris can throw a lot of warnings
    #  that we don't want bubbling up. We may change this in the future as it's a bit overkill.
    logging.captureWarnings(True)

def __error_occurred(e):
    '''
    Wrapper method used to print error messages.
    
    @param e: An error object or any string
    '''
    sys.stderr.write(str(e) + "\n")
    exit(1)

def __store_variable_name_in_dictionary(main_arguments, data, var_axis_dict, axis):
    from iris.cube import Cube
    from jasmin_cis.exceptions import InvalidVariableError, NotEnoughAxesSpecifiedError

    if axis == "x":
        other_axis = "y"
    elif axis =="y":
        other_axis = "x"

    for data_item in data:
        if not isinstance(data_item, Cube):

            if len(data_item.coords(name=main_arguments[axis + "axis"])) == 0:
                raise InvalidVariableError(main_arguments[axis + "axis"] + " is not a valid variable")
            else:
                if data_item.coord(name=main_arguments[axis + "axis"]).axis == other_axis.upper() and main_arguments[other_axis + "axis"] is None:
                    raise NotEnoughAxesSpecifiedError("--" + other_axis + "axis must also be specified if assigning the current " + other_axis + " axis coordinate to the " + axis + " axis")
                else:
                    var_axis_dict[main_arguments[axis + "axis"]] = axis.upper()
                    logging.info("Overriding data product default variable for " + axis + " axis with: " + main_arguments[axis + "axis"])
                    break
        else:
            raise NotImplementedError("Options --xaxis and --yaxis are not implemented for Cube object")


def __assign_variables_to_x_and_y_axis(main_arguments, data):
    # overwrites which variable to used for the x and y axis
    # ignore unknown variables
    from iris.cube import Cube
    var_axis_dict = {}
    if main_arguments['xaxis'] is not None:
        __store_variable_name_in_dictionary(main_arguments, data, var_axis_dict, "x")

    if main_arguments['yaxis'] is not None:
        __store_variable_name_in_dictionary(main_arguments, data, var_axis_dict, "y")

    main_arguments.pop("xaxis")
    main_arguments.pop("yaxis")

    print var_axis_dict

    for data_item in data:

        for coord in data_item.coords():
            print coord.name(), coord.axis

        if not isinstance(data_item, Cube):
            for coord in data_item.coords():
                if var_axis_dict.has_key(coord.name()):
                    coord.axis = var_axis_dict[coord.name()]
                if coord.name() not in var_axis_dict.iterkeys() and coord.axis in var_axis_dict.itervalues():
                    coord.axis = ''
        else:
            raise NotImplementedError("Options --xaxis and --yaxis are not implemented for Cube object")

        print "---"
        for coord in data_item.coords():
            print coord.name(), coord.axis

def plot_cmd(main_arguments):
    '''
    Main routine for handling calls to the 'plot' command. 
    Reads in the data files specified and passes the rest of the arguments to the plot function.
        

    @param main_arguments:    The command line arguments (minus the plot command)        
    '''
    from plotting.plot import Plotter
    from jasmin_cis.data_io.read import read_data
    import jasmin_cis.exceptions as ex
    from iris.exceptions import IrisError


    data = []
    try:
        # create a list of data object (ungridded or gridded(in that case, a Iris cube)), concatenating data from various files
        data = [ read_data(datagroup['filenames'], datagroup['variable'], datagroup['product']) for datagroup in main_arguments.datagroups ]

    except (IrisError, ex.InvalidVariableError, ex.ClassNotFoundError) as e:
        __error_occurred(e)
    except IOError as e:
        __error_occurred("There was an error reading one of the files: \n" + str(e))

    main_arguments = vars(main_arguments)
    main_arguments.pop('command') # Remove the command argument now it is not needed
    plot_type = main_arguments.pop("type")
    output = main_arguments.pop("output")

    try:
        __assign_variables_to_x_and_y_axis(main_arguments, data)
    except (ex.InvalidVariableError, ex.NotEnoughAxesSpecifiedError) as e:
        __error_occurred(e)

    try:
        Plotter(data, plot_type, output, **main_arguments)
    except (ex.CISError, ValueError) as e:
        __error_occurred(e)

def info_cmd(main_arguments):
    '''
    Main routine for handling calls to the 'info' command.
    Reads in the variables from the data file specified and lists them to stdout if no
    particular variable was specified, otherwise prints detailed information about each
    variable specified

    @param main_arguments:    The command line arguments (minus the info command)
    '''
    variables = main_arguments.variables
    filename = main_arguments.filename
    data_type = main_arguments.type

    from jasmin_cis.info import  info

    try:
        info(filename, variables, data_type)
    except CISError as e:
        __error_occurred(e)


def col_cmd(main_arguments):
    '''
    Main routine for handling calls to the co-locate ('col') command.

    @param main_arguments:    The command line arguments (minus the col command)
    '''
    from jasmin_cis.exceptions import ClassNotFoundError, CISError
    from jasmin_cis.col import Colocate
    from jasmin_cis.utils import add_file_prefix

    # Add a prefix to the output file so that we have a signature to use when we read it in again
    output_file = add_file_prefix("cis-col-", main_arguments.output + ".nc")

    try:
        col = Colocate(main_arguments.samplefiles, main_arguments.samplevariable, main_arguments.sampleproduct, output_file)
    except IOError as e:
        __error_occurred("There was an error reading one of the files: \n" + str(e))

    for input_group in main_arguments.datagroups:
        variable = input_group['variable']
        filenames = input_group['filenames']
        col_name = input_group['colocator'][0] if  input_group['colocator'] is not None else None
        col_options = input_group['colocator'][1] if  input_group['colocator'] is not None else None
        con_name = input_group['constraint'][0] if  input_group['constraint'] is not None else None
        con_options = input_group['constraint'][1] if  input_group['constraint'] is not None else None
        kern_name = input_group['kernel'][0] if  input_group['kernel'] is not None else None
        kern_options = input_group['kernel'][1] if  input_group['kernel'] is not None else None
        product = input_group["product"] if input_group["product"] is not None else None

        try:
            col.colocate(variable, filenames, col_name, col_options, con_name, con_options, kern_name, kern_options, product)
        except ClassNotFoundError as e:
            __error_occurred(str(e) + "\nInvalid co-location option.")
        except (CISError, IOError) as e:
            __error_occurred(e)


commands = { 'plot' : plot_cmd,
             'info' : info_cmd,
             'col'  : col_cmd} 

def main():
    '''
    The main method for the program.
    Sets up logging, parses the command line arguments and then calls the appropriate command with its arguments
    '''
    import os
    from parse import parse_args
    import logging, logging.config
    from datetime import datetime

    # configure logging
    logging.config.fileConfig( os.path.join(os.path.dirname(__file__), "logging.conf"))
    logging.captureWarnings(True) # to catch warning from 3rd party libraries

    # parse command line arguments
    arguments = parse_args()
    command = arguments.command

    logging.debug("CIS started at: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    logging.debug("Running command: " + command)
    logging.debug("With the following arguments: " + str(arguments))

    # execute command
    commands[command](arguments)


if __name__ ==  '__main__':
    main()
