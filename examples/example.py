from isr_matcher import matching, clear_cache
from pathlib import Path

# fmt: off
# root path
root = Path(__file__).parent.parent

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
average_low_velocity = True                  # averages consecutive measurements with velocity smaller than 'threshold_velocity' (only if velocity measuremnt are available)
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

# fmt: on
