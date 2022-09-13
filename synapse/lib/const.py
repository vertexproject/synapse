import ssl
import logging

# Logging related constants
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s ' \
             '[%(filename)s:%(funcName)s:%(threadName)s:%(processName)s]'
LOG_LEVEL_CHOICES = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}
LOG_LEVEL_INVERSE_CHOICES = {v: k for k, v in LOG_LEVEL_CHOICES.items()}

# Math related constants
kilobyte = 1000
megabyte = 1000 * kilobyte
gigabyte = 1000 * megabyte
terabyte = 1000 * gigabyte
petabyte = 1000 * terabyte
exabyte = 1000 * petabyte
zettabyte = 1000 * exabyte
yottabyte = 1000 * zettabyte

kibibyte = 1024
mebibyte = 1024 * kibibyte
gibibyte = 1024 * mebibyte
tebibyte = 1024 * gibibyte
pebibyte = 1024 * tebibyte
exbibyte = 1024 * pebibyte
zebibyte = 1024 * exbibyte
yobibyte = 1024 * zebibyte

# time (in millis) constants
second = 1000
minute = second * 60
hour = minute * 60
day = hour * 24
week = day * 7
month = day * 30
year = day * 365

# TLS related constants

# Create a cipher string that supports TLS 1.2 and TLS 1.3 ciphers which do
# not use RSA. This has the effect of modifying the cipher list for a SSL
# context in Python 3.8 and below. Python 3.10+ has a default cipher list
# which drops several additional ciphers which are removed below.
_ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
_ciphers = [c for c in _ctx.get_ciphers()
            if c.get('protocol') in ('TLSv1.2', 'TLSv1.3')
            and c.get('kea') != 'kx-rsa']
tls_server_ciphers = ':'.join([c.get('name') for c in _ciphers])
del _ctx
del _ciphers
