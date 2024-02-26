from __future__ import annotations
from isr_matcher.data_handlers.gnss_data_import import GNSSDataImport
from isr_matcher.map_matching.isr_matcher import ISRMatcher
from pathlib import Path
from typing import Literal


def matching(
    export_path: Path | str,  # path to export directory (where results will be written)
    csv_path: Path | str,  # path to input csv file with gnss times and coordinates
    column_name_dict: dict,  # specifies the column names of the input csv file
    r: float = 1500.0,  # search radius around gnss measurements
    sigma: float | None = None,  # estimate of the gnss error (standard deviation)
    prune: Literal['auto'] | float | None = 'auto',  # pruning strategy for input gnss trajectory
    average_low_velocity: bool = True,  # averages measurement points with low velocity (only if velocity measurements are available)
    threshold_velocity: float = 3,  # threshold for averaging by velocity, in meter per second. Consecutive points with lower velocity than threshold will be averaged.
    sigma_method: Literal['mad', 'std'] = 'mad',  # method for estimating sigma, if sigma is not given
    create_plots: bool = False,  # if plots for velocity, acceleration, incline and height profiles are to be created (requires matplotlib)
    skiprows: int = 0,  # sets number of rows to skip from start of input csv file
    correct_velocity: bool = True,  # if computed velocity should be corrected for track incline
) -> None:
    """The main function of the package. Performs map matching and post-analysis. Results are written to directory specified by 'export_path'.

    Parameters
    ----------
    export_path: Path | str
        String or Path to the directory where results will be written to.
    csv_path: Path | str
        String or Path to the csv file with gnss measurements. The file must at least contain columns with latitude and lognitude as well as a time column.
    column_name_dict: dict
        A dictionary specifying the available data in the csv file. The format of the dictionary is as follows:

            example_dict: {
                "time_utc": <column_name_in_csv_file_with_utc_time_stamps>,
                "time_s": <column_name_in_csv_file_with_time_in_seconds>,
                "latitude": <column_name_in_csv_file_with_latitudes>,
                "longitude": <column_name_in_csv_file_with_longitudes>,
                "altitude_m": <column_name_in_csv_file_with_measured_altitude>,
                "velocity_ms": <column_name_in_csv_file_with_measured_velocity>,
                "acceleration_ms2": <column_name_in_csv_file_with_measured_acceleration>,
            }

        The name of latitude, longitude and of one time column must be given. The rest (inclduing one time column) can be set to None, if the corrsponding information is missing in the input file.
    r: float = 1500
        Optional. Defines the search radius around the input gnss trajectory, in meter. All elements in this radius will be queried from ISR. If not set, this defaults to 1.5 km.
    sigma: float | None = None
        Optional. Estimate of the gnss error, meaning the standard deviation of gnss measurements. If not set, this defaults to estimating the gnss error with the method given by 'sigma_method'.
    prune: Literal['auto'] | float | None = 'auto'
        Optional. Sets the strategy for pruning input gnss measurements. If 'auto', it prunes points within 2*sigma of the previous point. If a float, the float defines the pruning radius in meter. If None, no pruning is performed.
    average_low_velocity: bool = True
        Sets whether points with low velocity should be averaged. Defaults to True.
    threshold_velocity: float = 3,
        Threshold for averaging by velocity, in meter per second. Consecutive points with lower velocity than threshold will be averaged.
    sigma_method: Literal['mad', 'std'] = 'mad',
        Method for estimating sigma, if sigma is not given. Can be 'mad' (median absoulte deviation) or 'std' (standard deviation). With 'mad', sigma is underestimated which gives moderate estimates. With 'std', estimates are higher as a forward error component is included, which is sampled from a distribution. This can lead to very high estimates.
    create_plots: bool = False,
        If plots for velocity, acceleration, incline and height profiles are to be created (requires matplotlib).
    skiprows: int = 0,
        Sets number of rows to skip from start of input csv file.
    correct_velocity: bool = True
        Sets if the computed velocities should be corrected for track incline. Defaults to True.

    Raises
    ------
    ValueError: If an error occurs during the map matching process.
    """

    # instantiate
    gdi = GNSSDataImport()

    # read csv file
    gnss_series = gdi.read_csv(csv_path=csv_path, column_name_dict=column_name_dict, skiprows=skiprows)

    # MMpreprocessor
    isr_matcher = ISRMatcher(
        gnss_series=gnss_series,
        export_path=export_path,
        export_results=True,
        r_boundary=r,
        r_candidates=200,
    )

    # ISR Map Matching
    try:
        return_code = isr_matcher.match(
            sigma=sigma,
            prune=prune,
            average_low_velocity=average_low_velocity,
            threshold_velocity=threshold_velocity,
            sigma_method=sigma_method,
            create_plots=create_plots,
            correct_velocity=correct_velocity,
        )
    except:
        return_code = -1

    if return_code != 0:
        raise ValueError(
            'An error orcurred during the map matching process. Results could not be obtained. This may be due to bad input or an implementation error. Please note the tool is still in development and can produce erros.'
        )

    print(f'Map Matching successful. Results have been written to {export_path}')
    return
