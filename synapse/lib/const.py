# Logging related constants
import logging

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
