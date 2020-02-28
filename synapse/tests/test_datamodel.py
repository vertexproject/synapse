import synapse.exc as s_exc
import synapse.datamodel as s_datamodel
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

class DataModelTest(s_t_utils.SynTest):

    async def test_datmodel_formname(self):
        modl = s_datamodel.Model()
        mods = (
            ('hehe', {
                'types': (
                    ('derp', ('int', {}), {}),
                ),
                'forms': (
                    ('derp', {}, ()),
                ),
            }),
        )

        with self.raises(s_exc.BadFormDef):
            modl.addDataModels(mods)

    async def test_datamodel_dynamics(self):

        modl = s_datamodel.Model()

        with self.raises(s_exc.NoSuchType):
            modl.addType('he:he', 'ha:ha', {}, {})

        with self.raises(s_exc.NoSuchType):
            modl.addForm('he:he', {}, [])

        with self.raises(s_exc.BadPropDef):
            modl.addType('he:he', 'int', {}, {})
            modl.addForm('he:he', {}, [
                ('asdf',),
            ])

        with self.raises(s_exc.NoSuchProp):
            modl.delFormProp('he:he', 'newp')

        with self.raises(s_exc.NoSuchForm):
            modl.delFormProp('ne:wp', 'newp')

        with self.raises(s_exc.NoSuchUniv):
            modl.delUnivProp('newp')

    async def test_datamodel_del_prop(self):

        modl = s_datamodel.Model()

        modl.addType('foo:bar', 'int', {}, {})
        modl.addForm('foo:bar', {}, (('x', ('int', {}), {}), ))
        modl.addUnivProp('hehe', ('int', {}), {})
        modl.addFormProp('foo:bar', 'y', ('int', {}), {})

        self.nn(modl.prop('foo:bar:x'))
        self.nn(modl.prop('foo:bar:y'))
        self.nn(modl.prop('foo:bar.hehe'))

        self.nn(modl.form('foo:bar').prop('x'))
        self.nn(modl.form('foo:bar').prop('y'))
        self.nn(modl.form('foo:bar').prop('.hehe'))

        self.len(3, modl.propsbytype['int'])

        modl.delFormProp('foo:bar', 'y')

        self.nn(modl.prop('foo:bar:x'))
        self.nn(modl.prop('foo:bar.hehe'))
        self.nn(modl.form('foo:bar').prop('x'))
        self.nn(modl.form('foo:bar').prop('.hehe'))

        self.len(2, modl.propsbytype['int'])
        self.none(modl.prop('foo:bar:y'))
        self.none(modl.form('foo:bar').prop('y'))

        modl.delUnivProp('hehe')

        self.none(modl.prop('.hehe'))
        self.none(modl.form('foo:bar').prop('.hehe'))

    async def test_datamodel_form_refs_cache(self):
        async with self.getTestCore() as core:

            refs = core.model.form('test:comp').getRefsOut()
            self.len(1, refs['prop'])

            await core.addFormProp('test:comp', '_ipv4', ('inet:ipv4', {}), {})

            refs = core.model.form('test:comp').getRefsOut()
            self.len(2, refs['prop'])

            await core.delFormProp('test:comp', '_ipv4')

            refs = core.model.form('test:comp').getRefsOut()
            self.len(1, refs['prop'])
