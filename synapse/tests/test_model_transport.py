import synapse.tests.utils as s_test

class TransportTest(s_test.SynTest):

    async def test_model_transport(self):

        async with self.getTestCore() as core:

            craft = (await core.nodes('[ transport:air:craft=* :tailnum=FF023 ]'))[0]
            tailnum = (await core.nodes('transport:air:tailnum=FF023 [ :type=fighter ]'))[0]
            flightnum = (await core.nodes('[ transport:air:flightnum="ua 2437" :carrier=* :from:port=IAD :to:port=LAS :stops=(IAD,VISI,LAS) ]'))[0]

            flight = (await core.nodes('''
                [ transport:air:flight=*
                    :num=UA2437
                    :scheduled:departure=20200202
                    :scheduled:arrival=20200203
                    :departed=2020020202
                    :arrived=202002020302
                    :carrier=*
                    :craft=*
                    :from:port=IAD
                    :to:port=LAS
                    :stops=(iad, visi, las)
                    :cancelled=true
                ]'''))[0]

            self.len(1, await core.nodes('transport:air:flight -> transport:air:craft'))

            self.eq('ua2437', flight.get('num'))
            self.eq(1580601600000, flight.get('scheduled:departure'))
            self.eq(1580688000000, flight.get('scheduled:arrival'))
            self.eq(1580608800000, flight.get('departed'))
            self.eq(1580612520000, flight.get('arrived'))
            self.true(flight.get('cancelled'))

            self.nn(flight.get('carrier'))

            self.eq('las', flight.get('to:port'))
            self.eq('iad', flight.get('from:port'))

            flightiden = flight.ndef[1]
            occup = (await core.nodes(f'[ transport:air:occupant=* :flight={flightiden} :seat=1A :contact=* ]'))[0]

            self.eq('1a', occup.get('seat'))
            self.len(1, await core.nodes('transport:air:occupant -> ps:contact'))
            self.len(1, await core.nodes('transport:air:occupant -> transport:air:flight'))

            telem = (await core.nodes('''
                [ transport:air:telem=*
                    :flight=*
                    :latlong=(20.22, 80.1111)
                    :loc=us
                    :place=*
                    :accuracy=10m
                    :altitude=9144m
                    :altitude:accuracy=10m
                    :time=20200202
                ]'''))[0]
            self.nn(telem.get('flight'))
            self.nn(telem.get('place'))
            self.eq((20.22, 80.1111), telem.get('latlong'))
            self.eq('us', telem.get('loc'))
            self.eq(10000, telem.get('accuracy'))
            self.eq(6380152800, telem.get('altitude'))
            self.eq(10000, telem.get('altitude:accuracy'))
            self.eq(1580601600000, telem.get('time'))

            vessel = (await core.nodes('''[
                transport:sea:vessel=*
                    :mmsi=123456789
                    :name="Slice of Life"
                    :flag=us
                    :imo="IMO 1234567"
                    :built=2020
                    :length=20m
                    :beam=10m
                ]'''))[0]
            self.eq('123456789', vessel.get('mmsi'))
            self.eq('slice of life', vessel.get('name'))
            self.eq('us', vessel.get('flag'))
            self.eq('imo1234567', vessel.get('imo'))
            self.eq(1577836800000, vessel.get('built'))
            self.eq(20000, vessel.get('length'))
            self.eq(10000, vessel.get('beam'))

            self.len(1, await core.nodes('transport:sea:vessel:imo^="IMO 123"'))

            seatelem = (await core.nodes('''[
                 transport:sea:telem=*
                    :time=20200202
                    :vessel=*
                    :latlong=(20.22, 80.1111)
                    :loc=us
                    :place=*
                    :accuracy=10m
                    :draft=20m
                    :airdraft=30m
            ]'''))[0]

            self.nn(seatelem.get('place'))
            self.eq((20.22, 80.1111), seatelem.get('latlong'))
            self.eq('us', seatelem.get('loc'))
            self.eq(10000, seatelem.get('accuracy'))
            self.eq(1580601600000, seatelem.get('time'))
            self.eq(20000, seatelem.get('draft'))
            self.eq(30000, seatelem.get('airdraft'))

            airport = (await core.nodes('transport:air:port=VISI [:name="Visi Airport" :place=*]'))[0]
            self.eq('visi', airport.ndef[1])
            self.eq('visi airport', airport.get('name'))
            self.nn(airport.get('place'))
