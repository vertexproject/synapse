import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

geotestmodel = (
    ('geo:test', {

        'types': (
            ('test:latlong', ('geo:latlong', {}), {}),
            ('test:distoff', ('geo:dist', {'baseoff': 1000}), {}),
        ),

        'forms': (

            ('test:latlong', {}, (
                ('lat', ('geo:latitude', {}), {}),
                ('long', ('geo:longitude', {}), {}),
                ('dist', ('geo:dist', {}), {}),
            )),
            ('test:distoff', {}, ()),
        ),
    }),
)

geojson0 = {
  "type": "GeometryCollection",
  "bbox": [-110, -45, 110, 45],
  "geometries": [
    {
      "type": "Point",
      "coordinates": [0, 0]
    },
    {
      "type": "LineString",
      "coordinates": [[-110, 45], [110, -45]]
    },
    {
      "type": "Polygon",
      "coordinates": [
        [
          [100.0, 0.0],
          [101.0, 0.0],
          [101.0, 1.0],
          [100.0, 1.0],
          [100.0, 0.0]
        ],
        [
          [100.8, 0.8],
          [100.8, 0.2],
          [100.2, 0.2],
          [100.2, 0.8],
          [100.8, 0.8]
        ]
      ]
    }
  ]
}

geojson1 = {
  "type": "MultiPolygon",
  "coordinates": [
    [
      [
        [102.0, 2.0, 10],
        [103.0, 2.0, 10],
        [103.0, 3.0, 10],
        [102.0, 3.0, 10],
        [102.0, 2.0, 10]
      ]
    ],
    [
      [
        [100.0, 0.0, 20],
        [101.0, 0.0, 20],
        [101.0, 1.0, 20],
        [100.0, 1.0, 20],
        [100.0, 0.0, 20]
      ],
      [
        [100.2, 0.2, 30],
        [100.8, 0.2, 30],
        [100.8, 0.8, 30],
        [100.2, 0.8, 30],
        [100.2, 0.2, 30]
      ]
    ]
  ]
}

geojson2 = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "1",
      "geometry": {
        "type": "Point",
        "coordinates": [0, 0]
      },
      "properties": {
        "name": "basic"
      }
    }
  ]
}


