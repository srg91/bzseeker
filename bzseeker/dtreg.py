import re
import locale
from datetime import time as dt_time

_DIRECT_PATTERN = re.compile(r'%[A-z]')

_C_KEY = locale.nl_langinfo(locale.D_T_FMT)
_XD_KEY = locale.nl_langinfo(locale.D_FMT)
_XT_KEY = locale.nl_langinfo(locale.T_FMT)
_AMPM_KEY = '({am}|{pm})'.format(am=dt_time().strftime('%p'),
                                 pm=dt_time(12).strftime('%p'))

_DIRECTIVES = {
    r'\w+': ('%a', '%A', '%b', '%B'),
    r'\d{2}': ('%d', '%H', '%I', '%j', '%m', '%M', '%S', '%U', '%W', '%y'),
    r'\d{4,}': ('%Y', ),
    r'\d': ('%w', ),

    _AMPM_KEY: ('%p', ),
    _C_KEY: ('%c', ),
    _XD_KEY: ('%x', ),
    _XT_KEY: ('%X', ),

    r'(UTC|EST|CST)?': ('%Z', ),
    r'(\+\d{4})?': ('%z', ),
}


def convert(dt_format):
    _special = ('%c', '%x', '%X', )

    def _get_by_directive(directive):
        for regex, directives in _DIRECTIVES.iteritems():
            if directive in directives:
                if directive in _special:
                    _get_by_directive.complex = True
                return regex
        return directive

    _map_directive = lambda d: _get_by_directive(d.group())
    _get_by_directive.complex = False

    result = _DIRECT_PATTERN.sub(_map_directive, dt_format)
    while _get_by_directive.complex:
        result = _DIRECT_PATTERN.sub(_map_directive, result)
        _get_by_directive.complex = False

    return result.replace(' ', r'\s')
