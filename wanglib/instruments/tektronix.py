#!/usr/bin/env python
"""
Interfaces to Tektronix oscilloscopes.

"""

from wanglib.util import InstrumentError, sciround
import numpy

class TDS3000(object):
    """ A Tektronix oscilloscope from the TDS3000 series.

    Can be controlled over GPIB, RS-232, or Ethernet. Just
    pass an object with ``write``, ``read``, and ``ask`` methods
    to the constructor.

    >>> from wanglib.util import Serial
    >>> bus = Serial('/dev/ttyS0', rtscts=True)
    >>> scope = tds3000(bus)

    If using RS-232 (as above), be sure to use rtscts, and
    connect using a null modem cable.

    """

    class _Wfmpre(dict):
        """ Waveform formatting parameters, as a dictionary. """

        def __init__(self, bus):
            self.bus = bus

        def __getitem__(self, key):
            result = self.bus.ask('WFMP:%s?' % key).rstrip()
            return result

    def __init__(self, bus=None):
        if bus is None:
            from wanglib.util import Serial
            bus = Serial('/dev/ttyS0', rtscts=True, term_chars='\n')
        self.bus = bus
        self.wfmpre = self._Wfmpre(bus)

    def get_curve(self):
        """
        Fetch a trace.

        :returns: A numpy array representing the current waveform.

        """
        self.bus.readall()
        self.bus.write('CURV?')
        result = self.bus.read() # reads either everything (GPIB)
                                 # or a single byte (RS-232)
        if result == '#':
            meta_len = int(self.bus.read(1))
            data_len = int(self.bus.read(meta_len))
            result = self.bus.read(data_len)
            self.bus.read(1) # read final newline
        elif len(result) == 1:
            # if we received something other than a pound sign
            raise InstrumentError('Unknown first byte: %s' % result)

        fmt = '>' if self.wfmpre['BYT_OR'] == 'MSB' else '<'
        fmt += 'i' if self.wfmpre['BN_FMT'] == 'RI' else 'u'
        fmt += self.wfmpre['BYT_NR']

        return numpy.fromstring(result, dtype = fmt)

    def get_timediv(self):
        """
        Get time per division, in seconds.

        :returns: Seconds per division, as a floating-point number.
        """
        result = self.bus.ask('HOR:MAI:SCA?')
        return float(result.rstrip())

    _acceptable_timedivs = (  10,   4,    2,    1,
                                 4e-1, 2e-1, 1e-1,
                                 4e-2, 2e-2, 1e-2,
                                 4e-3, 2e-3, 1e-3,
                                 4e-4, 2e-4, 1e-4,
                                 4e-5, 2e-5, 1e-5,
                                 4e-6, 2e-6, 1e-6,
                                 4e-7, 2e-7, 1e-7,
                                 4e-8, 2e-8, 1e-8,
                                 4e-9, 2e-9, 1e-9)

    def set_timediv(self, to):
        """
        Set time per division, in seconds.

        :param to:  Desired seconds per division.
                    Acceptable values range from 10 seconds to 1, 2, or
                    4ns, depending on model, in a 1-2-4 sequence.
        :type to:   float

        """
        to = sciround(to, 1)
        if to in self._acceptable_timedivs:
            self.bus.write('HOR:MAI:SCA %.0E' % to)
        else:
            raise InstrumentError('Timediv not in %s' %
                                  str(self._acceptable_timedivs))

    timediv = property(get_timediv, set_timediv)
    """ Time per division, in seconds. """


if __name__ == "__main__":
    scope = TDS3000()
    