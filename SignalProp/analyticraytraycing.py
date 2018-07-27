from __future__ import absolute_import, division, print_function
import numpy as np
import matplotlib.pyplot as plt
import time
from scipy.optimize import fsolve, minimize, basinhopping, root
from scipy import optimize, integrate, interpolate
import scipy.constants
from NuRadioMC.utilities import units
import logging
"""
analytic ray tracing solution
"""
speed_of_light = scipy.constants.c * units.m / units.s


class ray_tracing_2D():

    def __init__(self, medium, log_level=logging.WARNING):
        self.medium = medium
        self.__b = 2 * self.medium.n_ice
        self.__logger = logging.getLogger('ray_tracing_2D')
        self.__logger.setLevel(log_level)

    def n(self, z):
        """
        refractive index as a function of depth
        """
        res = self.medium.n_ice - self.medium.delta_n * np.exp(z / self.medium.z_0)
    #     if(type(z) is float):
    #         if(z > 0):
    #             return 1.
    #         else:
    #             return res
    #     else:
    #         res[z > 0] = 1.
        return res

    def get_gamma(self, z):
        return self.medium.delta_n * np.exp(z / self.medium.z_0)

    def get_turning_point(self, c):
        """
        calculate the turning point, i.e. the maximum of the ray tracing path
        """
        gamma2 = self.__b * 0.5 - (0.25 * self.__b ** 2 - c) ** 0.5  # first solution discarded
        z2 = np.log(gamma2 / self.medium.delta_n) * self.medium.z_0
        return gamma2, z2

    def get_C_1(self, x1, C_0):
        """
        calculates constant C_1 for a given C_0 and start point x1
        """
        return x1[0] - self.get_y_with_z_mirror(x1[1], C_0)

    def get_c(self, C_0):
        return self.medium.n_ice ** 2 - C_0 ** -2

    def get_C0_from_log(self, logC0):
        """
        transforms the fit parameter C_0 so that the likelihood looks better
        """
        return np.exp(logC0) + 1. / self.medium.n_ice

    def get_y(self, gamma, C_0, C_1):
        """
        analytic form of the ray tracing part given an exponential index of refraction profile

        Parameters
        -------
        gamma: (float or array)
            gamma is a function of the depth z
        C_0: (float)
            first parameter
        C_1: (float)
            second parameter
        """
        c = self.medium.n_ice ** 2 - C_0 ** -2
        root = np.abs(gamma ** 2 - gamma * self.__b + c)  # we take the absolute number here but we only evaluate the equation for positive outcome. This is to prevent rounding errors making the root negative
        logargument = gamma / (2 * c ** 0.5 * (root) ** 0.5 - self.__b * gamma + 2 * c)
        if(np.sum(logargument <= 0)):
            self.__logger.debug('log = ', logargument)
        result = self.medium.z_0 * (self.medium.n_ice ** 2 * C_0 ** 2 - 1) ** -0.5 * np.log(logargument) + C_1
        return result

    def get_y_diff(self, z_raw, C_0):
        """
        derivative dy(z)/dz
        """
        z = self.get_z_unmirrored(z_raw, C_0)
        c = self.medium.n_ice ** 2 - C_0 ** -2
        res = (-np.sqrt(c) * np.exp(z / self.medium.z_0) * self.__b * self.medium.delta_n + 0.2e1 * np.sqrt(-self.__b * self.medium.delta_n * np.exp(z / self.medium.z_0) + self.medium.delta_n ** 2 * np.exp(0.2e1 * z / self.medium.z_0) + c) * c + 0.2e1 * c ** (0.3e1 / 0.2e1)) / (0.2e1 * np.sqrt(c) * np.sqrt(-self.__b * self.medium.delta_n * np.exp(z / self.medium.z_0) + self.medium.delta_n ** 2 * np.exp(0.2e1 * z / self.medium.z_0) + c) - self.__b * self.medium.delta_n * np.exp(z / self.medium.z_0) + 0.2e1 * c) * (-self.__b * self.medium.delta_n * np.exp(z / self.medium.z_0) + self.medium.delta_n ** 2 * np.exp(0.2e1 * z / self.medium.z_0) + c) ** (-0.1e1 / 0.2e1) * ((self.medium.n_ice ** 2 * C_0 ** 2 - 1) ** (-0.1e1 / 0.2e1))

        if(z != z_raw):
            res *= -1
        return res

    def get_y_with_z_mirror(self, z, C_0, C_1=0):
        """
        analytic form of the ray tracing part given an exponential index of refraction profile

        this function automatically mirrors z values that are above the turning point,
        so that this function is defined for all z

        Parameters
        -------
        z: (float or array)
            depth z
        C_0: (float)
            first parameter
        C_1: (float)
            second parameter
        """
        c = self.medium.n_ice ** 2 - C_0 ** -2
        gamma_turn, z_turn = self.get_turning_point(c)
        if(z_turn >= 0):
            # signal reflected at surface
            self.__logger.debug('signal reflects off surface')
            z_turn = 0
            gamma_turn = self.get_gamma(0)
        y_turn = self.get_y(gamma_turn, C_0, C_1)
        if(type(z) == float or (type(z) == int) or (type(z) == np.float64)):
            if(z < z_turn):
                gamma = self.get_gamma(z)
                return self.get_y(gamma, C_0, C_1)
            else:
                gamma = self.get_gamma(2 * z_turn - z)
                return 2 * y_turn - self.get_y(gamma, C_0, C_1)
        else:
            mask = z < z_turn
            res = np.zeros_like(z)
            zs = np.zeros_like(z)
            gamma = self.get_gamma(z[mask])
            zs[mask] = z[mask]
            res[mask] = self.get_y(gamma, C_0, C_1)
            gamma = self.get_gamma(2 * z_turn - z[~mask])
            res[~mask] = 2 * y_turn - self.get_y(gamma, C_0, C_1)
            zs[~mask] = 2 * z_turn - z[~mask]

            self.__logger.debug('turning points for C_0 = {:.2f}, b= {:.2f}, gamma = {:.4f}, z = {:.1f}, y_turn = {:.0f}'.format(C_0, self.__b, gamma_turn, z_turn, y_turn))
            return res, zs

    def get_z_mirrored(self, x1, x2, C_0):
        """
        calculates the mirrored x2 position so that y(z) can be used as a continuous function
        """
        c = self.medium.n_ice ** 2 - C_0 ** -2
        C_1 = x1[0] - self.get_y_with_z_mirror(x1[1], C_0)
        gamma_turn, z_turn = self.get_turning_point(c)
        if(z_turn >= 0):
            # signal reflected at surface
            self.__logger.debug('signal reflects off surface')
            z_turn = 0
            gamma_turn = self.get_gamma(0)
        y_turn = self.get_y(gamma_turn, C_0, C_1)
        zstart = x1[1]
        zstop = x2[1]
        if(y_turn < x2[0]):
            zstop = zstart + np.abs(z_turn - x1[1]) + np.abs(z_turn - x2[1])
        x2_mirrored = [x2[0], zstop]
        return x2_mirrored

    def get_z_unmirrored(self, z, C_0):
        """
        calculates the unmirrored z position
        """
        c = self.medium.n_ice ** 2 - C_0 ** -2
        gamma_turn, z_turn = self.get_turning_point(c)
        if(z_turn >= 0):
            # signal reflected at surface
            self.__logger.debug('signal reflects off surface')
            z_turn = 0

        z_unmirrored = z
        if(z > z_turn):
            z_unmirrored = 2 * z_turn - z
        return z_unmirrored

    def ds(self, t, C_0):
        """
        helper to calculate line integral
        """
        return (self.get_y_diff(t, C_0) ** 2 + 1) ** 0.5

    def get_path_length(self, x1, x2, C_0):
        x2_mirrored = self.get_z_mirrored(x1, x2, C_0)
        path_length = integrate.quad(self.ds, x1[1], x2_mirrored[1], args=(C_0))
        self.__logger.info("calculating path length from ({:.0f}, {:.0f}) to ({:.0f}, {:.0f}) = ({:.0f}, {:.0f}) = {:.2f} m".format(x1[0], x1[1], x2[0], x2[1],
                                                                                                                             x2_mirrored[0],
                                                                                                                             x2_mirrored[1],
                                                                                                                             path_length[0] / units.m))
        return path_length[0]

    def get_travel_time(self, x1, x2, C_0):
        x2_mirrored = self.get_z_mirrored(x1, x2, C_0)

        def dt(t, C_0):
            z = self.get_z_unmirrored(t, C_0)
            return self.ds(t, C_0) / speed_of_light * self.n(z)

        travel_time = integrate.quad(dt, x1[1], x2_mirrored[1], args=(C_0))
        self.__logger.info("calculating travel time from ({:.0f}, {:.0f}) to ({:.0f}, {:.0f}) = ({:.0f}, {:.0f}) = {:.2f} ns".format(x1[0], x1[1], x2[0], x2[1], x2_mirrored[0], x2_mirrored[1], travel_time[0] / units.ns))
        return travel_time[0]

    def get_attenuation_along_path(self, x1, x2, C_0, frequency):
        x2_mirrored = self.get_z_mirrored(x1, x2, C_0)

        def dt(t, C_0, frequency):
            z = self.get_z_unmirrored(t, C_0)
            return self.ds(t, C_0) / self.get_attenuation_length(z, frequency)

        mask = frequency > 0

        # to speed up things we only calculate the attenuation for a few frequencies
        # and interpolate linearly between them
        freqs = np.linspace(frequency[mask].min(), frequency[mask].max(), 4)
        tmp = np.array([integrate.quad(dt, x1[1], x2_mirrored[1], args=(C_0, f), epsrel=0.05)[0] for f in freqs])
        att_func = interpolate.interp1d(freqs, tmp)
        tmp2 = att_func(frequency[mask])
