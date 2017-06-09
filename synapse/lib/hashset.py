import hashlib

class HashSet:

    def __init__(self):

        self.size = 0

        # BEWARE ORDER MATTERS FOR guid()
        self.hashes = [
            ('md5',hashlib.md5()),
            ('sha1',hashlib.sha1()),
            ('sha256',hashlib.sha256()),
            ('sha512',hashlib.sha512())
        ]

    def guid(self):
        '''
        Use elements from this hash set to create a unique
        (re)identifier.
        '''
        iden = hashlib.md5()
        props = {'size':self.size}

        for name,item in self.hashes:
            iden.update(item.digest())
            props[name] = item.hexdigest()

        return iden.hexdigest(),props

    def eatfd(self, fd):
        '''
        Consume all the bytes from a file like object.

        Example:

            hset = HashSet()
            hset.eatfd(fd)

        '''
        fd.seek(0)
        byts = fd.read(10000000)
        while byts:
            self.update(byts)
            byts = fd.read(10000000)

        return self.guid()

    def update(self, byts):
        '''
        Update all the hashes in the set with the given bytes.
        '''
        self.size += len(byts)
        [ h[1].update(byts) for h in self.hashes ]

    def digests(self):
        '''
        Return a list of (name,digest) tuples for the hashes in the set.
        '''
        return [ (name,item.hexdigest()) for (name,item) in self.hashes ]


