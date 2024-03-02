from isr_matcher.geometry.gnss_series import GNSSSeries
from isr_matcher.geometry.track_segment import TrackSegment
from isr_matcher.geometry.operational_point import OperationalPoint
from isr_matcher.geometry.rail import Rail
from isr_matcher.geometry.map import Map
from isr_matcher.ops._preprocessing import MMPreprocessor
from isr_matcher.ops._postprocessing import MMPostprocessor
from isr_matcher.data_handlers.rail_data_import import RailDataImport
from isr_matcher.map_matching.hmm import HMM
from pathlib import Path
import pickle
from typing import Literal
from numpy.typing import ArrayLike
import pandas as pd
import numpy as np
from typing import Tuple
import json
from shapely import Point
from isr_matcher.data_handlers.transformer import Transformer
import folium
from isr_matcher._constants.logging import setup_logger
import logging

# Create logger for the current module
setup_logger()
logger = logging.getLogger(__name__)


# ISR Map Matching class
class ISRMatcher:
    """Class that handles map matching of GNSS time series to ISR map data.

    This is a high-level class leveraging several other classes to handle the whole map matching process. It wraps and handles GNSS and map preprocessing (MMPreprocessor), map matching (HMM), and post-analysis (TBD).

    Attributes
    ----------
    _project_path : Path
        Path to the root of the project.
    _r_boundary : float
        Radius for boundary.
    _r_candidates : float
        Radius for rail candidates (around each measurement point).
    export_path : Path
        Path to export the results.
    export_results : bool
        Determines whether to export the results.
    _preprocessor : MMPreprocessor
        Preprocessor instance for map and GNSS data.
    _postprocessor : MMPostprocessor
        Postprocessor instance for map data.
    """

    def __init__(
        self,
        gnss_series: GNSSSeries,
        export_path: Path | str | None,
        r_boundary: float = 1500.0,
        r_candidates: float = 200.0,
        export_results: bool = True,
        enhance_kilometrage: bool = True,
        cache_preprocessed_segments: bool = True,
    ):
        """Initializes the ISRMatcher class.

        Parameters
        ----------
        gnss_series : GNSSSeries
            The GNSS time series data.
        export_path : Path | str | None
            Path to export the results.
        r_boundary : float, optional
            Radius for boundary, by default 1500.0.
        r_candidates : float, optional
            Radius for rail candidates (around each measurement point), by default 200.0.
        export_results : bool, optional
            Determines whether to export the results, by default True.
        enhance_kilometrage : bool, optional
            Determines whether to enhance kilometrage, by default True.
        cache_preprocessed_segments : bool, optional
            Determines whether to cache preprocessed segments, by default True.
        """

        self._project_path = Path(__file__).parent.parent.parent.parent  # path to root of project
        self._r_boundary = r_boundary  # radius for boundary
        self._r_candidates = r_candidates  # radius for rail candidates (around each measurment point)
        self.query_map(
            gnss=gnss_series,
            enhance_kilometrage=enhance_kilometrage,
            cache_preprocessed_segments=cache_preprocessed_segments,
        )  # query map and set self._map
        self._preprocessor = MMPreprocessor(  # create preprocessor instance
            map_data=self.map,
            gnss=gnss_series,
            r=self.r_candidates,
        )
        self._postprocessor = MMPostprocessor(map_=self.map)
        if export_results == True:
            if export_path:
                self.export_path = Path(export_path)
                self.export_path.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError("Option 'export_results' is set to True but no 'export_path' was given.")
        self.export_results = export_results

    @property
    def r_boundary(self) -> float:
        """Returns the search radius for map elements."""
        return self._r_boundary

    @property
    def r_candidates(self) -> float:
        """Returns the search radius around gnss measurements for candidate rails."""
        return self._r_candidates

    @property
    def gnss(self) -> GNSSSeries:
        """Returns the GNSS Series."""
        return self.preprocessor.gnss

    @property
    def map(self) -> Map:
        """Returns the map (list of all elements)."""
        return self._map

    @property
    def project_path(self) -> Path:
        """Returns the path to the root of the project."""
        return self._project_path

    @property
    def preprocessor(self) -> MMPreprocessor:
        """Returns the preprocessor instance."""
        return self._preprocessor

    @property
    def postprocessor(self) -> MMPostprocessor:
        """Returns the postprocessor instance."""
        return self._postprocessor

    def query_map(self, gnss: GNSSSeries, enhance_kilometrage: bool = True, cache_preprocessed_segments: bool = True):
        """
        Query ISR for all elements within a boundary around GNSS measurements.

        Returns
        -------
        map_data: list[TrackSegment | OperationalPoint]
            All elements within search radius r of gnss series.
        """
        # boundary as string (LinearRing)
        boundary_string = gnss.boundary_string(r=self.r_boundary)

        # query map data
        rdi = RailDataImport()
        logger.info('Querying ISR for all elements in boundary...')
        map_data = rdi.query(
            filter_name='BOUNDARY',
            args=[boundary_string],
            enhance_kilometrage=enhance_kilometrage,
            cache_preprocessed_segments=cache_preprocessed_segments,
        )

        # set map attribute
        self._map = ISRMatcher._map_data_to_map(map_data=map_data)

        logger.info('Preprocessing track segments complete.')

    def preprocess_map(self):
        """Preprocesses map."""

        # set bi-directional rails
        # self._map = self.preprocessor.set_bidirectional_rails()

        # split rails at switch zones
        self._map = self.preprocessor.split_rails_at_switch_zones()

        # set index of rails
        self._map = self.preprocessor.index_rails()

    def preprocess_gnss(
        self,
        sigma: float | ArrayLike | None = None,
        sigma_method: Literal['std'] | Literal['mad'] = 'std',
        prune: float | Literal['auto'] | None = None,
        average_low_velocity: bool = True,
        threshold_velocity: float = 3.0,
    ):
        """Preprocesses GNSS series.

        Parameters
        ----------
        sigma : float | ArrayLike | None, optional
            Standard deviation of the noise. If None, it will be estimated, by default None.
        sigma_method : {'std', 'mad'}, optional
            Method to estimate sigma, by default 'std'.
        prune : float | {'auto'} | None, optional
            Prune parameter, by default None.
        average_low_velocity : bool, optional
            Determines whether to average low velocity measurements, by default True.
        threshold_velocity : float, optional
            Threshold velocity, by default 3.0.
        """

        # average low velocity measurement
        if average_low_velocity and not isinstance(self.gnss.velocity_ms, type(None)):
            velocity_ms = self.gnss.velocity_ms
            # if more than 10 timesteps remain
            if len(np.where(velocity_ms > threshold_velocity)[0]) > 10:
                self.preprocessor.average(threshold=threshold_velocity)

        # prune measurements
        match prune:
            case 'auto':
                # remove points within 2 * sigma of last included point,
                # where sigma is an estimate of the GNSS noise
                self.preprocessor.prune(r=None, sigma_method=sigma_method)

            case None:
                self.preprocessor.prune(r=0, sigma_method=sigma_method)

            case _:  # float
                self.preprocessor.prune(r=prune, sigma_method=sigma_method)

        # gnss noise
        if not sigma:
            sigma = self.preprocessor.estimate_gnss_noise(method=sigma_method)
        self.preprocessor.gnss._sigma = sigma  # type: ignore

    def match(
        self,
        sigma: float | ArrayLike | None = None,
        prune: float | Literal['auto'] | None = None,
        sigma_method: Literal['std'] | Literal['mad'] = 'std',
        path_resolution_m: float = 5,
        average_low_velocity: bool = True,
        threshold_velocity: float = 3.0,
        correct_velocity: bool = True,
        create_plots: bool = True,
    ) -> int:
        """Matches GNSS data to the map and computes various parameters.

        This method preprocesses the GNSS series and map data, constructs a Hidden Markov Model based on the preprocessed data, computes the optimal state sequence, and then computes various parameters such as position, incline, height, velocity, and acceleration profiles. It also exports the results to CSV files and generates plots if specified.

        Parameters
        ----------
        sigma : float | ArrayLike | None, optional
            Standard deviation of the noise, by default None.
        prune : float | {'auto'} | None, optional
            Prune parameter, by default None.
        sigma_method : {'std', 'mad'}, optional
            Method to estimate sigma, by default 'std'.
        path_resolution_m : float, optional
            Spacing between points of computed path of train in meter, by default 5.
        average_low_velocity : bool, optional
            Determines whether to average low velocity measurements, by default True.
        threshold_velocity : float, optional
            Threshold velocity, by default 3.0.
        correct_velocity : bool, optional
            Determines whether to correct velocity, by default True.
        create_plots : bool, optional
            Determines whether to create plots, by default True.

        Returns
        -------
        int
            Returns 0 upon successful completion.
        """

        logger.info('Preprocessing GNSS series...')
        # preprocess: gnss
        self.preprocess_gnss(
            sigma=sigma,
            prune=prune,
            sigma_method=sigma_method,
            average_low_velocity=average_low_velocity,
            threshold_velocity=threshold_velocity,
        )

        logger.info('Preprocessing GNSS complete.')

        import matplotlib.pyplot as plt

        f, ax = plt.subplots(1, 1)
        line = self.gnss.line_utm
        for p in self.gnss.coords_utm:
            ax.scatter(p.x, p.y, color='k')
        ax.plot(*line.xy, color='k', alpha=0.4)
        plt.savefig(self.export_path / 'input_pruned.png')
        plt.close()

        logger.info('Preprocessing map...')
        # preprocess: map
        # set rail directions
        # split rails at switch zones
        self.preprocess_map()
        logger.info('Preprocessing map complete')

        logger.info('Constructing HMM...')
        # construct hmm  | HMM input: preprocessed map, pre processed gnss
        hmm = HMM.from_map_and_gnss(map_=self.map, gnss=self.gnss)
        self.hmm = hmm
        logger.info('Constructing HMM complete.')

        logger.info('Computing optimal state sequence...')
        # solve hmm with viterbi
        S = hmm.solve()  # S: optimal state sequence

        # check if a solution was found
        assert not all(
            [s == 0 for s in S]
        ), f'Map Matching Solution could not be found, probably due to bad or sparse input.'
        logger.info('Successfully computed optimal state sequence.')

        # compute tentative path
        logger.info('Computing path...')
        path = self.postprocessor.concatenate_rails(
            S=S, start_point=self.gnss.coords_utm[0], end_point=self.gnss.coords_utm[-1]
        )
        rail_sequence = [self.map['rails'][i] for i in S]

        # compute positional parameters
        position_dict = self.postprocessor.compute_position_parameter(
            path=path,
            rail_sequence=rail_sequence,
            gnss_coords=self.gnss.coords_utm,
        )

        # prune timesteps with wrong direction (direction changes for a single timestep)
        position_dict, S = self.prune_timesteps_with_wrong_direction(position_dict=position_dict, S=S)
        rail_sequence = [self.map['rails'][i] for i in S]
        # recompute path
        path = self.postprocessor.concatenate_rails(
            S=S, start_point=self.gnss.coords_utm[0], end_point=self.gnss.coords_utm[-1], resolution_m=path_resolution_m
        )

        # compute track semgen sequence corresponding to rail sequence
        track_segment_sequence, track_segment_indices = self.postprocessor.compute_track_segment_sequence(
            rail_sequence=rail_sequence
        )
        logger.info('Path computation completed.')

        # incline profile (from ISR)
        logger.info('Computing incline and height profile...')
        incline_profile = self.postprocessor.compute_incline_profile(
            path=path,
            gnss_coords_utm=self.gnss.coords_utm,
            track_segment_sequence=track_segment_sequence,
            track_segment_indices=track_segment_indices,
            rail_sequence=rail_sequence,
            position_dict=position_dict,
        )

        # compute_height_profile (from ISR inclines)
        profiles = self.postprocessor.compute_height_profile(
            incline_profile=incline_profile, track_segment_sequence=track_segment_sequence
        )
        logger.info('Incline and height profile completed.')

        logger.info('Computing veclocity profile...')
        # compute velocity_profile
        velocity_kmh = self.postprocessor.velocity_from_gnss(
            kms_running=position_dict['kms_running'],
            gnss=self.gnss,
            incline_profile=profiles,
            correct_velocity=correct_velocity,
        )
        velocity_ms = np.array(velocity_kmh) / 3.6
        logger.info('Veclocity profile completed.')

        logger.info('Computing acceleration profile....')
        # compute acceleartion_profile
        acceleration_ms2 = self.postprocessor.acceleration_from_gnss_and_velocity(
            gnss=self.gnss, velocity_ms=velocity_ms.tolist()
        )
        # acceleration from measured velocity (if no measured acceleration)
        if isinstance(self.gnss.acceleration_ms2, type(None)) and not isinstance(self.gnss.velocity_ms, type(None)):
            acceleration_from_measured_velocity_ms2 = self.postprocessor.acceleration_from_gnss_and_velocity(
                gnss=self.gnss, velocity_ms=self.gnss.velocity_ms.tolist()
            )
            self.gnss._acceleration_ms2 = np.array(acceleration_from_measured_velocity_ms2)
        logger.info('Acceleration profile completed.')

        logger.info(f'Writing results to: {self.export_path}.')
        # create result dataframe
        df_dict = {
            'time': self.gnss.time,
            'time_from_start_s': self.gnss.time_s,
            'lat_measured': self.gnss.latitude,
            'lon_measured': self.gnss.longitude,
            'lat_wgs84': [point.x for point in position_dict['matched_coordinates_wgs']],
            'lon_wgs84': [point.y for point in position_dict['matched_coordinates_wgs']],
            'x_epsg31467': [point.x for point in position_dict['matched_coordinates_utm']],
            'y_epsg31467': [point.y for point in position_dict['matched_coordinates_utm']],
            'track_number': position_dict['track_numbers'],
            'km': position_dict['kms'],
            'km_db': position_dict['kms_db'],
            'km_running': position_dict['kms_running'],
            'move_direction': position_dict['directions'],
            'rail_type': position_dict['rail_types'],
            'gnss_error_m': position_dict['gnss_error_m'],
            'inclines_promille': position_dict['inclines'],
            'altitude_measured_m': self.gnss.altitude_m
            if not isinstance(self.gnss.altitude_m, type(None))
            else len(self.gnss) * [np.nan],
            'altitude_computed_m': np.interp(x=position_dict['kms_running'], xp=profiles['kms'], fp=profiles['height']),
            'velocity_measured_ms': self.gnss.velocity_ms
            if not isinstance(self.gnss.velocity_ms, type(None))
            else len(self.gnss) * [np.nan],
            'velocity_computed_ms': velocity_ms,
            'acceleration_measured_ms2': self.gnss.acceleration_ms2
            if not isinstance(self.gnss.acceleration_ms2, type(None))
            else len(self.gnss) * [np.nan],
            'acceleration_computed_ms2': acceleration_ms2,
        }
        df_results = pd.DataFrame(data=df_dict)
        if self.export_results == True:
            df_results.to_csv(self.export_path / 'results.csv')

        # data frame with incline profile
        # 2 columns: running km and incline
        df_incline_and_height_profile = pd.DataFrame(data=profiles)
        df_incline_and_height_profile = df_incline_and_height_profile.drop_duplicates(subset=['inclines', 'kms'])
        if self.export_results == True:
            df_incline_and_height_profile.to_csv(self.export_path / 'incline_and_height_full_profile.csv')

        # data frame with path coordinates
        # projection of matched point (utm to wgs)
        transformer = Transformer(source_cs='epsg:31467', target_cs='epsg:4326')
        path_points_wgs = []
        path_points_utm = []
        lat_wgs84 = []
        lon_wgs84 = []
        x_31467 = []
        y_31467 = []
        for path_coord_utm in path.coords[:]:
            point_utm = Point([path_coord_utm[0], path_coord_utm[1]])
            path_coord_wgs = transformer.transform('source_to_target', Point([path_coord_utm[1], path_coord_utm[0]]))
            path_points_wgs.append(Point(path_coord_wgs))
            path_points_utm.append(point_utm)
            lat_wgs84.append(path_coord_wgs.x)
            lon_wgs84.append(path_coord_wgs.y)
            x_31467.append(point_utm.x)
            y_31467.append(point_utm.y)
        path_running_km = np.around(path.project(path_points_utm) / 1000, 3)
        dict_path = {
            'running_km': path_running_km,
            'lat_wgs84': lat_wgs84,
            'lon_wgs84': lon_wgs84,
            'x_epsg31467': x_31467,
            'y_epsg31467': y_31467,
        }
        df_path = pd.DataFrame(data=dict_path)
        if self.export_results == True:
            df_path.to_csv(self.export_path / 'path.csv')

        # write route information
        route_dir = self.export_path / 'route'
        route_dir.mkdir(parents=True, exist_ok=True)
        route_dict = {}
        for i, idx in enumerate(track_segment_indices):
            # track segments in sequence with corresponding rail
            rail = rail_sequence[idx]
            track_segment = track_segment_sequence[i]

            # get ISR properties
            if rail.direction == 0 or rail.direction == 1:
                properties = track_segment.properties
            elif rail.direction == 2:
                properties = track_segment.properties_2
            else:
                raise ValueError(f'Received unknown rail direction: {rail.direction}')

            # write to file
            if i < 10:
                prefix = '00'
            elif i < 100:
                prefix = '0'
            else:
                prefix = ''

            if self.export_results == True:
                filepath = route_dir / f'{prefix}{i}_{track_segment.track_nr}_{track_segment.name}.txt'
                with open(filepath, 'w') as file:
                    file.write(json.dumps(properties))
            else:
                route_dict[f'{prefix}{i}_{track_segment.track_nr}_{track_segment.name}'] = properties

        # create plots
        if create_plots == True and self.export_results == True:
            import matplotlib.pyplot as plt

            # velocity
            plt.style.use("ggplot")
            f, ax = plt.subplots(1, 1, dpi=200)
            ax.plot(position_dict['kms_running'], velocity_kmh, label='Berechnung')
            ax.plot(position_dict['kms_running'], self.gnss.velocity_ms * 3.6, label='Messung')
            ax.set_xlabel('Fahrweg [km]')
            ax.set_ylabel('Geschwindigkeit [km/h]')
            ax.legend()
            plt.savefig(self.export_path / 'velocity_ms.png')
            plt.close()

            # inclines
            plt.style.use("ggplot")
            f, ax = plt.subplots(1, 1, dpi=200)
            kms = profiles['kms']
            inclines = profiles['inclines']
            for i in range(len(kms) - 1):
                ax.hlines(inclines[i], kms[i], kms[i + 1])
                ax.vlines(kms[i + 1], inclines[i], inclines[i + 1])

            ax.set_xlabel('Fahrweg [km]')
            ax.set_ylabel('Steigung [‰]')
            plt.savefig(self.export_path / 'inclines_promille.png')
            plt.close()

            # height
            plt.style.use("ggplot")
            f, ax = plt.subplots(1, 1, dpi=200)

            kms = profiles['kms']
            h = profiles['height']
            ax.plot(kms, h)

            ax.set_xlabel('Fahrweg [km]')
            ax.set_ylabel('Höhe [m]')
            plt.savefig(self.export_path / 'altitude_m.png')
            plt.close()

            # acceleration
            plt.style.use("ggplot")
            f, ax = plt.subplots(1, 1, dpi=200)
            ax.plot(position_dict['kms_running'], acceleration_ms2, label='Berechnung')
            if not isinstance(self.gnss.acceleration_ms2, type(None)):
                ax.plot(
                    position_dict['kms_running'],
                    self.gnss.acceleration_ms2,
                    label='Abgeleitet von Geschwindigkeitsmessung',
                )
            ax.set_xlabel('Fahrweg [km]')
            ax.set_ylabel('Beschleunigung [m/s^2]')
            ax.legend()
            plt.savefig(self.export_path / 'acceleration_ms2.png')
            plt.close()

        # folium map
        m = MMPostprocessor.map_matching_results_to_map(
            df=df_results, export_path=self.export_path, df_path=df_path, map_=self.map, return_map=True
        )
        folium.LayerControl().add_to(m)
        m.save(self.export_path / f'map.html')  # save map

        logger.info(f'Results written to: {self.export_path}.')

        return 0

    def prune_timesteps_with_wrong_direction(self, position_dict: dict, S: list[int]) -> Tuple[dict, list[int]]:
        """Prunes timesteps with direction error."""

        # identify direction errors (direction changes for a single timestep)
        directions = position_dict['directions']
        index = []
        for i, d in enumerate(directions):
            if i == 0:
                if directions[0] != directions[1]:
                    index.append(0)
            elif i == len(directions) - 1:
                if directions[-1] != directions[-2]:
                    index.append(len(directions) - 1)
            else:
                if directions[i] != directions[i - 1] and directions[i] != directions[i + 1]:
                    index.append(i)

        # prune every attribute at timesteps given by index
        self.gnss.prune(r=0, index=index)  # prune points where direction changes for one meausrement only
        position_dict = self.prune_position_dict(position_dict=position_dict, index=index)
        S = [s for i, s in enumerate(S) if not (i in index)]

        return position_dict, S

    @staticmethod
    def prune_position_dict(position_dict: dict, index: list[int]) -> dict:
        """Prunes entries on position dict according to index.

        Parameters
        ----------
        position_dict : dict
            Dictionary containing positional data.
        index : list[int]
            List of indices to prune.

        Returns
        -------
        dict
            Pruned position dictionary.
        """

        for key in position_dict.keys():
            position_dict[key] = np.delete(position_dict[key], index)

        return position_dict

    @staticmethod
    def _map_data_to_map(map_data: list[TrackSegment | OperationalPoint]) -> Map:
        """Function that transforms map data as returned by RailDataImport to a typed dict.

        Parameters
        ----------
        map_data: list[TrackSegment | OperationalPoint]
            List of map elements.

        Returns
        -------
        map_: Map
            Typed dictionary (Map) of map elements, keys: 'track_segments', 'operational_points', 'rails'.
        """

        # parse elements
        track_segments = []
        operational_points = []
        rails = []
        track_transitions = []

        for element in map_data:
            if element.element_type == 'TrackSegment':
                track_segments.append(element)  # append track segment
                rails += element.rails  # append rails

            elif element.element_type == 'OperationalPoint':
                operational_points.append(element)  # append operational points

                if 'StrUeb' in element.name:
                    track_transitions.append(element)

            else:
                raise ValueError(f'Unknown element type: {element.element_type}')

        # create map (typed dict)
        map_: Map = {
            'track_segments': track_segments,
            'operational_points': operational_points,
            'rails': rails,
            'track_transitions': track_transitions,
        }

        return map_

    def _find_track_segment_for_rail(self, rail: Rail) -> TrackSegment:
        """
        Searches for the track segment the rail belongs to in cache and if available, unpickles and returns TrackSegment instance.

        This method should only be called after map matching has been conducted, because then the TrackSegment is definetely in cache.

        Parameters
        ----------
        rail: Rail
            An instance of Rail class.

        Returns
        -------
        track_segment: TrackSegment
            The TrackSegment instance the rail belongs to.
        """

        file_path = self.project_path / f'{rail.track}_{rail.track_segment_name}.pickle'
        if file_path.exists() and file_path.suffix == '.pickle':
            with open(file_path, "rb") as file:
                track_segment: TrackSegment = pickle.load(file)

            return track_segment

        else:
            raise ValueError(f'Given filepath does not exist or does not point to a pickle file: {file_path}')
