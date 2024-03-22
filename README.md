# ISR Matcher

A package for map matching GNSS measurements onto German rail network. Supports route visualization and creation of route profiles (velocity, acceleration, incline and height profiles).

## Description

This package enables map matching onto German rail network. The data of the rail infrastructure is requested from [ISR](https://geovdbn.deutschebahn.com/isr), a service of Deutsche Bahn. 

GNSS measurements can only be input in form of CSV files. They must contain at least three columns (latitude, longitude and time). Further columns can be used by the tool (altitude, speed, acceleration), but they are not necessary. 

The tool matches the GNSS trajectory to the German rail network and performs certain analysis tasks. Results are written to file(s). For a more detailed description of the functionality, see the section [Methodology](#methodolgy)

Please note that this is still an unstable release. In the current form, it is a prototype of a map matching tool that was created during a 4-month period for my master's thesis. The implementation may suffer from unexpected errors, bugs or performance issues.

## Methodology

The main functionality of the tool is divided into three steps:

- **Preprocessing**
    - Aquisition of rail infrastructure data from ISR based on GNSS input.
    - Preprocessing of raw infrastructure data into internal object structure.

- **Map Matching**
    - Map matching algorithm is based on the Hidden-Markov-Model (HMM) of Newson & Krumm [[1]](https://www.ismll.uni-hildesheim.de/lehre/semSpatial-10s/script/6.pdf).
    - Inference of optimal route is performed with the Viterbi algorithm.

- **Postprocessing**
    - Route construction: Concatenation of rails and spline interpolation to yield a smooth route.
    - Coordinate tranformation: Mapping absoulte GNSS coordinates to track coordinates.
    - Route information: Provides infrastructural and operational information about the traveled route.
    - Incline profile: The incline profile for the traveled route, in permil.
    - Height profile: The height profile for the traveled route, in meter above sea level.
    - Velocity profile: The velocity profile for the traveled route, in kilometer per hour.
    - Acceleration profile: The acceleration profile for the traveled rotue, in meter per square second.

The following image provides an overview of the structure of the map matching functionality.

![Structure of the map matching tool](https://github.com/mgillwald/isr_matcher/blob/main/images/Tool.png)
Structure of the map matching tool.

## Results

The map matching results are output to files. Namely, the following result files are created:

- **route/**
    - 000_<first_track_segment>.txt
    - 001_<second_track_segment>.txt
    - ...

    The directory containes the sequence of track segments the train traveled on. Each text file contains the ISR attributes for the respective track segment in JSON format.
- **map.html**

    An HTML-map created with ``folium`` that visualizes the GNSS measurements and map matched route. 
    ![Example of map matching result](images/Example.PNG)
Example of map matching result and visualization.  
- **results.csv**
    
    A CSV-file that contains the main results. The following columns are included: 
    - time: Time stamps.
    - time_from_start_s: Passed time, in seconds.
    - lat_measured: Latitude as measured by GNSS (cs: WGS84).
    - lon_measured: Longitude as measured by GNSS (cs: WGS84).
    - lat_wgs84: Latitude of the map matched coordinate (cs: WGS84).
    - lon_wgs84: Longitude of the map matched coordinate (cs: WGS84).
    - x_epsg31467: Easting of the map matched coordinates (cs: EPSG:31467, as used by ISR).
    - y_epsg31467: Northing of the map matched coordinates (cs: EPSG:31467, as used by ISR).
    - track_number: The four digit DB track number.
    - km: The kilometrage value as float, in kilometer.
    - km_db: The kilometrage value in DB format, [km,hm + m,cm].
    - km_running: The running distance along the traveld route, in kilometer. *This is notably different from the kilometrage. Distance calculations should always use running distances.* 
    - move_direction: Direction of ride in respect to kilometrage (1: direction of increasing kilometrage, 2: direction of decreasing kilometrage).
    - rail_type: 'Richtungsgleis' (Direction Track), 'Gegengleis' (Opposite Track) or 'eingleisig' (monorail).
    - gnss_error_m: Lateral GNSS error, in meter.
    - inclines_promille: Track incline, in permil.
    - altitude_measured_m: Measured altitude, in meter. NaN, if no measurements are available.
    - altitude_computed_m: Computed altitude, in meter.
    - velocity_measured_ms: Measured velocity, in meter per second. NaN, if no measurments are available.
    - velocity_computed_ms: Computed velocity, in meter per second.
    - acceleration_measured_ms2: Measured acceleration, in meter per square second. Nan, if no measurements are available. 
    - acceleration_computed_ms2: Computed acceleration, in meter per square second.

- **path.csv**

   Provides the coordinates of the traveled route in the desired resolution. With the default resolution the path is provided with a spacing of 5 m between coordinates. 
- **incline_and_height_profile.csv**

    Contains the exact incline profile as given by ISR, and the computed height profile. This provides the actual running kilometers, where track incline changes. Therefore, it is a more accurate representation than the instantaneous values contained in results.csv
- **(optional) inclines_permil.png**
- **(optional) altitude_m.png**
- **(optional) velocity_ms.png**
- **(optional) acceleration_ms2.png**

    The profiles can be optionally be plotted with ``matplotlib`` and saved as .png files, as shown below.



    ![Example of map matching result](https://github.com/mgillwald/isr_matcher/blob/main/images/Profiles.png)
Examples for computed route profiles 

## Getting Started

This section gives a short overview of package dependencies and installation.

### Dependencies

The package is supported and tested for python version 3.11.

The package has the following dependencies, which will be installed along the package:

    * folium>=0.15.1,
    * matplotlib>=3.8.2,
    * numpy>=1.26.4,
    * pandas>=2.2.1,
    * pyproj>=3.6.0,
    * pytest>=7.4.3,
    * requests>=2.31.0,
    * scipy>=1.12.0,
    * shapely>=2.0.3,


### Installing

Install the package using pip:

```bash
pip install isr_matcher
```

## Usage

This section details the intended usage of the package. First, it shows how to set up the GNSS input file. Then, the obligatory and optional parameters of the tool are explained. Lastly, examples for the usage of the map matching tool are presented.

### Pre usage: Input

The tool currently only supports inputting GNSS data as CSV files. In order to make the CSV data compatible with the tool, two options are available.

#### Option 1: Use standardized column names

The first option is to rename the columns in you CSV file to standardized names used by the tool. The following lists these standardized column names with a short description of the respective data contained in each column.  

- **latitude**:        column with latitudes (in WGS84 coordinate system)
- **longitude**:       column with longitudes (in WGS84 coordinate system)
- **time_utc**:        column with timestamps 
- **time_s**:          column with passed time in seconds
- **altitude_m**:      column with measured altitudes, in meter
- **velocity_ms**:      column with measured velocity, in meter per second
- **acceleartion_ms**:  column with measured acceleration, in meter per second

The columns **latitude**, **longitude** and *one* time column (either **time_utc** *or* **time_s**) are *at least* required. Altitudes, velocities and accelerations can be included optionally, if they are available. The CSV file can contain further columns, but they are ignored by the tool.

#### Option 2: Use a dictionary mapping column names

The second option is to use a dictionary that maps the column names in your CSV file to the standardized column names. This dictionary can then be passed as a parameter to the map matching function, which avoids manually renaming columns in your input file. An example for how to set up this dictionary is given in the following snippet:

```python
column_name_dict = {
    "latitude": 'column_name_in_csv_file_with_latitudes',                      # obligatory
    "longitude": 'column_name_in_csv_file_with_longitudes',                    # ogligatory
    "time_utc": 'column_name_in_csv_file_with_utc_time_stamps',                # can be None (if time_s is given)
    "time_s": 'column_name_in_csv_file_with_time_in_seconds',                  # can be None (if time_utc is given)
    "altitude_m": 'column_name_in_csv_file_with_measured_altitude',            # can be None (if not available)
    "velocity_ms": 'column_name_in_csv_file_with_measured_velocity',           # can be None (if not available)
    "acceleration_ms2": 'column_name_in_csv_file_with_measured_acceleration',  # can be None (if not available)
}
```


### Pre usage: Parameter settings

The tool allows to control the map matching and analysis task to a certain extent with parameter settings. 

#### Obligatory parameters

- **``export_path``**: ``str`` | ``Path``

    The path to the output directory where results will be written to.    

- **``csv_path``**: ``str`` | ``Path``

    The path to the input CSV file with GNSS measurements.

- **``column_name_dict``**: ``dict`` | ``None``

    A dictionary mapping column names of the input CSV file to standardized names used by the tool. For further description see section **Pre usage: Input** above. If standardized column names are used (option 1), this parameter should be set to ``None``.


#### Optional parameters

- **``r``**: ``float`` = 1500.0

    Determines the boundary around GNSS trajectory for querying infrastructure elements from ISR, in meter.
    Larger values ensure all necessary elements are queried, but increase processing time of the tool and the map matching process. Smaller values speed up this processing, but too small values may lead to missing elements in the query.

- **``sigma``**: ``float`` | ``None`` = None

    The standard deviation of the GNSS error, in meter. If set to ``None``, the standard deviation will be estimated with ``sigma_method``.

    This parameter mainly influences the map matching. For smaller values, the solution will tend to pick rails close to the GNSS measurements, while for larger values the picked rails can be more distant to the measurements.

- **``prune``**: ``Literal['auto']`` | ``float`` | ``None`` = 'auto'

    Controls pruning of GNSS measurments:

    - ``'auto'``: Removes measurements within 2 * ``sigma`` of each other.
    - ``float``: Removes measurements within 2 * ``<float_value>`` of each other.
    - ``None``: No pruning.

    The idea of pruning is taken from [[1]](https://www.ismll.uni-hildesheim.de/lehre/semSpatial-10s/script/6.pdf) and based on the assumption, that for measurements within two times the standard deviation of each other, the confidence is low that the movement originates from an actual movement of the vehicle, and not from noise. Furthermore, it reduces the computational overhead of the map matching algorithm by reducing the number of timesteps.

- **``path_resolution_m``**: ``float`` = 5.0

    Path resolution, in meter. Controls the resolution of the interpolated traveled path, that is the spacing between adjacent path coordinates.

- **``average_low_velocity``**: ``bool`` = True

    If True, averages consecutive measurements with velocity smaller than ``threshold_velocity``. If false, no averaging is performed.

    When the vehicle stands still or moves very slowly, the position can still jump due to GNSS positioning error. Therefore, setting this to True can be useful to mitigate this effect. However, note that this option is only possible if velocity measurements are provided.

- **``threshold_velocity``**: ``float`` = 3.0

    The upper threshold for low velocities that is used when ``average_low_velocity`` is set to True, in meter per second. 

- **``sigma_method``**: ``Literal['mad', 'std']`` = 'mad'

    The method for estimating ``sigma``, if ``sigma`` is set to None. 
    
    - ``'mad'``: Conservative estimate using distance of GNSS measurements to nearest rails and the median absolute deviation (mad) estimator.
    - ``std``: Bold estimate which uses standard deviation instead and includes experimental methods for estimating longitudinal GNSS error besides lateral GNSS error. Can be beneficial if the GNSS error is believed to be very large (e.g. due to tunnel sections.)

- **``create_plots``**: ``bool`` = False

    If True, creates plots of the computed route profiles with ``matplotlib`` and saves them as .png files. If False, no plots are created.

- **``skiprows``**: ``int`` = 0

    Determines if rows should be skipped in the input CSV file. 

- **``correct_velocity``**: ``bool`` = True.

    Determines if the computed velocity should be corrected for track incline. If your velocity measurements are directly from GNSS, it is better to set this to True. For accurate velocity measurements from other sensors, this should be set to False. 

- **``cache_processed_segments``**: ``bool`` = True.

    Determines if preprocessed track segments should be written to cache. Setting this to True significantly speeds up preprocessing the next time the specific track segment is required. Cached track segments can be deleted from cache with the method ``clear_cache`` (see [Example usage](#example-usage)).

### Example usage

#### Minimal working example

The following script demonstrates the basic usage of the tool. The script can be downloaded from [github](https://github.com/mgillwald/isr_matcher/tree/main/examples) along with the (simulated) test data. As the CSV file containing the test data already has correct column names, we set ``column_name_dict = None``.

```python
from isr_matcher import matching
from pathlib import Path

# required parameters
root = Path(__file__).parent.parent          
export_path = root / 'examples/results/'     # change this as needed
csv_path = root / 'examples/test_data.csv'   # change this as needed
column_name_dict = None                      # test data has correct column names

# map matching
matching(
    export_path=export_path,                 
    csv_path=csv_path,                       
    column_name_dict=column_name_dict,       
)
```

#### Extended example with all parameters

An extended example with all parameters explicitly set.

```python
from isr_matcher import matching, clear_cache
from pathlib import Path

# required parameters
root = Path(__file__).parent.parent          
export_path = root / 'examples/results/'     # change this as needed
csv_path = root / 'examples/test_data.csv'   # change this as needed
column_name_dict = None                      # test data has correct column names

# optional parameters (default values)
r = 1500  
sigma = None 
prune = 'auto'                              
path_resolution_m: float = 5.0                
average_low_velocity = True                  
threshold_velocity = 3.0                       
sigma_method = 'mad'                        
create_plots = False                         
skiprows = 0                                 
correct_velocity = True                      
cache_preprocessed_segments = True           

# cache
clear_cache()  # optional, removes all preprocessed track files from cache

# map matching
matching(
    export_path=export_path,                
    csv_path=csv_path,                       
    column_name_dict=column_name_dict,
    r=r,
    sigma=sigma,
    path_resolution_m=path_resolution_m,
    average_low_velocity=average_low_velocity,
    threshold_velocity=threshold_velocity,
    sigma_method=sigma_method,
    create_plots=create_plots,
    skiprows=skiprows,
    correct_velocity=correct_velocity,
    cache_preprocessed_segments=cache_preprocessed_segments,       
)
```

## Help

If you encounter problems or are looking for help, please open an [issue](https://github.com/mgillwald/isr_matcher/issues) or send me a [mail](marco.gillwald@gmx.de).

## Authors

Marco Gillwald ([marco.gillwald@gmx.de](marco.gillwald@gmx.de) / [mgillwald](https://github.com/mgillwald))

## Version History
* 0.0.4
    * Readme updated
    * Minor bug fixes
* 0.0.3
    * Readme updated
    * Example added
    * Updated doc strings
* 0.0.2
    * Readme added
* 0.0.1
    * Initial Release

## Road Map

The main goals that need to be addressed are:

    * Release full Documentation
    * Bug fixes and code optimization
    * Expand testing

Reaching those goals will culminate in the first stable release. Additionally, a small GUI is intended for simple usage and control of features. However, this all depends on how much time I will put into further development in the future.


## License

This project is licensed under the Apache Software License 2.0 - see the LICENSE file for details

## Acknowledgments

This package does not include, but allows to query data from infrastructure registry ([Infrastrukturregister](https://geovdbn.deutschebahn.com/isr)) of Deutsche Bahn.
This package uses kilometrage information from the dataset [Geo-Streckennetz](https://data.deutschebahn.com/dataset/geo-strecke.html) of Deutsche Bahn.
