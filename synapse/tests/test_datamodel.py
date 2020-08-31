import synapse.exc as s_exc
import synapse.datamodel as s_datamodel
import synapse.lib.module as s_module

import synapse.lib.modules as s_modules
import synapse.lib.types as s_types

import synapse.tests.utils as s_t_utils

depmodel = {
    'types': (
        ('test:dep:easy', ('test:str', {'deprecated': True}), {}),
        ('test:dep:comp', ('comp', {'fields': (('int', 'test:int'), ('str', 'test:dep:easy'))}), {}),
        ('test:dep:array', ('array', {'type': 'test:dep:easy'}), {})
    ),
    'forms': (
        ('test:dep:easy', {'deprecated': True}, (
            ('guid', ('test:guid', {'deprecated': True}), {}),
            ('array', ('test:dep:array', {}), {}),
            ('comp', ('test:dep:comp', {}), {}),
        )),
    ),
    'univs': (
        ('udep', ('test:dep:easy', {}), {}),
        ('pdep', ('test:str', {}), {'deprecated': True})
    )
}

class DeprecatedModel(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('test:dep', depmodel),
        )

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

    import contextlib

    async def test_model_deprecation(self):
        mods = ['synapse.tests.utils.TestModule',
                'synapse.tests.test_datamodel.DeprecatedModel',
                ]
        conf = {'modules': mods}
        import synapse.cortex as s_cortex

        at_mesg = 'Array type test:dep:array is based on a deprecated type test:dep:easy'

        with self.getAsyncLoggerStream('synaspe.lib.types', at_mesg) as tstream,
            with self.getTestDir() as dirn:
                core = await s_cortex.Cortex.anit(dirn, conf)

                print(core)
                print('8' * 120)
                msgs = await core.stormlist('[test:dep:easy=test1 :guid=(t1,)] [:guid=(t2,)]')
                self.stormIsInWarn('The form test:dep:easy is deprecated', msgs)
                self.stormIsInWarn('The property test:dep:easy:guid is deprecated or using a deprecated type', msgs)

                print('8' * 120)
                # Comp type warning is logged by the server, not sent back to users
                mesg = 'type test:dep:comp field str uses a deprecated type test:dep:easy'
                with self.getAsyncLoggerStream('synapse.lib.types', mesg) as cstream:
                    _ = await core.stormlist('[test:dep:easy=test2 :comp=(1, two)]')
                    self.true(cstream.wait(6))

                msgs = await core.stormlist('[test:str=tehe .pdep=beep]')
                self.stormIsInWarn('property test:str.pdep is deprecated', msgs)

                await core.fini()
