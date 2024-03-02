from __future__ import annotations
import numpy as np
from numpy import newaxis as na
from shapely import Point
from shapely.ops import nearest_points
from isr_matcher.geometry.map import Map
from isr_matcher.geometry.gnss_series import GNSSSeries
from isr_matcher.geometry.rail import Rail
from isr_matcher.ops._functions import angle_between
from isr_matcher._constants._filters import ISR_EXCEPTIONAL_STATION_NAMES
from isr_matcher._constants.logging import setup_logger
import logging

# Create logger for the current module
setup_logger()
logger = logging.getLogger(__name__)


class HMM:
    """TODO"""

    def __init__(self, A_list: list[np.ndarray], B_log: np.ndarray, C_log: np.ndarray):
        self.N = A_list[0].shape[0]  # number of states
        self.M = B_log.shape[1]  # number of observations

        self.A_list = A_list  # list of state transition probability matrices, list of length M, dimension: (N, N)
        self.B_log = B_log  # emission probability matrix,         dimension: (N, M)
        self.C_log = C_log  # initial distribution,                dimension: (N,)

    def solve(self) -> list[int]:
        """Solves HMM for optimal state sequence using Viterbi algorithm (in log-domain).

        Original implementation from: https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S3_Viterbi.html

        Returns
        -------
        S_opt: list[int]
            Optimal state sequence of length M
        """

        N = self.N  # Number of states
        M = self.M  # Number of observations
        A_list = self.A_list  # list of transition matrices (one matrix for each pair of observations)
        B_log = self.B_log  # emission probability matrix (log)
        C_log = self.C_log  # initial state distribution (log)

        # Initialize D and E matrices
        D_log = np.zeros((N, M))
        E = np.zeros((N, M - 1)).astype(np.int32)
        D_log[:, 0] = C_log + B_log[:, 0]

        # Compute D and E in a nested loop
        for t in range(1, M):
            A_log = np.log(A_list[t - 1])  # transition matrix for timestep

            for i in range(N):
                temp_sum = A_log[:, i] + D_log[:, t - 1]
                D_log[i, t] = np.max(temp_sum) + B_log[i, t]
                E[i, t - 1] = np.argmax(temp_sum)

        # Backtracking
        S_opt = np.zeros(M).astype(np.int32)
        S_opt[-1] = np.argmax(D_log[:, -1])
        for t in range(M - 2, -1, -1):
            S_opt[t] = E[int(S_opt[t + 1]), t]

        return S_opt.tolist()

    @classmethod
    def state_transition_matrix_from_map(cls, map_: Map, gnss: GNSSSeries) -> list[np.ndarray]:
        """Computes state transition probability matrix from Map 'map_'."""

        rails = map_['rails']  # all rails in map
        ops = map_['operational_points'] + map_['track_transitions']
        observations = gnss.coords_utm  # observations as sequence of Points
        N = len(rails)  # number of rails (states)
        M = len(observations)  # number of gnss coordinates (observations)
        A_list = []  # list of transition matrices, for each t = 1,...,M (skipping 0)
        dr = 3.1

        # for each observation
        logger.info(f'Computing transition matrices for {M} time steps...')
        for t in range(1, M):
            A = np.zeros((N, N))  # initialize state transition matrix for time step t
            obs_current = observations[t]  # observation at time step t
            obs_previous = observations[t - 1]  # observation at time step t-1

            for i in range(N):
                # for each state / rail, we compute the transition probabilites to all other rails

                rail_i = rails[i]  # current rail
                x_i_current = nearest_points(rail_i, obs_current)[0]  # current obs projected on rail
                x_i_previous = nearest_points(rail_i, obs_previous)[0]  # prev obs projected on rail
                rail_i_start_point = Point(rail_i.coords[0])  # rail start coordinates
                rail_i_end_point = Point(rail_i.coords[-1])  # rail end coordinates

                # distance along rails for projections
                d_x_i_current = rail_i.project(x_i_current, normalized=True)  # distance along rail for current obs
                d_x_i_previous = rail_i.project(x_i_previous, normalized=True)  # distance along rail for prev obs

                # driving direction on rail i (source) based on observations
                if d_x_i_current - d_x_i_previous > 0:
                    driving_direction_i = 1  # driving direction 1 : direction of increasing km
                elif d_x_i_current - d_x_i_previous < 0:
                    driving_direction_i = 2  # driving direction 2 : direction of decreasing km
                else:
                    driving_direction_i = 0  # invalid ( direction not determinable )

                match driving_direction_i:
                    # set end point according to driving direction
                    case 0:
                        end_point = None
                    case 1:
                        end_point = rail_i_end_point
                    case 2:
                        end_point = rail_i_start_point
                    case _:
                        raise NotImplementedError(f'Invalid value for driving direction: {driving_direction_i}')

                if end_point and end_point.distance(x_i_current) < 1:  # transition between rails (current rail ends)
                    for j in range(N):
                        if i == j:
                            continue  # transition between rails, so no transition on same rail
                        if rail_i.distance(rails[j]) > 100.0:
                            continue  # this sets a threshold for the maximum length of a connecting rail!
                        rail_j = rails[j]

                        # allow transition if current rail and target rail are close to the same BS
                        # -> Missing junctions can cause HMM breaks, in stations often many junctions are missing in ISR
                        if rail_i.track != rail_j.track:
                            for op in ops:
                                if op.distance(rail_i) < 20 and op.distance(rail_j) < 20:
                                    connecting_rail = True
                                    reduce_factor = 1e-6
                                    break
                            else:
                                connecting_rail = False
                                reduce_factor = 1.0
                        else:
                            connecting_rail = False
                            reduce_factor = 1.0

                        rail_j_start_point = Point(rail_j.coords[0])  # target rail start point
                        rail_j_end_point = Point(rail_j.coords[-1])  # target rail end point
                        x_j_current = nearest_points(rail_j, obs_current)[0]  # projection on target rail

                        # no transitions to a rail that ends parallel to current rail
                        if driving_direction_i == 1 and (x_j_current == rail_j_end_point):
                            continue
                        elif driving_direction_i == 2 and (x_j_current == rail_j_start_point):
                            continue
                        elif rail_i_end_point == rail_j_end_point:
                            continue

                        # continue if end points are further than dr apart and there is no connecting rail
                        # (reason: if observations are sparse, rails may be skipped)
                        distance = min(end_point.distance([rail_j_start_point, rail_j_end_point]))

                        if connecting_rail == False:
                            for k in range(len(rails)):
                                if i == k or j == k:
                                    continue  # skip identical rail
                                if max(rails[k].distance([rails[i], rails[j]])) > dr:
                                    continue  # if min. distances is greater than dr, k cannot be connecting rail

                                rail_k_start_point = Point(rails[k].coords[0])  # conn. rail start point
                                rail_k_end_point = Point(rails[k].coords[-1])  # conn. rail end point

                                # distance between end points of rail i and rail k < dr
                                distance_ik = end_point.distance([rail_k_start_point, rail_k_end_point])
                                min_index = np.argmin(distance_ik)
                                connection_ik = distance_ik[min_index] < dr
                                if connection_ik == False:
                                    continue

                                # distance between end points of rail k and rail j < dr
                                other_index = int(min_index) - 1  # 0 -> -1, 1 -> 0
                                distance_kj = [rail_k_start_point, rail_k_end_point][other_index].distance(
                                    [rail_j_start_point, rail_j_end_point]
                                )
                                connection_kj = min(distance_kj) < dr
                                if connection_kj == False:
                                    continue

                                # direction vector rail i
                                end_point_arr = np.array([end_point.x, end_point.y])
                                if end_point == rail_i_start_point:
                                    prev_point_arr = np.array([rail_i.coords[1][0], rail_i.coords[1][1]])
                                elif end_point == rail_i_end_point:
                                    prev_point_arr = np.array([rail_i.coords[-2][0], rail_i.coords[-2][1]])
                                else:
                                    raise NotImplementedError()
                                rail_i_direction_vec = end_point_arr - prev_point_arr

                                # direction vector rail k
                                if min_index == 0:
                                    prev_point_arr = np.array([rails[k].coords[1][0], rails[k].coords[1][1]])
                                elif min_index == 1:
                                    prev_point_arr = np.array([rails[k].coords[-2][0], rails[k].coords[-2][1]])
                                else:
                                    raise NotImplementedError()
                                rail_k_direction_vec = prev_point_arr - end_point_arr

                                # angle rail i rail k
                                angle_ik = angle_between(rail_i_direction_vec, rail_k_direction_vec)
                                if angle_ik > 90:
                                    continue  # no connecting rail that would need vehicle to do a u-turn

                                connecting_rail = True
                                break

                            else:
                                connecting_rail = False

                        # continue if end points are further than dr apart and there is no connecting rail
                        if distance > dr and connecting_rail == False:
                            continue

                        # previous code in loop is only to exclude rails to which transitioning does not make sense
                        # at this point, we specify the transition probability between rail i and j (at current time step)
                        # we consider three parameters

                        #   - track number: higher prob. for transitioning to a rail of the same track
                        #                   or at track transitions ('streckenwechsel')

                        transitions = [
                            str(rail_i.track) in tt.name
                            for tt in map_['track_transitions']
                            if tt.distance(rail_j_start_point) < 5
                        ]
                        p_track = 0.8 if rail_i.track == rail_j.track or any(transitions) else 0.2

                        #   - driving direction: higher prob. for transitioning to a rail with same direction (direction 1->2 and 2->1 unlikely)

                        p_direction = 0.9 if driving_direction_i + rail_j.direction != 3 else 0.1

                        #  - distance: higher prob. to transition to closer rails and highest prob. to connected rails or free ends,

                        if all(
                            [
                                min(rail.distance([rail_j_start_point, rail_j_end_point])) > 1
                                for rail in rails
                                if rail != rail_j
                            ]
                        ):
                            distance = 0  # set distance=0 for free ends
                        lambd = 0.5  # parameter
                        p_distance = np.exp(-lambd * distance)  # higher prob. for lower distance

                        # total probability
                        A[i, j] = p_track * p_direction * p_distance * reduce_factor

                else:  # no transition / self-transition
                    # self-transitions are much more common than transitions to other rails
                    # this is especially true for high sample rates
                    # therefore, the probabilites of self-transitions have much more influence
                    # than the probabilities of rail-transitions, which are only punctual
                    # thus, we encode direction information also in the self-transition probabilities,
                    # setting a higher prob. for rail whose direction matches the driving direction

                    ts_name = rail_i.track_segment_name
                    if ts_name.count(' - ') > 1:
                        a, b, c = ts_name.split(' - ')
                        if a + ' - ' + b in ISR_EXCEPTIONAL_STATION_NAMES:
                            from_name = a + ' - ' + b
                            to_name = c
                        else:  # b + ' - ' + c in ISR_EXCEPTIONAL_STATION_NAMES:
                            from_name = a
                            to_name = b + ' - ' + c
                    else:
                        from_name, to_name = ts_name.split(' - ')
                    p_same = (
                        0.5 if 'Hbf' in from_name and 'Hbf' in to_name else 0.9
                    )  # at main stations, ignore rail direction

                    # only allow self transitions
                    if driving_direction_i + rails[i].direction != 3:
                        A[i, i] = p_same  # higher prob. if driving direction matches rail direction
                    else:
                        A[i, i] = 1 - p_same  # lower prob. otherwise
                    # -> NO Normalization (rows)!

            A_list.append(A)  # append to list
        logger.info(f'Transition matrices computed.')
        return A_list

    @staticmethod
    def emission_probabilities(rail: Rail, measurements: list[Point], sigma: float) -> np.ndarray:
        """Computes emission probabilities for state 'rail', observations 'measurements' and standard deviation of GNSS noise 'sigma'."""
        exponent = -0.5 * (rail.distance(measurements) / sigma) ** 2
        return np.exp(exponent) / (np.sqrt(2 * np.pi) * sigma)

    @staticmethod
    def log_emission_probabilities(rail: Rail, measurements: list[Point], sigma: float) -> np.ndarray:
        """Computes emission probabilities for state 'rail', observations 'measurements' and standard deviation of GNSS noise 'sigma' directly in log space.

        Gaussian distribution in log space: log( 1 / (sqrt(2*pi) * sigma) ) - 0.5 (distance / sigma)^2
        """
        return np.log(1 / (np.sqrt(2 * np.pi) * sigma)) - 0.5 * (rail.distance(measurements) / sigma) ** 2

    @classmethod
    def emission_probability_matrix_from_map_and_gnss(cls, map_: Map, gnss: GNSSSeries) -> np.ndarray:
        """Computes emission probability matrix in log-domain from Map 'map_' and GNSS measurements 'gnss'."""

        rails = map_['rails']  # all rails in map
        N = len(rails)  # number of rails (states)
        M = len(gnss)  # number of observations
        B_log = np.zeros((N, M))  # initialize state transition matrix

        # compute and set emission probabilites
        logger.info(f'Computing emission probabilites for {N} rails...')
        for i in range(N):
            B_log[i, :] = HMM.log_emission_probabilities(rail=rails[i], measurements=gnss.coords_utm, sigma=gnss.sigma)  # type: ignore (gnss.sigma is never None at this stage)
            B_log[i, :] = np.where(
                rails[i].distance(gnss.coords_utm) > 500.0, -np.inf, B_log[i, :]
            )  # set emission prob. to 0 for distant rails
        logger.info(f'Emission probabilites computed.')
        return B_log

    @classmethod
    def from_map_and_gnss(cls, map_: Map, gnss: GNSSSeries) -> HMM:
        """Constructs an HMM from a map instance 'map_' and GNSS measurements 'gnss'.

        Parameters
        ----------
        map_: Map
            Instance of class Map (TypedDict with keys 'track_segments', 'operational_points' and 'rails').
        gnss: GNSSSeries
            Instance of class GNSSSeries, representing the measured GNSS parameters (lat, lon, utm coordinates, velocity, etc.).

        Returns
        -------
        hmm: HMM
            A new instance of HMM with parameters (A, B, C) computed from 'map_' and GNSS measurements 'gnss'.
        """

        # compute HMM parameter
        A_list = cls.state_transition_matrix_from_map(map_=map_, gnss=gnss)
        B_log = cls.emission_probability_matrix_from_map_and_gnss(map_=map_, gnss=gnss)
        C_log = B_log[:, 0]

        return cls(A_list, B_log, C_log)