class GeoTest(s_t_utils.SynTest):

    async def test_types_forms(self):
        formlat = 'geo:latitude'
        formlon = 'geo:longitude'
        formlatlon = 'geo:latlong'

        async with self.getTestCore() as core:

            # Latitude Type Tests =====================================================================================
            t = core.model.type(formlat)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('-90.1'))
            self.eq((await t.norm('-90'))[0], -90.0)
            self.eq((await t.norm('-12.345678901234567890'))[0], -12.34567890123456789)
            self.eq((await t.norm('-0'))[0], 0.0)
            self.eq((await t.norm('0'))[0], 0.0)
            self.eq((await t.norm('12.345678901234567890'))[0], 12.34567890123456789)
            self.eq((await t.norm('90'))[0], 90.0)
            self.eq((await t.norm('39.94891608'))[0], 39.94891608)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('90.1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('newp'))

            # Longitude Type Tests =====================================================================================
            t = core.model.type(formlon)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('-180.0'))
            self.eq((await t.norm('-12.345678901234567890'))[0], -12.34567890123456789)
            self.eq((await t.norm('-0'))[0], 0.0)
            self.eq((await t.norm('0'))[0], 0.0)
            self.eq((await t.norm('12.345678901234567890'))[0], 12.34567890123456789)
            self.eq((await t.norm('180'))[0], 180.0)
            self.eq((await t.norm('39.94891608'))[0], 39.94891608)
            await self.asyncraises(s_exc.BadTypeValu, t.norm('180.1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('newp'))

            # Latlong Type Tests =====================================================================================
            t = core.model.type(formlatlon)
            subs = {'lat': (t.lattype.typehash, 0.0, {}), 'lon': (t.lontype.typehash, 0.0, {})}
            self.eq(await t.norm('0,-0'), ((0.0, 0.0), {'subs': subs}))

            subs = {'lat': (t.lattype.typehash, 89.999, {}), 'lon': (t.lontype.typehash, 179.999, {})}
            self.eq(await t.norm('89.999,179.999'), ((89.999, 179.999), {'subs': subs}))

            subs = {'lat': (t.lattype.typehash, -89.999, {}), 'lon': (t.lontype.typehash, -179.999, {})}
            self.eq(await t.norm('-89.999,-179.999'), ((-89.999, -179.999), {'subs': subs}))

            subs = {'lat': (t.lattype.typehash, 89.999, {}), 'lon': (t.lontype.typehash, 179.999, {})}
            self.eq(await t.norm([89.999, 179.999]), ((89.999, 179.999), {'subs': subs}))
            self.eq(await t.norm((89.999, 179.999)), ((89.999, 179.999), {'subs': subs}))

            # Demonstrate precision
            subs = {'lat': (t.lattype.typehash, 12.345678, {}), 'lon': (t.lontype.typehash, -12.345678, {})}
            self.eq(await t.norm('12.345678,-12.345678'), ((12.345678, -12.345678), {'subs': subs}))

            subs = {'lat': (t.lattype.typehash, 12.3456789, {}), 'lon': (t.lontype.typehash, -12.3456789, {})}
            self.eq(await t.norm('12.3456789,-12.3456789'), ((12.3456789, -12.3456789), {'subs': subs}))
            self.eq(await t.norm('12.34567890,-12.34567890'), ((12.3456789, -12.3456789), {'subs': subs}))

            self.eq(t.repr((0, 0)), '0,0')
            self.eq(t.repr((0, -0)), '0,0')
            self.eq(t.repr((12.345678, -12.345678)), '12.345678,-12.345678')

            # Geo-dist tests
            formname = 'geo:dist'
            t = core.model.type(formname)

            self.eq(await t.norm('11 mm'), (11, {}))
            self.eq(await t.norm('11 millimeter'), (11, {}))
            self.eq(await t.norm('11 millimeters'), (11, {}))

            self.eq((await t.norm('837.33 m'))[0], 837330)
            self.eq((await t.norm('837.33 meter'))[0], 837330)
            self.eq((await t.norm('837.33 meters'))[0], 837330)

            self.eq((await t.norm('100km'))[0], 100000000)
            self.eq((await t.norm('100     km'))[0], 100000000)
            self.eq(await t.norm('11.2 km'), (11200000, {}))
            self.eq(await t.norm('11.2 kilometer'), (11200000, {}))
            self.eq(await t.norm('11.2 kilometers'), (11200000, {}))

            self.eq(await t.norm(11200000), (11200000, {}))

            self.eq((await t.norm('2 foot'))[0], 609)
            self.eq((await t.norm('5 feet'))[0], 1524)
            self.eq((await t.norm('1 yard'))[0], 914)
            self.eq((await t.norm('10 yards'))[0], 9144)
            self.eq((await t.norm('1 mile'))[0], 1609344)
            self.eq((await t.norm('3 miles'))[0], 4828032)

            self.eq(t.repr(5), '5 mm')
            self.eq(t.repr(500), '50.0 cm')
            self.eq(t.repr(1000), '1.0 m')
            self.eq(t.repr(10000), '10.0 m')
            self.eq(t.repr(1000000), '1.0 km')

            await self.asyncraises(s_exc.BadTypeValu, t.norm('1.3 pc'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('foo'))

            # geo:place

            # test inline tuple/float with negative syntax...
            nodes = await core.nodes('[ geo:place="*" :latlong=(-30.0,20.22) :type=woot.woot]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('type'), 'woot.woot.')
            self.eq(node.get('latlong'), (-30.0, 20.22))

            nodes = await core.nodes('''
                [ geo:place=*
                    :id=IAD
                    :ids=(ABC,)
                    :desc="The place where Vertex Project hangs out at!"
                    :name="Vertex HQ"
                    :address="208 Datong Road, Pudong District, Shanghai, China"
                    :address:city="  Shanghai  "
                    :loc=us.hehe.haha
                    :photo=*
                    :latlong=(34.1341, -118.3215)
                    :latlong:accuracy=2m
                    :altitude=200m
                    :altitude:accuracy=2m
                    :bbox="2.11, 2.12, -4.88, -4.9"
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('id'), 'IAD')
            self.eq(node.get('ids'), ('ABC',))
            self.eq(node.get('name'), 'vertex hq')
            self.eq(node.get('loc'), 'us.hehe.haha')
            self.eq(node.get('latlong'), (34.1341, -118.3215))
            self.eq(node.get('latlong:accuracy'), 2000)
            self.eq(node.get('altitude'), 6371208800)
            self.eq(node.get('altitude:accuracy'), 2000)
            self.eq(node.get('desc'), 'The place where Vertex Project hangs out at!')
            self.eq(node.get('address'), '208 datong road, pudong district, shanghai, china')
            self.eq(node.get('address:city'), 'shanghai')
            self.nn(node.get('photo'))

            self.len(1, await core.nodes('geo:place :photo -> file:bytes'))

            self.eq(node.get('bbox'), (2.11, 2.12, -4.88, -4.9))
            self.eq(node.repr('bbox'), '2.11,2.12,-4.88,-4.9')

            self.len(1, await core.nodes('geo:place -> geo:place:type:taxonomy'))

            self.eq(nodes[0].ndef[1], await core.callStorm('return({[geo:place=({"id": "ABC"})]})'))

            q = '[geo:place=(beep,) :latlong=$latlong]'
            opts = {'vars': {'latlong': (11.38, 20.01)}}
            nodes = await core.nodes(q, opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('latlong'), (11.38, 20.01))
            nodes = await core.nodes('[ geo:place=(hehe, haha) :names=("Foo  Bar ", baz) ] -> meta:name')
            self.eq(('baz', 'foo bar'), [n.ndef[1] for n in nodes])

            nodes = await core.nodes('geo:place=(hehe, haha)')
            node = nodes[0]

            self.len(1, nodes := await core.nodes('[ geo:place=({"name": "baz"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

    async def test_eq(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[geo:place=* :name="Vertex HQ" :latlong=(34.1341, -118.3215)]')
            self.len(1, nodes)

            nodes = await core.nodes('[geo:place=* :name="Griffith Observatory" :latlong=(34.1341, -118.3215)]')
            self.len(1, nodes)

            nodes = await core.nodes('geo:place:latlong=(34.1341, -118.3215)')
            self.len(2, nodes)

            nodes = await core.nodes('geo:place:latlong=(34.1341, -118.3)')
            self.len(0, nodes)

            nodes = await core.nodes('geo:place:latlong=(34.1, -118.3215)')
            self.len(0, nodes)

    async def test_near(self):

        async with self.getTestCore() as core:

            # These two nodes are 2,605m apart
            guid0 = s_common.guid()
            props = {'name': 'Vertex  HQ',
                     'latlong': '34.1341, -118.3215'}
            opts = {'vars': {'valu': guid0, 'p': props}}
            q = '[ geo:place=$valu :name=$p.name :latlong=$p.latlong ]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)

            guid1 = s_common.guid()
            props = {'name': 'Griffith Observatory',
                     'latlong': '34.118560, -118.300370'}
            opts = {'vars': {'valu': guid1, 'p': props}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)

            guid2 = s_common.guid()
            props = {'name': 'unknown location'}
            opts = {'vars': {'valu': guid2, 'p': props}}
            q = '[ geo:place=$valu :name=$p.name ]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)

            # Far away nodes to test bounding box
            guid5 = s_common.guid()
            props = {'latlong': '35.118660, -118.300470'}
            opts = {'vars': {'valu': guid5, 'p': props}}
            q = '[(tel:mob:telem=$valu :place:latlong=$p.latlong)]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)

            guid6 = s_common.guid()
            props = {'latlong': '33.118660, -118.300470'}
            opts = {'vars': {'valu': guid6, 'p': props}}
            q = '[(tel:mob:telem=$valu :place:latlong=$p.latlong)]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)

            # Node filtering behavior
            nodes = await core.nodes('geo:place +:latlong*near=((34.1, -118.3), 10km)')
            self.len(2, nodes)
            nodes = await core.nodes('geo:place +geo:place:latlong*near=((34.1, -118.3), 10km)')
            self.len(2, nodes)

            nodes = await core.nodes('geo:place +:latlong*near=((34.1, -118.3), 50m)')
            self.len(0, nodes)

            # +1's come from the unknown loc without a latlong prop
            nodes = await core.nodes('geo:place -:latlong*near=((34.1, -118.3), 10km)')
            self.len(0 + 1, nodes)
            nodes = await core.nodes('geo:place -:latlong*near=((34.1, -118.3), 50m)')
            self.len(2 + 1, nodes)

            q = f'geo:place={guid0} $latlong=:latlong | spin | geo:place +:latlong*near=($latlong, 5km)'
            self.len(2, await core.nodes(q))

            # Lifting nodes by *near=((latlong), accuracy)
            q = 'geo:place:latlong*near=((34.1, -118.3), 10km)'
            self.len(2, await core.nodes(q))

            q = 'geo:place:latlong*near=(("34.118560", "-118.300370"), 50m)'
            self.len(1, await core.nodes(q))

            q = 'geo:place:latlong*near=((0, 0), 50m)'
            self.len(0, await core.nodes(q))

            # Use a radius to lift nodes which will be inside the bounding box,
            # but outside the cmpr implemented using haversine filtering.
            q = 'geo:place:latlong*near=(("34.118560", "-118.300370"), 2600m)'
            self.len(1, await core.nodes(q))

        async with self.getTestCore() as core:

            await core._addDataModels(geotestmodel)

            # Lift behavior for a node whose has a latlong as their primary property
            nodes = await core.nodes('[(test:latlong=(10, 10) :dist=10m) '
                                    '(test:latlong=(10.1, 10.1) :dist=20m) '
                                    '(test:latlong=(3, 3) :dist=5m)]')
            self.len(3, nodes)

            nodes = await core.nodes('test:latlong*near=((10, 10), 5km)')
            self.len(1, nodes)
            nodes = await core.nodes('test:latlong*near=((10, 10), 30km)')
            self.len(2, nodes)

            # Ensure geo:dist inherits from IntBase correctly
            nodes = await core.nodes('test:latlong +:dist>5m')
            self.len(2, nodes)
            nodes = await core.nodes('test:latlong +:dist>=5m')
            self.len(3, nodes)
            nodes = await core.nodes('test:latlong +:dist<5m')
            self.len(0, nodes)
            nodes = await core.nodes('test:latlong +:dist<=5m')
            self.len(1, nodes)
            nodes = await core.nodes('test:latlong:dist>5m')
            self.len(2, nodes)
            nodes = await core.nodes('test:latlong:dist>=5m')
            self.len(3, nodes)
            nodes = await core.nodes('test:latlong:dist<5m')
            self.len(0, nodes)
            nodes = await core.nodes('test:latlong:dist<=5m')
            self.len(1, nodes)

            nodes = await core.nodes('test:latlong +:dist*range=(8m, 10m)')
            self.len(1, nodes)
            nodes = await core.nodes('test:latlong:dist*range=(8m, 10m)')
            self.len(1, nodes)

    async def test_geojson(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadTypeValu):
                opts = {'vars': {'geojson': {}}}
                nodes = await core.nodes('[ geo:place=* :geojson=$geojson ]', opts=opts)

            opts = {'vars': {'geojson': geojson0}}
            nodes = await core.nodes('[ geo:place=* :geojson=$geojson ]', opts=opts)

            opts = {'vars': {'geojson': geojson1}}
            nodes = await core.nodes('[ geo:place=* :geojson=$geojson ]', opts=opts)

            opts = {'vars': {'geojson': geojson2}}
            nodes = await core.nodes('[ geo:place=* :geojson=$geojson ]', opts=opts)

    async def test_geo_dist_offset(self):

        async with self.getTestCore() as core:

            await core._addDataModels(geotestmodel)
            nodes = await core.nodes('[ test:distoff=-3cm ]')
            self.eq(970, nodes[0].ndef[1])
            self.eq('-3.0 cm', await core.callStorm('test:distoff return($node.repr())'))
            with self.raises(s_exc.BadTypeValu):
                nodes = await core.nodes('[ test:distoff=-3km ]')

    async def test_model_geospace_telem(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ geo:telem=*
                    :time=20220618
                    :desc=foobar
                    :node=(test:int, 1234)

                    :place={[ geo:place=({"name": "Woot"}) ]}
                    :place:loc=us.ny.woot
                    :place:name=Woot
                    :place:country={[ pol:country=({"code": "us"}) ]}
                    :place:country:code=us
                    :place:address="123 main street"

                    :place:latlong=(10.1, 3.0)
                    :place:latlong:accuracy=10m

                    :phys:mass=10kg
                    :phys:width=5m
                    :phys:height=10m
                    :phys:length=20m
                    :phys:volume=1000m
                ]
            ''')
            self.eq(1655510400000000, nodes[0].get('time'))
            self.eq('foobar', nodes[0].get('desc'))
            self.eq('woot', nodes[0].get('place:name'))
            self.len(1, await core.nodes('geo:telem -> geo:place +:name=woot'))
            self.eq(('test:int', 1234), nodes[0].get('node'))
            self.len(1, await core.nodes('test:int=1234'))

            self.nn(nodes[0].get('place'))
            self.nn('us.ny.woot', nodes[0].get('place:loc'))
            self.nn('woot', nodes[0].get('place:name'))
            self.nn('123 main street', nodes[0].get('place:address'))
            self.eq((10.1, 3.0), nodes[0].get('place:latlong'))
            self.eq(10000, nodes[0].get('place:latlong:accuracy'))

            self.eq('10000', nodes[0].get('phys:mass'))
            self.eq(5000, nodes[0].get('phys:width'))
            self.eq(10000, nodes[0].get('phys:height'))
            self.eq(20000, nodes[0].get('phys:length'))
            self.eq(1000000, nodes[0].get('phys:volume'))

    async def test_model_geospace_area(self):

        async with self.getTestCore() as core:
            area = core.model.type('geo:area')
            self.eq(1, (await area.norm(1))[0])
            self.eq(1000000, (await area.norm('1 sq.km'))[0])
            self.eq('1.0 sq.km', area.repr(1000000))
            self.eq('1 sq.mm', area.repr(1))
            with self.raises(s_exc.BadTypeValu):
                await area.norm('asdf')
            with self.raises(s_exc.BadTypeValu):
                await area.norm('-1sq.km')