#         tmp = np.array([integrate.quad(dt, x1[1], x2_mirrored[1], args=(C_0, f), epsrel=0.05)[0] for f in frequency[mask]])
        attenuation = np.ones_like(frequency)
        attenuation[mask] = np.exp(-1 * tmp2)
        self.__logger.info("calculating attenuation from ({:.0f}, {:.0f}) to ({:.0f}, {:.0f}) = ({:.0f}, {:.0f}) =  a factor {}".format(x1[0], x1[1], x2[0], x2[1], x2_mirrored[0], x2_mirrored[1], 1 / attenuation))
        return attenuation

    def get_temperature(self, z):
        return (-51.5 + z * (-4.5319e-3 + 5.822e-6 * z))

    def get_attenuation_length(self, z, frequency):
        t = self.get_temperature(z)
        f0 = 0.0001
        f2 = 3.16
        w0 = np.log(f0)
        w1 = 0.0
        w2 = np.log(f2)
        w = np.log(frequency / units.GHz)
        b0 = -6.74890 + t * (0.026709 - t * 0.000884)
        b1 = -6.22121 - t * (0.070927 + t * 0.001773)
        b2 = -4.09468 - t * (0.002213 + t * 0.000332)
        if((type(frequency) == float) or (type(frequency) == np.float64)):
            if (frequency < 1. * units.GHz):
                a = (b1 * w0 - b0 * w1) / (w0 - w1)
                bb = (b1 - b0) / (w1 - w0)
            else:
                a = (b2 * w1 - b1 * w2) / (w1 - w2)
                bb = (b2 - b1) / (w2 - w1)
        else:
            a = np.ones_like(frequency) * (b2 * w1 - b1 * w2) / (w1 - w2)
            bb = np.ones_like(frequency) * (b2 - b1) / (w2 - w1)
            a[frequency < 1. * units.GHz] = (b1 * w0 - b0 * w1) / (w0 - w1)
            bb[frequency < 1. * units.GHz] = (b1 - b0) / (w1 - w0)

        return 1. / np.exp(a + bb * w)

    def get_angle(self, x, x_start, C_0):
        z = self.get_z_mirrored(x_start, x, C_0)[1]
        dy = self.get_y_diff(z, C_0)
        angle = np.arctan(dy)
        if(angle < 0):
            angle = np.pi + angle
        return angle

    def get_launch_angle(self, x1, C_0):
        return self.get_angle(x1, x1, C_0)

    def get_receive_angle(self, x1, x2, C_0):
        return np.pi - self.get_angle(x2, x1, C_0)

    def get_path(self, x1, x2, C_0, n_points=1000):
        """
        for plotting purposes only,  returns the ray tracing path between x1 and x2

        the result is only valid if C_0 is a solution to the ray tracing problem

        Parameters
        -------
        x1: array
            start position (y, z)
        x2: array
            stop position (y, z)
        C_0: (float)
            first parameter
        n_points: integer (optional)
            the number of coordinates to calculate

        Returns
        -------
        yy: array
            the y coordinates of the ray tracing path
        zz: array
            the z coordinates of the ray tracing path
        """
        c = self.medium.n_ice ** 2 - C_0 ** -2
        C_1 = x1[0] - self.get_y_with_z_mirror(x1[1], C_0)
        gamma_turn, z_turn = self.get_turning_point(c)
        if(z_turn >= 0):
            # signal reflected at surface
            self.__logger.debug('signal reflects off surface')
            z_turn = 0
            gamma_turn = self.get_gamma(0)
        y_turn = self.get_y(gamma_turn, C_0, C_1)
        zstart = x1[1]
        zstop = self.get_z_mirrored(x1, x2, C_0)[1]
        z = np.linspace(zstart, zstop, n_points)
        mask = z < z_turn
        res = np.zeros_like(z)
        zs = np.zeros_like(z)
        gamma = self.get_gamma(z[mask])
        zs[mask] = z[mask]
        res[mask] = self.get_y(gamma, C_0, C_1)
        gamma = self.get_gamma(2 * z_turn - z[~mask])
        res[~mask] = 2 * y_turn - self.get_y(gamma, C_0, C_1)
        zs[~mask] = 2 * z_turn - z[~mask]

        self.__logger.debug('turning points for C_0 = {:.2f}, b= {:.2f}, gamma = {:.4f}, z = {:.1f}, y_turn = {:.0f}'.format(C_0, self.__b, gamma_turn, z_turn, y_turn))
        return res, zs

    def obj_delta_y_square(self, logC_0, x1, x2):
        """
        objective function to find solution for C0
        """
        C_0 = self.get_C0_from_log(logC_0)
        return self.get_delta_y(C_0, x1, x2) ** 2

    def obj_delta_y(self, logC_0, x1, x2):
        """
        function to find solution for C0, returns distance in y between function and x2 position
        result is signed! (important to use a root finder)
        """
        C_0 = self.get_C0_from_log(logC_0)
        return self.get_delta_y(C_0, x1, x2)

    def get_delta_y(self, C_0, x1, x2, C0range=None):
        """
        calculates the difference in the y position between the analytic ray tracing path
        specified by C_0 at the position x2
        """
        if(C0range is None):
            C0range = [1. / self.medium.n_ice, np.inf]
        if(not(type(C_0) == np.float64 or type(C_0) == float)):
            C_0 = C_0[0]
        if((C_0 < C0range[0]) or(C_0 > C0range[1])):
            self.__logger.debug('C0 = {:.4f} out of range {:.0f} - {:.2f}'.format(C_0, C0range[0], C0range[1]))
            return np.inf
        c = self.medium.n_ice ** 2 - C_0 ** -2
        # determine y translation first
        C_1 = x1[0] - self.get_y_with_z_mirror(x1[1], C_0)
        self.__logger.debug("C_0 = {:.4f}, C_1 = {:.1f}".format(C_0, C_1))

        # for a given c_0, 3 cases are possible to reach the y position of x2
        # 1) direct ray, i.e., beofre the turning point
        # 2) refracted ray, i.e. after the turning point but not touching the surface
        # 3) reflected ray, i.e. after the ray reaches the surface
        gamma_turn, z_turn = self.get_turning_point(c)
        if(z_turn > 0):
            z_turn = 0  # a reflection is just a turning point at z = 0, i.e. cases 2) and 3) are the same
            gamma_turn = self.get_gamma(z_turn)
        y_turn = self.get_y(gamma_turn, C_0, C_1)
        if(z_turn < x2[1]):  # turning points is deeper that x2 positions, can't reach target
            self.__logger.debug("turning points (zturn = {:.0f} is deeper than x2 positon z2 = {:.0f}".format(z_turn, x2[1]))
            return -np.inf
        self.__logger.debug('turning points is z = {:.1f}, y =  {:.1f}'.format(z_turn, y_turn))
        if(y_turn > x2[0]):  # we always propagate from left to right
            # direct ray
            y2_fit = self.get_y(self.get_gamma(x2[1]), C_0, C_1)  # calculate y position at get_path position
            diff = (x2[0] - y2_fit)
            self.__logger.debug('we have a direct ray, y({:.1f}) = {:.1f} -> {:.1f} away from {:.1f}'.format(x2[1], y2_fit, diff, x2[0]))
            return diff
        else:
            # now it's a bit more complicated. we need to transform the coordinates to be on the mirrored part of the function
            z_mirrored = x2[1]
            gamma = self.get_gamma(z_mirrored)
            self.__logger.debug("get_y( {}, {}, {})".format(gamma, C_0, C_1))
            y2_raw = self.get_y(gamma, C_0, C_1)
            y2_fit = 2 * y_turn - y2_raw
            diff = (x2[0] - y2_fit)
            self.__logger.debug('we have a reflected/refracted ray, y({:.1f}) = {:.1f} ({:.1f}) -> {:.1f} away from {:.1f} (gamma = {:.5g})'.format(z_mirrored, y2_fit, y2_raw, diff, x2[0], gamma))
            return -1 * diff

    def determine_solution_type(self, x1, x2, C_0):
        c = self.medium.n_ice ** 2 - C_0 ** -2
        C_1 = x1[0] - self.get_y_with_z_mirror(x1[1], C_0)
        gamma_turn, z_turn = self.get_turning_point(c)

        if(z_turn >= 0):
            z_turn = 0
            gamma_turn = self.get_gamma(0)
        y_turn = self.get_y(gamma_turn, C_0, C_1)
        if(x2[0] < y_turn):
            return 'direct'
        else:
            if(z_turn == 0):
                return 'reflected'
            else:
                return 'refracted'

    def find_solutions(self, x1, x2, plot=False):
        """
        this function finds all ray tracing solutions

        prerequesite is that x2 is above and to the right of x1, this is not a violation of universality
        because this requirement can be achieved with a simple coordinate transformation

        returns an array of the C_0 paramters of the solutions (the array might be empty)
        """
        tol = 1e-4
        results = []
        C0s = []  # intermediate storage of results
        self.__logger.debug('starting optimization with x0 = {:.2f} -> C0 = {:.3f}'.format(-1, self.get_C0_from_log(-1)))
        result = optimize.root(self.obj_delta_y_square, x0=-1, args=(x1, x2), tol=tol)
        if(plot):
            fig, ax = plt.subplots(1, 1)
        if(result.fun < 1e-5):
            if(plot):
                self.plot_result(x1, x2, self.get_C0_from_log(result.x[0]), ax)
            if(np.round(result.x[0], 3) not in np.round(C0s, 3)):
                C_0 = self.get_C0_from_log(result.x[0])
                C0s.append(C_0)
                solution_type = self.determine_solution_type(x1, x2, C_0)
                self.__logger.info("found {} solution C0 = {:.2f}".format(solution_type, C_0))
                results.append({'type': solution_type,
                                'C0': C_0,
                                'C1': self.get_C_1(x1, C_0)})

        # check if another solution with higher logC0 exists
        logC0_start = result.x[0] + 0.0001
        logC0_stop = 100
        delta_start = self.obj_delta_y(logC0_start, x1, x2)
        delta_stop = self.obj_delta_y(logC0_stop, x1, x2)
    #     print(logC0_start, logC0_stop, delta_start, delta_stop, np.sign(delta_start), np.sign(delta_stop))
        if(np.sign(delta_start) != np.sign(delta_stop)):
            self.__logger.info("solution with logC0 > {:.3f} exists".format(result.x[0]))
            result2 = optimize.brentq(self.obj_delta_y, logC0_start, logC0_stop, args=(x1, x2))
            if(plot):
                self.plot_result(x1, x2, self.get_C0_from_log(result2), ax)
            if(np.round(result2, 3) not in np.round(C0s, 3)):
                C_0 = self.get_C0_from_log(result2)
                C0s.append(C_0)
                solution_type = self.determine_solution_type(x1, x2, C_0)
                self.__logger.info("found {} solution C0 = {:.2f}".format(solution_type, C_0))
                results.append({'type': solution_type,
                                'C0': C_0,
                                'C1': self.get_C_1(x1, C_0)})
        else:
            self.__logger.info("no solution with logC0 > {:.3f} exists".format(result.x[0]))

        logC0_start = -100
        logC0_stop = result.x[0] - 0.0001
        delta_start = self.obj_delta_y(logC0_start, x1, x2)
        delta_stop = self.obj_delta_y(logC0_stop, x1, x2)
    #     print(logC0_start, logC0_stop, delta_start, delta_stop, np.sign(delta_start), np.sign(delta_stop))
        if(np.sign(delta_start) != np.sign(delta_stop)):
            self.__logger.info("solution with logC0 < {:.3f} exists".format(result.x[0]))
            result3 = optimize.brentq(self.obj_delta_y, logC0_start, logC0_stop, args=(x1, x2))

            if(plot):
                self.plot_result(x1, x2, self.get_C0_from_log(result3), ax)
            if(np.round(result3, 3) not in np.round(C0s, 3)):
                C_0 = self.get_C0_from_log(result3)
                C0s.append(C_0)
                solution_type = self.determine_solution_type(x1, x2, C_0)
                self.__logger.info("found {} solution C0 = {:.2f}".format(solution_type, C_0))
                results.append({'type': solution_type,
                                'C0': C_0,
                                'C1': self.get_C_1(x1, C_0)})
        else:
            self.__logger.info("no solution with logC0 < {:.3f} exists".format(result.x[0]))

        if(plot):
            plt.show()
        return results

    def plot_result(self, x1, x2, C_0, ax):
        """
        helper function to visualize results
        """
        C_1 = self.get_C_1(x1, C_0)

        zs = np.linspace(x1[1], x1[1] + np.abs(x1[1]) + np.abs(x2[1]), 1000)
        yy, zz = self.get_y_with_z_mirror(zs, C_0, C_1)
        ax.plot(yy, zz, '-', label='C0 = {:.3f}'.format(C_0))
        ax.plot(x1[0], x1[1], 'ko')
        ax.plot(x2[0], x2[1], 'd')

    #     ax.plot(zz, yy, '-', label='C0 = {:.3f}'.format(C_0))
    #     ax.plot(x1[1], x1[0], 'ko')
    #     ax.plot(x2[1], x2[0], 'd')
        ax.legend()


