# -*- coding: cp1252 -*-
# This file is part of pyTSEB for estimating the resistances to momentum and heat transport
# Copyright 2016 Hector Nieto and contributors listed in the README.md file.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Created on Apr 6 2015
@author: Hector Nieto (hnieto@ias.csic.es)

Modified on Jan 27 2016
@author: Hector Nieto (hnieto@ias.csic.es)

DESCRIPTION
===========
This module includes functions for calculating the resistances for
heat and momentum trasnport for both One- and Two-Source Energy Balance models.
Additional functions needed in are imported from the following packages

* :doc:`meteoUtils` for the estimation of meteorological variables.
* :doc:`MOsimilarity` for the estimation of the Monin-Obukhov length and stability functions.

PACKAGE CONTENTS
================
Resistances
-----------
* :func:`calc_R_A` Aerodynamic resistance.
* :func:`calc_R_S_Choudhury` [Choudhury1988]_ soil resistance.
* :func:`calc_R_S_McNaughton` [McNaughton1995]_ soil resistance.
* :func:`calc_R_S_Kustas` [Kustas1999]_ soil resistance.
* :func:`calc_R_x_Choudhury` [Choudhury1988]_ canopy boundary layer resistance.
* :func:`calc_R_x_McNaughton` [McNaughton1995]_ canopy boundary layer resistance.
* :func:`calc_R_x_Norman` [Norman1995]_ canopy boundary layer resistance.

Stomatal conductance
--------------------
* :func:`calc_stomatal_conductance_TSEB` TSEB stomatal conductance.
* :func:`calc_coef_m2mmol` Conversion factor from stomatal conductance from m s-1 to mmol m-2 s-1.

Estimation of roughness
-----------------------
* :func:`calc_d_0` Zero-plane displacement height.
* :func:`calc_roughness` Roughness for different land cover types.
* :func:`calc_z_0M` Aerodynamic roughness lenght.
* :func:`raupach` Roughness and displacement height factors for discontinuous canopies.

