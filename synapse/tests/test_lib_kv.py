import os
import lmdb

import synapse.lib.kv as s_kv
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

class KvTest(s_t_utils.SynTest):

    def test_lib_kv_base_rewrite(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'test.lmdb')
            key = b'hehe'
            dupkey = b'dup:hehe'
            valu = b'haha'
            propd = {b'prefix:1': b'woah',
                     b'prefix:2': b'dude',
                     b'pennywise:derry': b'georgie'}
            dlk1 = b'dup:list'
            dlk2 = b'dup:dict'
            duplist = [
                (dlk1, b'hehe'),
                (dlk1, b'hehe'),
                (dlk1, b'haha'),
                (dlk1, b'dude'),
                (dlk2, b'{}'),
                (dlk2, b'{jk}')
            ]

            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                # Set a key
                self.none(stor.setKvProp(key, valu))
                self.eq(stor.getKvProp(key), valu)

                # We can overwrite a key
                self.none(stor.setKvProp(key, valu + valu))
                self.eq(stor.getKvProp(key), valu + valu)

                # Missing keys are None
                self.none(stor.getKvProp(valu))

                # We can delete a key
                self.true(stor.delKvProp(key))
                self.false(stor.delKvProp(key))

                # We can set a bunch of values in a single xact
                self.none(stor.setKvProps(propd))
                self.eq(stor.getKvProp(b'prefix:1'), b'woah')
                self.eq(stor.getKvProp(b'prefix:2'), b'dude')
                self.eq(stor.getKvProp(b'pennywise:derry'), b'georgie')

                # We can iterate over a given prefix of data
                vals = [tup for tup in stor.iterKvProps(b'prefix:')]
                self.len(2, vals)
                ed = propd.copy()
                ed.pop(b'pennywise:derry')
                self.eq(ed, dict(vals))

                # We may get no items during iteration too
                vals = [tup for tup in stor.iterKvProps(b'notaprefix:')]
                self.eq(vals, [])

                # Some keys may have multiple values in them via dup API
                self.false(stor.hasKvDups(dupkey))
                self.none(stor.addKvDup(dupkey, valu))
                self.none(stor.addKvDup(dupkey, valu + valu))
                self.none(stor.addKvDup(dupkey, valu + valu + valu))
                self.true(stor.hasKvDups(dupkey))
                vals = [tup for tup in stor.iterKvDups(dupkey)]
                self.eq(vals, [valu, valu + valu, valu + valu + valu])

                # Assert missing key gives no vals
                vals = [tup for tup in stor.iterKvDups(b'qwerasdfzxcv')]
                self.eq(vals, [])

                # We can delete a single value from a dup list
                self.true(stor.delKvDup(dupkey, valu + valu))
                self.false(stor.delKvDup(dupkey, valu + valu))
                vals = [tup for tup in stor.iterKvDups(dupkey)]
                self.eq(vals, [valu, valu + valu + valu])

                # We can set a bunch of dup props at once
                self.none(stor.addKvDups(duplist))
                # duplist contains one duplicate key/valu tuple,
                # which is discarded by lmdb
                self.len(6, duplist)
                self.len(3, [val for val in stor.iterKvDups(dlk1)])
                self.len(2, [val for val in stor.iterKvDups(dlk2)])

                # We can generate a named iden to use as an alias
                iden = stor.genKvAlias('vertex')
                self.len(16, iden)
                self.isinstance(iden, bytes)
                # the aliases are still stable
                niden = stor.genKvAlias('vertex')
                self.eq(iden, niden)
                another_iden = stor.genKvAlias('pennywise')
                self.len(16, another_iden)

                # We cannot have keys which are empty bytes
                self.raises(lmdb.BadValsizeError, stor.setKvProp, b'', b'newp')
                # We can have keys which have empty values though
                stor.setKvProp(b'yerp', b'')
                self.eq(stor.getKvProp(b'yerp'), b'')

            # The data in the kv store is persistent
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                self.none(stor.getKvProp(key))  # we had deleted data for key
                self.eq(stor.getKvProp(b'prefix:1'), b'woah')
                self.eq(stor.getKvProp(b'prefix:2'), b'dude')
                vals = [tup for tup in stor.iterKvDups(dupkey)]
                self.eq(vals, [valu, valu + valu + valu])
                self.len(3, [val for val in stor.iterKvDups(dlk1)])
                self.len(2, [val for val in stor.iterKvDups(dlk2)])

                # the aliases are still stable
                niden = stor.genKvAlias('vertex')
                self.eq(iden, niden)

    def test_lib_kv_set(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'test.lmdb')
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kset = stor.getKvSet('hehe')

                # Add a few items to the set
                # this also exercises __len__
                self.len(0, kset)
                self.none(kset.add(10))
                self.none(kset.add(20))
                self.len(2, kset)

                # Items are unique
                self.none(kset.add(20))
                self.len(2, kset)

                # We can remove items from the set
                kset.add(50)
                self.false(kset.remove(80))
                self.true(kset.remove(50))
                self.false(kset.remove(50))

                vals = [v for v in kset]
                self.len(2, vals)
                self.eq(set(vals), {10, 20})

            # The kset is persistent
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kset = stor.getKvSet('hehe')

                vals = [v for v in kset]
                self.len(2, vals)
                self.eq(set(vals), {10, 20})

                # We can do a bulk update of items
                items = [10, 11, 12, 13, 13, 13]
                self.none(kset.update(items))
                self.len(5, kset)
                self.eq({v for v in kset}, {10, 11, 12, 13, 20})

            # The kset is persistent and has the data we added from update()
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kset = stor.getKvSet('hehe')
                self.true(kset.remove(11))

    def test_lib_kv_dict(self):

        n = 20
        large_kv = {str(v): v for v in range(n)}

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'test.lmdb')
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kdic = stor.getKvDict('haha')

                self.none(kdic.set('lol', (1, 2, 3)))
                self.eq(kdic.get('lol'), (1, 2, 3))
                # Calling set again does an early-exit, this is for code coverage
                self.none(kdic.set('lol', (1, 2, 3)))

                # We can remove items from the store
                self.eq(kdic.pop('lol'), (1, 2, 3))
                self.none(kdic.pop('lol'))

                # We can set and update values in the store
                self.none(kdic.set('lol', (1, 2, 3)))
                self.eq(kdic.get('lol'), (1, 2, 3))
                self.none(kdic.set('lol', (4, 5, 6)))
                self.eq(kdic.get('lol'), (4, 5, 6))

            # The kvdict is persistent
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kdic = stor.getKvDict('haha')
                self.eq(kdic.get('lol'), (4, 5, 6))

                # Slam in a few items so we can iterate over them
                for k, v in large_kv.items():
                    kdic.set(k, v)

                # Ensure that if someone changes the kdic contents during iteration
                # we do not throw a runtime error
                check = n // 2
                for i, (k, v) in enumerate(kdic.items()):
                    if i == check:
                        kdic.set('vertex', 'do not break')
                        kdic.pop('lol')
                self.none(kdic.get('lol'))
                self.nn(kdic.get('vertex'))

            # Make sure we store updates to mutable objects
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kdic = stor.getKvDict('haha')

                v = {'a': 3, 'b': 'foo'}
                kdic.set('alpha', v)
                self.eq(kdic.get('alpha'), v)

                # change internal dictionary value
                v['a'] = 5
                kdic.set('alpha', v)

            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                kdic = stor.getKvDict('haha')
                self.eq(kdic.get('alpha')['a'], 5)

    def test_lib_kv_look(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')
            tufo = ('yo dawg', {'key': 1234})

            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                look = stor.getKvLook('haha')
                self.none(look.get('lol'))
                self.none(look.set('lol', (1, 2, 3)))
                self.eq(look.get('lol'), (1, 2, 3))

            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                look = stor.getKvLook('haha')
                self.eq(look.get('lol'), (1, 2, 3))
                self.none(look.set('lol', (5, 6, 7)))
                self.eq(look.get('lol'), (5, 6, 7))

            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                look = stor.getKvLook('haha')
                self.eq(look.get('lol'), (5, 6, 7))

            # We can work with the raw APIs too
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                look = stor.getKvLook('haha')

                self.none(look.getraw(b'node'))

                byts = look.getraw(b'lol')
                self.isinstance(byts, bytes)
                self.eq(byts, s_msgpack.en((5, 6, 7)))

                nbytes = s_msgpack.en(tufo)
                look.setraw(b'node', nbytes)
                self.eq(look.getraw(b'node'), nbytes)

            # We can iterate over the items stored in the KvLook's namespace
            with s_kv.KvStor(path) as stor:  # type: s_kv.KvStor
                look = stor.getKvLook('haha')
                kvs = [tup for tup in look.items()]
                self.len(2, kvs)
                self.sorteq(kvs, [('lol', (5, 6, 7)), ('node', tufo)])
