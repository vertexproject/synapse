import time

class RateLimit:
    '''
    A RateLimit class may be used to detect/enforce rate limits.

    Example:

        # allow 20 uses per 10 sec ( 2/sec )
        rlimit = RateLimit(20,10)

    Notes:

        It is best ( even in a "calls per day" type config ) to
        specify a smaller "per" to force rate "smoothing".

    '''
    def __init__(self, rate, per):
        self.rate = float(rate)
        self.per = float(per)

        self.lasttick = time.time()
        self.allowance = float(rate)

        self.persec = float(rate) / float(per)
        self.onetick = float(per) / float(rate)

    def allows(self):
        '''
        Returns True if the rate limit has not been reached.

        Example:

            if not rlimit.allows():
                rasie RateExceeded()

            # ok to go...

        '''
        tick = time.time()
        passed = tick - self.lasttick

        self.allowance = min(self.rate, self.allowance + (passed * self.persec))

        self.lasttick = tick

        if self.allowance < 1.0:
            return False

        self.allowance -= 1.0
        return True
