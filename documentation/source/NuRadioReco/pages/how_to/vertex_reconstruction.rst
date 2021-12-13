Use the Vertex Reconstruction Modules
======================================

NuRadioReco comes with 2 modules to reconstruct the position of the neutrino
interaction vertex. Both work in a very similar way: The expected difference
in signal arrival times between channels is determined for a possible vertex
position and the correlation between the channel waveforms is calculated for
that time shift. This is done for multiple channel pair and the correlations
for each pair are summed up. By scanning over all possible locations,the vertex
position can be determined by finding the point where the sum of correlations
is the largest.

Creating Lookup Tables
-------------------------

Redoing the raytracing for every point where the interaction vertex may be
will take too much time to be practical in the long run. Therefore, the propagation
times for a grid of positions is calculated once and stored to be used as a
lookup table later. To save computing time and storage space, cylindrical
symmetry of the signal propagation times is assumed, meaning that they do not
depend on the azimuth and can be stored as functions of the depth and the horizontal
distance from the antenna.

NuRadioReco provides a script to produce the lookup tables  at
`NuRadioReco/modules/neutrinoVertexReconstructor/create_lookup_tables.py`
The default settings should work well, just pay attention to some points:

  - You need to calculate lookup tables for all antenna depths you want to use in the
    reconstruction
  - Make sure the maximum depth and horitontal distance are large enough. They define
    the region where you can search for the vertex
  - Make sure you use the right ice model
  - Depending on the settings, calculating these tables can take a long time. We
    recommend running it on a batch system.

Creating Electric Field Templates
-------------------------------------------

The reliability of the vertex reconstructor modules at low SNR can be improved by using
a template to correlate with the measured voltages instead of correlating the waveforms
directly.

.. Important::
    The template correlation method has been tested for the RNO-G detector, whose antenna
    response is very consistent for different signal receiving angles. It may not work
    if the antenna has a group delay that depends on the receiving angle.

The template is an object of the class
:class:`BaseTrace <NuRadioReco.framework.base_trace>`
that contains an (three-dimensional) electric field that can be used by the vertex reconstruction
modules to fold it with the antenna response to create a voltage template. Such a template can
be created, for example, with this code snippet:

.. code-block:: Python

    import NuRadioMC.utilities.medium
    import NuRadioMC.SignalGen.askaryan
    import NuRadioReco.framework.base_trace
    from NuRadioReco.utilities import units
    n_samples = 1024
    viewing_angle = 1. * units.deg
    sampling_rate = 5. * units.GHz
    ice = NuRadioMC.utilities.medium.get_ice_model('greenland_simple')
    ior = ice.get_index_of_refraction([0, 0, -1. * units.km])
    cherenkov_angle = np.arccos(1. / ior)
    efield_spec = NuRadioMC.SignalGen.askaryan.get_frequency_spectrum(
        energy=1.e18 * units.eV,
        theta=viewing_angle + cherenkov_angle,
        N=n_samples,
        dt=1. / sampling_rate,
        shower_type='HAD',
        n_index=ior,
        R=5. * units.km,
        model='ARZ2019'
    )
    efield_template = NuRadioReco.framework.base_trace.BaseTrace()
    efield_template.set_frequency_spectrum(efield_spec, sampling_rate)

.. Important::
    The electric field template needs to have the same sampling rate as the voltage wave forms.
    It should also be long enough so the pulse does not wrap around when the antenna response
    is applied.

2D vs. 3D Vertex Reconstructor
----------------------------------

The neutrino2DVertexReconstructor uses antennas that are on the same string and takes advantage of
resulting symmetry to speed up the reconstruction. Thanks to the rotational symmetry around the
z-axis, the problem can be reduced to two dimensions and the vertex position is described by the
horizontal distance from the center and the depth. The disadvantage is that only channels on the same
detector string can be used and that deviations from the cylindrical symmetry by a real detector due
to some uncertainty in the exactl antenna positions may influence the resulting accuracy.
It can also not reconstruct the azimuth coordinate of the vertex position.

The neutrino3DVertexReconstructor can utilize all all detector channels of the same antenna type and
searches for the vertex position in the full 3D space. As doing a scan over the full detector volume
would take too long and use up too much memory, so first a rougher scan is performed that is used to
limit the finer scan to the most likely region.

For both detectors, the step size of the grid they search on is important. A smaller grid will give
better results, but the reconstruction will take longer. A step size of around 2m has worked well
so far. For the y-coordinates in 3D scan, a larger spacing can be used to speed up the process.

.. Important::
    Matplotlib can struggle with drawing colormaps from large data sets. Drawing the debug plots
    when using a fine grid spacing or a large search volume can seriously slow down the reconstruction
    or even freeze the computer, so it is advisable to use a larger spacing when drawing debug plots.







