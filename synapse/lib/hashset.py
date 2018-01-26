import hashlib

class HashSet:

    def __init__(self):

        self.size = 0

        # BEWARE ORDER MATTERS FOR guid()
        self.hashes = (
            ('md5', hashlib.md5()),
            ('sha1', hashlib.sha1()),
            ('sha256', hashlib.sha256()),
            ('sha512', hashlib.sha512())
        )

    def guid(self):
        '''
        Use elements from this hash set to create a unique
        (re)identifier.
        '''
        iden = hashlib.md5()
        props = {'size': self.size}

        for name, item in self.hashes:
            iden.update(item.digest())
            props[name] = item.hexdigest()

        return iden.hexdigest(), props

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
        [h[1].update(byts) for h in self.hashes]

    def digests(self):
        '''
        Get a list of (name, bytes) tuples for the hashes in the hashset.

        Notes:
            The computes the guid for the hashset and includes it in the
            list of values returned with the name "guid".

        Returns:
            list: A list of (str, bytes) tuples representing the name and
            hash value, in bytes, for the hashset.
        '''
        retn = []
        guid = hashlib.md5()

        for name, item in self.hashes:
            valu = item.digest()
            guid.update(valu)
            retn.append((name, valu))

        retn.append(('guid', guid.digest()))

        return retn