"""

from math import pi

import numpy as np

import pyTSEB.MO_similarity as MO
import pyTSEB.meteo_utils as met

#==============================================================================
# List of constants used in TSEB model and sub-routines
#==============================================================================
# Landcover classes and values come from IGBP Land Cover Type Classification
WATER = 0
CONIFER_E = 1
BROADLEAVED_E = 2
CONIFER_D = 3
BROADLEAVED_D = 4
FOREST_MIXED = 5
SHRUB_C = 6
SHRUB_O = 7
SAVANNA_WOODY = 8
SAVANNA = 9
GRASS = 10
WETLAND = 11
CROP = 12
URBAN = 13
CROP_MOSAIC = 14
SNOW = 15
BARREN = 16

# Leaf stomata distribution
AMPHISTOMATOUS = 2
HYPOSTOMATOUS = 1
# von Karman's constant
k = 0.4
# acceleration of gravity (m s-2)
gravity = 9.8
# Universal gas constant (kPa m3 mol-1 K-1)
R_u = 0.0083144

CM_a = 0.01  # Choudhury and Monteith 1988 leaf drag coefficient
KN_b = 0.012  # Value propoesd in Kustas et al 1999
KN_c = 0.0025  # Coefficient from Norman et al. 1995
KN_C_dash = 90.0  # value proposed in Norman et al. 1995


def calc_d_0(h_C):
    ''' Zero-plane displacement height

    Calculates the zero-plane displacement height based on a
    fixed ratio of canopy height.

    Parameters
    ----------
    h_C : float
        canopy height (m).

    Returns
    -------
    d_0 : float
        zero-plane displacement height (m).'''

    d_0 = h_C * 0.65
    return np.asarray(d_0)


def calc_roughness(LAI, h_C, w_C=1, landcover=CROP,f_c=None):
    ''' Surface roughness and zero displacement height for different vegetated surfaces.

    Calculates the roughness using different approaches depending we are dealing with
    crops or grasses (fixed ratio of canopy height) or shrubs and forests,depending of LAI
    and canopy shape, after [Schaudt2000]_

    Parameters
    ----------
    LAI : float
        Leaf (Plant) Area Index.
    h_C : float
        Canopy height (m)
    w_C : float, optional
        Canopy height to width ratio.
    landcover : int, optional
        landcover type, use 11 for crops, 2 for grass, 5 for shrubs,
        4 for conifer forests and 3 for broadleaved forests.

    Returns
    -------
    z_0M : float
        aerodynamic roughness length for momentum trasport (m).
    d : float
        Zero-plane displacement height (m).

    References
    ----------
    .. [Schaudt2000] K.J Schaudt, R.E Dickinson, An approach to deriving roughness length
        and zero-plane displacement height from satellite data, prototyped with BOREAS data,
        Agricultural and Forest Meteorology, Volume 104, Issue 2, 8 August 2000, Pages 143-155,
        http://dx.doi.org/10.1016/S0168-1923(00)00153-2.
    '''

    # Convert input scalars to numpy arrays
    LAI, h_C, w_C, landcover = map(np.asarray, (LAI, h_C, w_C, landcover))
    # Initialize fractional cover and horizontal area index
    lambda_=np.zeros(LAI.shape)
    if type(f_c) == type(None):
        f_c = np.zeros(LAI.shape)
        # Needleleaf canopies
        mask = np.logical_or(landcover == CONIFER_E, landcover == CONIFER_D)
        f_c[mask] = 1. - np.exp(-0.5 * LAI[mask])
        # Broadleaved canopies
        mask = np.logical_or.reduce((landcover == BROADLEAVED_E, landcover == BROADLEAVED_D,
                             landcover == FOREST_MIXED, landcover == SAVANNA_WOODY))
        f_c[mask] = 1. - np.exp(-LAI[mask])
        # Shrublands
        mask = np.logical_or(landcover == SHRUB_O, landcover == SHRUB_C)
        f_c[mask] = 1. - np.exp(-0.5 * LAI[mask])

    # Needleleaf canopies
    mask = np.logical_or(landcover == CONIFER_E, landcover == CONIFER_D)
    lambda_[mask] = (2. / pi) * f_c[mask] * w_C[mask]
    # Broadleaved canopies
    mask = np.logical_or.reduce((landcover == BROADLEAVED_E, landcover == BROADLEAVED_D,
                         landcover == FOREST_MIXED, landcover == SAVANNA_WOODY))
    lambda_[mask] = f_c[mask] * w_C[mask]
    # Shrublands
    mask = np.logical_or(landcover == SHRUB_O, landcover == SHRUB_C)
    lambda_[mask] = f_c[mask] * w_C[mask]

    # Calculation of the Raupach (1994) formulae
    z0M_factor, d_factor = raupach(lambda_)

    # Calculation of correction factors from  Lindroth
    fz = np.asarray(0.3299 * LAI**1.5 + 2.1713)
    fd = np.asarray(1. - 0.3991 * np.exp(-0.1779 * LAI))
    # LAI <= 0
    fz[LAI <= 0] = 1.0
    fd[LAI <= 0] = 1.0
    # LAI >= 0.8775:
    fz[LAI >= 0.8775] = 1.6771 * np.exp(-0.1717 * LAI[LAI >= 0.8775]) + 1.
    fd[LAI >= 0.8775] = 1. - 0.3991 * np.exp(-0.1779 * LAI[LAI >= 0.8775])
    # Application of the correction factors to roughness and displacement
    # height
    z0M_factor = np.asarray(z0M_factor * fz)
    d_factor = np.asarray(d_factor * fd)

    # For crops and grass we use a fixed ratio of canopy height
    mask = np.logical_or.reduce((landcover == CROP, landcover == GRASS,
                         landcover == SAVANNA, landcover == CROP_MOSAIC))
    z0M_factor[mask] = 1. / 8.
    d_factor[mask] = 0.65
    # Calculation of rouhgness length
    z_0M = np.asarray(z0M_factor * h_C)
    # Calculation of zero plane displacement height
    d = np.asarray(d_factor * h_C)
    # For barren surfaces (bare soil, water, etc.)
    mask = np.logical_or.reduce((landcover == WATER, landcover == URBAN,
                         landcover == SNOW, landcover == BARREN))
    z_0M[mask] = 0.01
    d[mask] = 0
    return np.asarray(z_0M), np.asarray(d)


def calc_R_A(z_T, ustar, L, d_0, z_0H):
    ''' Estimates the aerodynamic resistance to heat transport based on the
    MO similarity theory.

    Parameters
    ----------
    z_T : float
        air temperature measurement height (m).
    ustar : float
        friction velocity (m s-1).
    L : float
        Monin Obukhov Length for stability
    d_0 : float
        zero-plane displacement height (m).
    z_0M : float
        aerodynamic roughness length for momentum trasport (m).
    z_0H : float
        aerodynamic roughness length for heat trasport (m).

    Returns
    -------
    R_A : float
        aerodyamic resistance to heat transport in the surface layer (s m-1).

    References
    ----------
    .. [Norman1995] J.M. Norman, W.P. Kustas, K.S. Humes, Source approach for estimating
        soil and vegetation energy fluxes in observations of directional radiometric
        surface temperature, Agricultural and Forest Meteorology, Volume 77, Issues 3-4,
        Pages 263-293, http://dx.doi.org/10.1016/0168-1923(95)02265-Y.
    '''

    # Convert input scalars to numpy arrays
    z_T, ustar, L, d_0, z_0H = map(np.asarray, (z_T, ustar, L, d_0, z_0H))
    R_A_log = np.asarray(np.log((z_T - d_0) / z_0H))

    # if L -> infinity, z./L-> 0 and there is neutral atmospheric stability
    # other atmospheric conditions
    L[L == 0] = 1e-36
    Psi_H = MO.calc_Psi_H((z_T - d_0) / L)
    Psi_H0 = MO.calc_Psi_H(z_0H / L)

    #i = np.logical_and(z_star>0, z_T<=z_star)
    #Psi_H_star[i] = MO.calc_Psi_H_star(z_T[i], L[i], d_0[i], z_0H[i], z_star[i])

    i = ustar != 0
    R_A = np.asarray(np.ones(ustar.shape) * float('inf'))
    R_A[i] = (R_A_log[i] - Psi_H[i] + Psi_H0[i]) / (ustar[i] * k)
    return np.asarray(R_A)


def calc_R_S_Choudhury(u_star, h_C, z_0M, d_0, zm, z0_soil=0.01, alpha_k=2.0):
    ''' Aerodynamic resistance at the  soil boundary layer.

    Estimates the aerodynamic resistance at the  soil boundary layer based on the
    K-Theory model of [Choudhury1988]_.

    Parameters
    ----------
    u_star : float
        friction velocity (m s-1).
    h_C : float
        canopy height (m).
    z_0M : float
        aerodynamic roughness length for momentum trasport (m).
    d_0 : float
        zero-plane displacement height (m).
    zm : float
        height on measurement of wind speed (m).
    z0_soil : float, optional
        roughness length of the soil layer, use z0_soil=0.01.
    alpha_k : float, optional
        Heat diffusion coefficient, default=2.

    Returns
    -------
    R_S : float
        Aerodynamic resistance at the  soil boundary layer (s m-1).

    References
    ----------
    .. [Choudhury1988] Choudhury, B. J., & Monteith, J. L. (1988). A four-layer model
        for the heat budget of homogeneous land surfaces.
        Royal Meteorological Society, Quarterly Journal, 114(480), 373-398.
        http://dx/doi.org/10.1002/qj.49711448006.
    '''

    # Soil resistance eqs. 24 & 25 [Choudhury1988]_
    K_h = k * u_star * (h_C - d_0)
    R_S = (h_C * np.exp(alpha_k) / (alpha_k * K_h)) * \
        (np.exp(-alpha_k * z0_soil / h_C) - np.exp(-alpha_k * (d_0 + z_0M) / h_C))
    return np.asarray(R_S)

def calc_R_S_Haghighi(u, h_C, zm, rho, c_p, z0_soil=0.01, f_cover=0, w_C=1, theta=0.4,theta_res=0.1, phi=2.0, ps=0.001, n=0.5):
    ''' Aerodynamic resistance at the  soil boundary layer.

    Estimates the aerodynamic resistance at the  soil boundary layer based on the
    K-Theory model of [Choudhury1988]_.

    Parameters
    ----------
    u_star : float
        friction velocity (m s-1).
    h_C : float
        canopy height (m).
    z_0M : float
        aerodynamic roughness length for momentum trasport (m).
    d_0 : float
        zero-plane displacement height (m).
    zm : float
        height on measurement of wind speed (m).
    z0_soil : float, optional
        roughness length of the soil layer, use z0_soil=0.01.
    alpha_k : float, optional
        Heat diffusion coefficient, default=2.

    Returns
    -------
    R_S : float
        Aerodynamic resistance at the  soil boundary layer (s m-1).

    References
    ----------
    .. [Choudhury1988] Choudhury, B. J., & Monteith, J. L. (1988). A four-layer model
        for the heat budget of homogeneous land surfaces.
        Royal Meteorological Society, Quarterly Journal, 114(480), 373-398.
        http://dx/doi.org/10.1002/qj.49711448006.

% -------------------------------------------------------------------------
%  Inputs   |              Description
% -------------------------------------------------------------------------
% ps        | mean particle size of soil        [m]
% n         | soil pore size distribution index [-]
% phi       | porosity                          [-]
% theta     | soil water content                [m3 m-3]
% theta_res | residual water content            [m3 m-3]
% z_w       | measurement height                [m]
% U         | wind velocity                     [m s-1]
% eta       | vegetation cover fraction         [-]      =0 for bare soil
% h         | (cylindrical) vegettaion height   [m]      =0 for bare soil
% d         | (cylindrical) vegetation diameter [m]      =0 for bare soil
% -------------------------------------------------------------------------

    '''
    # Define constanst
    D    = 0.282e-4   # [m2 s-1]    water vapor diffusion coefficient in air
    nu   = 15.11e-6   # [m2 s-1]    kinmeatic visocosity of air
    Ka   = 0.024    # [W m-1 K-1] thermal conductivity of air
    lambda_E    = 2450e3   # [J/kg]      Latent heat of vaporization
    
    # [Haghighi and Or, 2015, JHydrol]
    a_r   = 3.
    a_s   = 5.
    k     = 0.1
    k_v   = 0.41
    gamma = 150.
    f_alpha = 22. # [Haghighi and Or, 2013, WRR]

    u, h_C, zm, z0_soil, f_cover, w_C, theta,theta_res, phi, ps, n = map(np.asarray, (u, h_C, zm, z0_soil, f_cover, w_C, theta,theta_res, phi, ps, n))

    f_theta = (1./np.sqrt(np.pi*(theta-theta_res)))*(np.sqrt(np.pi/(4*(theta-theta_res)))-1)

    THETA = (theta-theta_res)/(phi-theta_res)
    K_sat = (0.0077*n**7.35)/(24.*3600.)  #[m s-1]
    m     = 1.-1./n
    K_eff = 4*K_sat*np.sqrt(THETA)*(1-(1-THETA**(1/m))**m)**2     #[Haghighi et al., 2013, WRR]

    width=h_C*w_C
    A_veg  = (np.pi/4)*width**2
    lambda_ = width*h_C*f_cover/A_veg
    
    h_C[f_cover==0]=0
    lambda_[f_cover==0]=0

    z_0sc = z0_soil*(1+f_cover*((zm-h_C)/zm-1))
    f_r     = np.exp(-a_r*lambda_/(1.-f_cover)**k)
    f_s     = np.exp(-a_s*lambda_/(1.-f_cover)**k)
    C_sgc   = k_v**2*(np.log((zm-h_C)/z_0sc))**-2
    C_sg    = k_v**2*(np.log(zm/z0_soil))**-2
    f_c     = 1.+f_cover*(C_sgc/C_sg-1.)
    C_rg    = gamma*C_sg
    u_star  = u*np.sqrt(f_r*lambda_*(1-f_cover)*C_rg+(f_s*(1-f_cover)+f_c*f_cover)*C_sg)
    delta   = f_alpha*nu/u_star
    R_S_LE = rho* c_p*((delta+(ps/3)*f_theta)/D + 1.73e-5/K_eff)/lambda_E     # see Haghighi et al. [2013, WRR]
    R_S_H  = rho* c_p*delta/Ka;

    return np.asarray(R_S_H),np.asarray(R_S_LE)
    

def calc_R_S_McNaughton(u_friction):
    ''' Aerodynamic resistance at the  soil boundary layer.

    Estimates the aerodynamic resistance at the  soil boundary layer based on the
    Lagrangian model of [McNaughton1995]_.

    Parameters
    ----------
    u_friction : float
        friction velocity (m s-1).

    Returns
    -------
    R_S : float
        Aerodynamic resistance at the  soil boundary layer (s m-1)

    References
    ----------
    .. [McNaughton1995] McNaughton, K. G., & Van den Hurk, B. J. J. M. (1995).
        A 'Lagrangian' revision of the resistors in the two-layer model for calculating
        the energy budget of a plant canopy. Boundary-Layer Meteorology, 74(3), 261-288.
        http://dx/doi.org/10.1007/BF00712121.

    '''

    R_S = 10.0 / u_friction
    return np.asarray(R_S)


def calc_R_S_Kustas(u_S, deltaT, params = {}):
    ''' Aerodynamic resistance at the  soil boundary layer.

    Estimates the aerodynamic resistance at the  soil boundary layer based on the
    original equations in TSEB [Kustas1999]_.

    Parameters
    ----------
    u_S : float
        wind speed at the soil boundary layer (m s-1).
    deltaT : float
        Surface to air temperature gradient (K).

    Returns
    -------
    R_S : float
        Aerodynamic resistance at the  soil boundary layer (s m-1).

    References
    ----------
    .. [Kustas1999] William P Kustas, John M Norman, Evaluation of soil and vegetation heat
        flux predictions using a simple two-source model with radiometric temperatures for
        partial canopy cover, Agricultural and Forest Meteorology, Volume 94, Issue 1,
        Pages 13-29, http://dx.doi.org/10.1016/S0168-1923(99)00005-2.
    '''

    # Set model parameters
    if "KN_b" in params:    
        b = params["KN_b"]
    else:
        b = KN_b    
    if "KN_c" in params:
        c = params['KN_c']
    else:
        c = KN_c
    
    # Convert input scalars to numpy arrays
    u_S, deltaT = map(np.asarray, (u_S, deltaT))
    
    deltaT = np.asarray(np.maximum(deltaT, 0.1))
    R_S = 1.0 / (c * deltaT**(1.0 / 3.0) + b * u_S)
    return np.asarray(R_S)


def calc_R_x_Choudhury(u_C, F, leaf_width, alpha_prime=3.0):
    ''' Estimates aerodynamic resistance at the canopy boundary layer.

    Estimates the aerodynamic resistance at the canopy boundary layer based on the
    K-Theory model of [Choudhury1988]_.

    Parameters
    ----------
    u_C : float
        wind speed at the canopy interface (m s-1).
    F : float
        local Leaf Area Index.
    leaf_width : float
        efective leaf width size (m).
    alpha_prime : float, optional
        Wind exctinction coefficient, default=3.

    Returns
    -------
    R_x : float
        Aerodynamic resistance at the canopy boundary layer (s m-1).

    References
    ----------
    .. [Choudhury1988] Choudhury, B. J., & Monteith, J. L. (1988). A four-layer model
        for the heat budget of homogeneous land surfaces.
        Royal Meteorological Society, Quarterly Journal, 114(480), 373-398.
        http://dx/doi.org/10.1002/qj.49711448006.
    '''

    # Eqs. 29 & 30 [Choudhury1988]_
    R_x = 1.0 / (F * (2.0 * CM_a / alpha_prime) * np.sqrt(u_C / \
                 leaf_width) * (1.0 - np.exp(-alpha_prime / 2.0)))
    # R_x=(alpha_u*(sqrt(leaf_width/U_C)))/(2.0*alpha_0*LAI*(1.-exp(-alpha_u/2.0)))
    return np.asarray(R_x)


def calc_R_x_McNaughton(F, leaf_width, u_star):
    ''' Estimates aerodynamic resistance at the canopy boundary layer.

    Estimates the aerodynamic resistance at the canopy boundary layer based on the
    Lagrangian model of [McNaughton1995]_.

    Parameters
    ----------
    F : float
        local Leaf Area Index.
    leaf_width : float
        efective leaf width size (m).
    u_d_zm : float
        wind speed at the height of momomentum source-sink.

    Returns
    -------
    R_x : float
        Aerodynamic resistance at the canopy boundary layer (s m-1).

    References
    ----------
    .. [McNaughton1995] McNaughton, K. G., & Van den Hurk, B. J. J. M. (1995).
        A 'Lagrangian' revision of the resistors in the two-layer model for calculating
        the energy budget of a plant canopy. Boundary-Layer Meteorology, 74(3), 261-288.
        http://dx/doi.org/10.1007/BF00712121.
    '''

    C_dash = 130.0
    C_dash_F = C_dash / F
    # Eq. 30 in [McNaugthon1995]
    R_x = C_dash_F * (leaf_width * u_star)**0.5 + 0.36 / u_star  
    return np.asarray(R_x)


def calc_R_x_Norman(LAI, leaf_width, u_d_zm, params = {}):
    ''' Estimates aerodynamic resistance at the canopy boundary layer.

    Estimates the aerodynamic resistance at the  soil boundary layer based on the
    original equations in TSEB [Norman1995]_.

    Parameters
    ----------
    F : float
        local Leaf Area Index.
    leaf_width : float
        efective leaf width size (m).
    u_d_zm : float
        wind speed at the height of momomentum source-sink. .

    Returns
    -------
    R_x : float
        Aerodynamic resistance at the canopy boundary layer (s m-1).

    References
    ----------
    .. [Norman1995] J.M. Norman, W.P. Kustas, K.S. Humes, Source approach for estimating
        soil and vegetation energy fluxes in observations of directional radiometric
        surface temperature, Agricultural and Forest Meteorology, Volume 77, Issues 3-4,
        Pages 263-293, http://dx.doi.org/10.1016/0168-1923(95)02265-Y.
    '''

    # Set model parameters
    if "KN_C_dash" in params:
        C_dash = params["KN_C_dash"]
    else:
        C_dash = KN_C_dash
 
    R_x = (C_dash / LAI) * (leaf_width / u_d_zm)**0.5
    return np.asarray(R_x)


def calc_stomatal_conductance_TSEB(
        LE_C,
        LE,
        R_A,
        R_x,
        e_a,
        T_A,
        T_C,
        F,
        p=1013.0,
        leaf_type=1,
        f_g=1,
        f_dry=1):
    ''' TSEB Stomatal conductace

    Estimates the effective Stomatal conductace by inverting the
    resistance-based canopy latent heat flux from a Two source perspective

    Parameters
    ----------
    LE_C : float
        Canopy latent heat flux (W m-2).
    LE : float
        Surface (bulk) latent heat flux (W m-2).
    R_A : float
        Aerodynamic resistance to heat transport (s m-1).
    R_x : float
        Bulk aerodynamic resistance to heat transport at the canopy boundary layer (s m-1).
    e_a : float
        Water vapour pressure at the reference height (mb).
    T_A : float
        Air temperature at the reference height (K).
    T_C : float
        Canopy (leaf) temperature (K).
    F : float
        local Leaf Area Index.
    p : float, optional
        Atmospheric pressure (mb) use 1013.0 as default.
    leaf_type : int, optional
        type of leaf regarding stomata distribution.

            1=HYPOSTOMATOUS stomata in the lower surface of the leaf (default).
            2=AMPHISTOMATOUS, stomata in both surfaces of the leaf.
    f_g : float, optional
        Fraction of green leaves.
    f_dry : float, optional
        Fraction of dry (non-wet) leaves.

    Returns
    -------
    G_s : float
        effective leaf stomata conductance (m s-1).

    References
    ----------
    .. [Anderson2000] M.C. Anderson, J.M. Norman, T.P. Meyers, G.R. Diak, An analytical
        model for estimating canopy transpiration and carbon assimilation fluxes based on
        canopy light-use efficiency, Agricultural and Forest Meteorology, Volume 101,
        Issue 4, 12 April 2000, Pages 265-289, ISSN 0168-1923,
        http://dx.doi.org/10.1016/S0168-1923(99)00170-7.'''

    # Convert input scalars to numpy arrays
    LE_C, LE, R_A, R_x, e_a, T_A, T_C, F, p, leaf_type, f_g, f_dry = map(
        np.asarray, (LE_C, LE, R_A, R_x, e_a, T_A, T_C, F, p, leaf_type, f_g, f_dry))
    G_s = np.zeros(np.shape(LE_C))
    # Invert the bulk SW to obtain eb (vapor pressure at the canopy interface)
    rho = met.calc_rho(p, e_a, T_A)
    Cp = met.calc_c_p(p, e_a)
    Lambda = met.calc_lambda(T_A)
    psicr = met.calc_psicr(p, Lambda)
    e_ac = e_a + LE * R_A * psicr / (rho * Cp)
    # Calculate the saturation vapour pressure in the leaf in mb
    e_star = met.calc_vapor_pressure(T_C)
    # Calculate the boundary layer canopy resisitance to water vapour (Anderson et al. 2000)
    # Invert the SW LE_S equation to calculate the bulk stomatal resistance
    R_c = np.asarray((rho * Cp * (e_star - e_ac) / (LE_C * psicr)) - R_x)
    K_c = np.asarray(f_dry * f_g * leaf_type)
    # Get the mean stomatal resistance (here LAI comes in as stomatal resistances
    # are in parallel: 1/Rc=sum(1/R_st)=LAI/Rst
    # ans the mean leaf conductance is the reciprocal of R_st (m s-1)
    G_s[R_c > 0] = 1.0 / R_c[R_c > 0] * K_c[R_c > 0] * F[R_c > 0]
    return np.asarray(G_s)


def calc_coef_m2mmol(T_C, p=101.325):
    '''Calculates the conversion factor from stomatal conductance from m s-1
    to mmol m-2 s-1.

    Parameters
    ----------
    T_C : float
        Leaf temperature (K).
    p : float, optional
        Atmospheric pressure (kPa), default = 101.3 kPa.

    Returns
    -------
    K_gs : float
        Conversion factor from  m s-1 to mmol m-2 s-1.

    References
    ----------
    [Kimball2015] Kimball, B. A., White, J. W., Ottman, M. J., Wall, G. W., Bernacchi, C. J.,
        Morgan, J., & Smith, D. P. (2015). Predicting canopy temperatures and infrared heater energy
        requirements for warming field plots. Agronomy Journal, 107(1), 129-141
        http://dx.doi.org/10.2134/agronj14.0109.
    '''

    K_gs = p / (R_u * T_C)  # to mol m-2 s-1
    K_gs = K_gs * 1e3  # to mmol m-2 s-1
    return np.asarray(K_gs)


def calc_z_0H(z_0M, kB=0):
    '''Estimate the aerodynamic routhness length for heat trasport.

    Parameters
    ----------
    z_0M : float
        aerodynamic roughness length for momentum transport (m).
    kB : float
        kB parameter, default = 0.

    Returns
    -------
    z_0H : float
        aerodynamic roughness length for momentum transport (m).

    References
    ----------
    .. [Norman1995] J.M. Norman, W.P. Kustas, K.S. Humes, Source approach for estimating
        soil and vegetation energy fluxes in observations of directional radiometric
        surface temperature, Agricultural and Forest Meteorology, Volume 77, Issues 3-4,
        Pages 263-293, http://dx.doi.org/10.1016/0168-1923(95)02265-Y.
    '''

    z_0H = z_0M / np.exp(kB)
    return np.asarray(z_0H)


def calc_z_0M(h_C):
    ''' Aerodynamic roughness lenght.

    Estimates the aerodynamic roughness length for momentum trasport
    as a ratio of canopy height.

    Parameters
    ----------
    h_C : float
        Canopy height (m).

    Returns
    -------
    z_0M : float
        aerodynamic roughness length for momentum transport (m).'''

    z_0M = h_C * 0.125
    return np.asarray(z_0M)


def raupach(lambda_):
    '''Roughness and displacement height factors for discontinuous canopies

    Estimated based on the frontal canopy leaf area, based on Raupack 1994 model,
    after [Schaudt2000]_

    Parameters
    ----------
    lambda_ : float
        roughness desnsity or frontal area index.

    Returns
    -------
    z0M_factor : float
        height ratio of roughness length for momentum transport
    d_factor : float
        height ratio of zero-plane displacement height

    References
    ----------
    .. [Schaudt2000] K.J Schaudt, R.E Dickinson, An approach to deriving roughness length
        and zero-plane displacement height from satellite data, prototyped with BOREAS data,
        Agricultural and Forest Meteorology, Volume 104, Issue 2, 8 August 2000, Pages 143-155,
        http://dx.doi.org/10.1016/S0168-1923(00)00153-2.

    '''

    # Convert input scalar to numpy array
    lambda_ = np.asarray(lambda_)
    z0M_factor = np.zeros(lambda_.shape)
    d_factor = np.asarray(np.zeros(lambda_.shape) + 0.65)

    # Calculation of the Raupach (1994) formulae
    # if lambda_ > 0.152:
    i = lambda_ > 0.152
    z0M_factor[i] = (0.0537 / (lambda_[i]**0.510)) * \
                    (1. - np.exp(-10.9 * lambda_[i]**0.874)) + 0.00368
    # else:
    z0M_factor[~i] = 5.86 * \
        np.exp(-10.9 * lambda_[~i]**1.12) * lambda_[~i]**1.33 + 0.000860
    # if lambda_ > 0:
    i = lambda_ > 0
    d_factor[i] = 1. - \
        (1. - np.exp(-np.sqrt(15.0 * lambda_[i]))) / np.sqrt(15.0 * lambda_[i])

    return np.asarray(z0M_factor), np.asarray(d_factor)
