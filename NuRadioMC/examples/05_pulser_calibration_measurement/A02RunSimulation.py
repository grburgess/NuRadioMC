from __future__ import absolute_import, division, print_function
import argparse
import datetime
# import detector simulation modules
import NuRadioReco.modules.efieldToVoltageConverter
import NuRadioReco.modules.channelResampler
import NuRadioReco.modules.channelGenericNoiseAdder
import NuRadioReco.modules.ARIANNA.hardwareResponseIncorporator
import NuRadioReco.modules.trigger.highLowThreshold
from NuRadioReco.utilities import units
from NuRadioMC.simulation import simulation2 as simulation
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("runstrawman")

# initialize detector sim modules
efieldToVoltageConverter = NuRadioReco.modules.efieldToVoltageConverter.efieldToVoltageConverter()
efieldToVoltageConverter.begin()
channelResampler = NuRadioReco.modules.channelResampler.channelResampler()
channelGenericNoiseAdder = NuRadioReco.modules.channelGenericNoiseAdder.channelGenericNoiseAdder()
hardwareResponseIncorporator = NuRadioReco.modules.ARIANNA.hardwareResponseIncorporator.hardwareResponseIncorporator()
triggerSimulator = NuRadioReco.modules.trigger.highLowThreshold.triggerSimulator()
triggerSimulator.begin(log_level=logging.WARNING)

class mySimulation(simulation.simulation):


    def _detector_simulation(self):
        if(bool(self._cfg['signal']['zerosignal'])):
            self._increase_signal(None, 0)
        
        efieldToVoltageConverter.run(self._evt, self._station, self._det)  # convolve efield with antenna pattern
        # downsample trace to internal simulation sampling rate (the efieldToVoltageConverter upsamples the trace to
        # 20 GHz by default to achive a good time resolution when the two signals from the two signal paths are added) 
        channelResampler.run(self._evt, self._station, self._det, sampling_rate=1. / self._dt)
        
        if bool(self._cfg['noise']):
            Vrms = self._Vrms / (self._bandwidth /( 2.5 * units.GHz))** 0.5  # normalize noise level to the bandwidth its generated for
            channelGenericNoiseAdder.run(self._evt, self._station, self._det, amplitude=Vrms, min_freq=0 * units.MHz,
                                         max_freq=2.5 * units.GHz, type='rayleigh')
        

        hardwareResponseIncorporator.run(self._evt, self._station, self._det, sim_to_data=True)
        
        triggerSimulator.run(self._evt, self._station, self._det,
                           threshold_high=0.5 * units.mV,
                           threshold_low=-0.5 * units.mV,
                           high_low_window=5 * units.ns,
                           coinc_window=30 * units.ns,
                           number_concidences=2,
                           triggered_channels=range(8),
                           cut_trace=True)
#         self._station.set_triggered(True)
                
        # downsample trace back to detector sampling rate
        channelResampler.run(self._evt, self._station, self._det, sampling_rate=self._sampling_rate_detector)


parser = argparse.ArgumentParser(description='Run NuRadioMC simulation')
parser.add_argument('inputfilename', type=str,
                    help='path to NuRadioMC input event list')
parser.add_argument('detectordescription', type=str,
                    help='path to file containing the detector description')
parser.add_argument('config', type=str,
                    help='NuRadioMC yaml config file')
parser.add_argument('outputfilename', type=str,
                    help='hdf5 output filename')
parser.add_argument('outputfilenameNuRadioReco', type=str, nargs='?', default=None,
                    help='outputfilename of NuRadioReco detector sim file')
args = parser.parse_args()

sim = mySimulation(eventlist=args.inputfilename,
                            outputfilename=args.outputfilename,
                            detectorfile=args.detectordescription,
                            outputfilenameNuRadioReco=args.outputfilenameNuRadioReco,
                            config_file=args.config,
                            log_level=logging.INFO,
                            evt_time=datetime.datetime(2018, 12, 30))
sim.run()

