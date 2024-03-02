# ISR Matcher

A package for map matching gnss measurements onto german rail network. Supports route visualization and creation of route profiles (velocity, acceleration, incline and height profiles).

## Description

This package enables map matching onto german rail network. The data of the rail infrastructure is requested from [ISR](https://geovdbn.deutschebahn.com/isr), a service of Deutsche Bahn. 

GNSS measurements can be input only in CSV format. They must contain at least three columns (latitude, longitude and time). Further columns can be used by the tool (altitude, speed, acceleration), but they are not necessary. 

The tool matches the GNSS trajectory to the german rail network and performs certain analysis tasks. Results are written to file(s).

Please note that this is still an unstable release. In the current form, it is a prototype of a map matching tool that was created during a 4-month period for my master's thesis. The implementation may suffer from unexpected errors, bugs or performance issues.

## Getting Started

This section gives a short overview of dependencies and usage of the package.

### Dependencies

The package is supported and tested for python version 3.11.

The package has the following dependencies, which will be installed along the package:

    *folium>=0.15.1,
    *matplotlib>=3.8.2,
    *numpy>=1.26.4,
    *pandas>=2.2.1,
    *pyproj>=3.6.0,
    *pytest>=7.4.3,
    *requests>=2.31.0,
    *scipy>=1.12.0,
    *shapely>=2.0.3,


### Installing

Install the package using pip:

```bash
pip install isr_matcher
```

### Example usage

The following script demonstrates the basic usage of the tool. The script can be downloaded from [github](https://github.com/mgillwald/isr_matcher/tree/main/examples) along with the (simulated) test data.

```python
from isr_matcher import matching, clear_cache
from pathlib import Path

## INPUT: CSV FILE

# (Option 1) Rename the columns in your csv file to the following standardized names:

    # latitude: column with latitudes (WGS84)
    # longitude: column with longitudes (WGS84)
    # time_utc: column with timestamps
    # time_s: column with passed time in seconds
    # altitude_m: column with measured altitudes, in meter
    # velocity_ms: column with measured velocity, in meter per second
    # acceleration_ms: column with measured acceleration, in meter per square second

    # It is only necessary that the columns latitude, longitude and one time column are included. The rest is optional.

# (Option 2) OR pass a dict mapping the column names in your csv file to these standardized column names

column_name_dict = {
        "time_utc": 'column_name_in_csv_file_with_utc_time_stamps',                # can be None (if time_s is given)
        "time_s": 'column_name_in_csv_file_with_time_in_seconds',                  # can be None (if time_utc is given)
        "latitude": 'column_name_in_csv_file_with_latitudes',                      # obligatory
        "longitude": 'column_name_in_csv_file_with_longitudes',                    # ogligatory
        "altitude_m": 'column_name_in_csv_file_with_measured_altitude',            # can be None (if not available)
        "velocity_ms": 'column_name_in_csv_file_with_measured_velocity',           # can be None (if not available)
        "acceleration_ms2": 'column_name_in_csv_file_with_measured_acceleration',  # can be None (if not available)
    }


# map matching: set parameter

# (obligatory)
root = Path(__file__).parent.parent          
export_path = root / 'examples/results/'     # change this as needed
csv_path = root / 'examples/test_data.csv'   # change this as needed
column_name_dict = None                      # if csv file has correct column names, else see options above

# (optional, listed are default values)
r = 1500                                     # boundary around gnss for querying rail infrastructure, in meter
sigma = None                                 # standard devioation of gnss error. If None, is estimated with 'sigma_method'
prune = 'auto'                               # 'auto': prunes measurements in 2 * sigma distance of each other. 
                                             # float: replace 2 * sigma by value in meter
                                             # None: No pruning
path_resolution_m: float = 5                 # spacing between points for the computed path of the train.
average_low_velocity = True                  # averages consecutive measurements with velocity smaller than 'threshold_velocity' (if measuremnts are available)
threshold_velocity = 3                       # sets a threshold for averaging low velocities, in meter per second
sigma_method = 'mad'                         # method for estimating sigma ('mad': conservative estimate, 'std': bold estimate)
create_plots = False                         # sets if plots are created and exported (velocity, acceleration, incline, height)
skiprows = 0                                 # number of rows that are skipped at start of csv file (with a header row, this should be set to 0.)
correct_velocity = True                      # sets if the computed velocity should be corrected for inclines
cache_preprocessed_segments = True           # sets if preprocessed track segments are written to cache for fast loading next time (i.e faster preprocessing)

# run map matching with default settings

# clear_cache()                              # optional, run this ONLY if you want to remove all preprocessed track files from cache
matching(
    export_path=export_path,                 # path to directory where results are written to
    csv_path=csv_path,                       # path to csv file with gnss measuremnts
    column_name_dict=column_name_dict,       # if csv file has correct column names, else see options above
)
```

## Help

If you encounter problems or are looking for help, please open an [issue](https://github.com/mgillwald/isr_matcher/issues) or send me a [mail](marco.gillwald@gmx.de).

## Authors

Marco Gillwald ([marco.gillwald@gmx.de](marco.gillwald@gmx.de) / [mgillwald](https://github.com/mgillwald))

## Version History

* 0.0.3
    * Readme updated
    * Example added
    * Updated doc strings
* 0.0.2
    * Readme added
* 0.0.1
    * Initial Release

## Road Map

Primary goals for the near future are:

    * Release Documentation
    * Bug fixes and code optimization
    * Expand testing

Reaching those goals will culminate in the first stable release. Additionally, a small GUI is intended for simple usage and control of features.


## License

This project is licensed under the Apache Software License 2.0 - see the LICENSE file for details

## Acknowledgments

This package does not include, but allows to query data from infrastructure registry ([Infrastrukturregister](https://geovdbn.deutschebahn.com/isr)) of Deutsche Bahn.
This package uses kilometrage information from the dataset [Geo-Streckennetz](https://data.deutschebahn.com/dataset/geo-strecke.html) of Deutsche Bahn.