class ray_tracing:
    """
    utility class (wrapper around the 2D analytic ray tracing code) to get
    ray tracing solutions in 3D for two arbitrary points x1 and x2
    """

    def __init__(self, x1, x2, medium, log_level=logging.WARNING):
        """
        class initilization

        Parameters
        ----------
        x1: 3dim np.array
            start point of the ray
        x2: 3dim np.array
            stop point of the ray

        """
        self.__logger = logging.getLogger('ray_tracing')
        self.__logger.setLevel(log_level)

        self.__swap = False
        self.__X1 = x1
        self.__X2 = x2
        if(x2[2] < x1[2]):
            self.__swap = True
            self.__logger.debug('swap = True')
            self.__X2 = x1
            self.__X1 = x2

        dX = self.__X2 - self.__X1
        self.__dPhi = -np.arctan2(dX[1], dX[0])
        c, s = np.cos(self.__dPhi), np.sin(self.__dPhi)
        self.__R = np.array(((c, -s, 0), (s, c, 0), (0, 0, 1)))
        X1r = self.__X1
        X2r = np.dot(self.__R, self.__X2 - self.__X1) + self.__X1
        self.__logger.debug("X1 = {}, X2 = {}".format(self.__X1, self.__X2))
        self.__logger.debug('dphi = {:.1f}'.format(self.__dPhi / units.deg))
        self.__logger.debug("X2 - X1 = {}, X1r = {}, X2r = {}".format(self.__X2 - self.__X1, X1r, X2r))
        self.__x1 = np.array([X1r[0], X1r[2]])
        self.__x2 = np.array([X2r[0], X2r[2]])
        self.__r2d = ray_tracing_2D(medium, log_level=log_level)
        self.__results = self.__r2d.find_solutions(self.__x1, self.__x2)

    def has_solution(self):
        return len(self.__results) > 0

    def get_number_of_solutions(self):
        return len(self.__results)

    def get_results(self):
        return self.__results

    def get_solution_type(self, iS):
        """ returns the type of the solution

        Parameters
        ----------
        iS: int
            choose for which solution to compute the launch vector, counting
            starts at zero

        Returns
        -------
        solution_type: string
            * 'direct'
            * 'refracted'
            * 'reflected
        """

    def get_launch_vector(self, iS):
        """
        calculates the launch vector (in 3D) of solution iS

        Parameters
        ----------
        iS: int
            choose for which solution to compute the launch vector, counting
            starts at zero

        Returns
        -------
        launch_vector: 3dim np.array
            the launch vector
        """
        n = self.get_number_of_solutions()
        if(iS >= n):
            self.__logger.error("solution number {:d} requested but only {:d} solutions exist".format(iS + 1, n))
            raise IndexError

        result = self.__results[iS]
        alpha = self.__r2d.get_launch_angle(self.__x1, result['C0'])
        launch_vector_2d = np.array([np.sin(alpha), 0, np.cos(alpha)])
        if self.__swap:
            alpha = self.__r2d.get_receive_angle(self.__x1, self.__x2, result['C0'])
            launch_vector_2d = np.array([-np.sin(alpha), 0, np.cos(alpha)])
        self.__logger.debug(self.__R.T)
        launch_vector = np.dot(self.__R.T, launch_vector_2d)
        return launch_vector

    def get_receive_vector(self, iS):
        """
        calculates the receive vector (in 3D) of solution iS

        Parameters
        ----------
        iS: int
            choose for which solution to compute the launch vector, counting
            starts at zero

        Returns
        -------
        receive_vector: 3dim np.array
            the receive vector
        """
        n = self.get_number_of_solutions()
        if(iS >= n):
            self.__logger.error("solution number {:d} requested but only {:d} solutions exist".format(iS + 1, n))
            raise IndexError

        result = self.__results[iS]
        alpha = self.__r2d.get_receive_angle(self.__x1, self.__x2, result['C0'])
        receive_vector_2d = np.array([-np.sin(alpha), 0, np.cos(alpha)])
        if self.__swap:
            alpha = self.__r2d.get_launch_angle(self.__x1, result['C0'])
            receive_vector_2d = np.array([np.sin(alpha), 0, np.cos(alpha)])
        receive_vector = np.dot(self.__R.T, receive_vector_2d)
        return receive_vector

    def get_path_length(self, iS):
        """
        calculates the path length of solution iS

        Parameters
        ----------
        iS: int
            choose for which solution to compute the launch vector, counting
            starts at zero

        Returns
        -------
        distance: float
            distance from x1 to x2 along the ray path
        """
        n = self.get_number_of_solutions()
        if(iS >= n):
            self.__logger.error("solution number {:d} requested but only {:d} solutions exist".format(iS + 1, n))
            raise IndexError

        result = self.__results[iS]
        return self.__r2d.get_path_length(self.__x1, self.__x2, result['C0'])

    def get_travel_time(self, iS):
        """
        calculates the travel time of solution iS

        Parameters
        ----------
        iS: int
            choose for which solution to compute the launch vector, counting
            starts at zero

        Returns
        -------
        time: float
            travel time
        """
        n = self.get_number_of_solutions()
        if(iS >= n):
            self.__logger.error("solution number {:d} requested but only {:d} solutions exist".format(iS + 1, n))
            raise IndexError

        result = self.__results[iS]
        return self.__r2d.get_travel_time(self.__x1, self.__x2, result['C0'])

    def get_attenuation(self, iS, frequency):
        """
        calculates the signal attenuation due to attenuation in the medium (ice)

        Parameters
        ----------
        iS: int
            choose for which solution to compute the launch vector, counting
            starts at zero

        frequency: array of floats
            the frequencies for which the attenuation is calculated

        Returns
        -------
        attenuation: array of floats
            the fraction of the signal that reaches the observer
            (only ice attenuation, the 1/R signal falloff not considered here)
        """
        n = self.get_number_of_solutions()
        if(iS >= n):
            self.__logger.error("solution number {:d} requested but only {:d} solutions exist".format(iS + 1, n))
            raise IndexError

        result = self.__results[iS]
        return self.__r2d.get_attenuation_along_path(self.__x1, self.__x2, result['C0'], frequency)
