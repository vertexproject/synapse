import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types

logger = logging.getLogger(__name__)

class SynUser(s_types.Guid):

    async def _normPyStr(self, text, view=None):

        core = self.modl.core
        if core is not None:

            # direct use of an iden takes precedence...
            user = core.auth.user(text)
            if user is not None:
                return user.iden, {}

            user = core.auth._getUserByName(text)
            if user is not None:
                return user.iden, {}

        if text == '*':
            mesg = f'{self.name} values must be a valid username or a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        try:
            return await s_types.Guid._normPyStr(self, text)
        except s_exc.BadTypeValu:
            mesg = f'No user named {text} and value is not a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text) from None

    def repr(self, iden):

        core = self.modl.core
        if core is not None:
            user = core.auth.user(iden)
            if user is not None:
                return user.name

        return iden

class SynRole(s_types.Guid):

    async def _normPyStr(self, text, view=None):

        core = self.modl.core
        if core is not None:

            # direct use of an iden takes precedence...
            role = core.auth.role(text)
            if role is not None:
                return role.iden, {}

            role = core.auth._getRoleByName(text)
            if role is not None:
                return role.iden, {}

        if text == '*':
            mesg = f'{self.name} values must be a valid rolename or a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text)

        try:
            return await s_types.Guid._normPyStr(self, text)
        except s_exc.BadTypeValu:
            mesg = f'No role named {text} and value is not a guid.'
            raise s_exc.BadTypeValu(mesg=mesg, name=self.name, valu=text) from None

    def repr(self, iden):

        core = self.modl.core
        if core is not None:
            role = core.auth.role(iden)
            if role is not None:
                return role.name

        return iden

async def _liftRuntSynCmd(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = view.core.stormcmds.get(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in view.core.getStormCmds():
        yield item[1].getRuntPode()

async def _liftRuntSynForm(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.form(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.forms.values()):
        yield item.getRuntPode()

async def _liftRuntSynProp(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.prop(cmprvalu[1])
        if item is not None:
            if item.isform:
                yield item.getRuntPropPode()
            else:
                yield item.getRuntPode()
        return

    for item in prop.modl.getProps():
        if item.isform:
            yield item.getRuntPropPode()
        else:
            yield item.getRuntPode()

async def _liftRuntSynType(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.type(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.types.values()):
        yield item.getRuntPode()

async def _liftRuntSynTagProp(view, prop, cmprvalu=None):

    if prop.isform and cmprvalu is not None and cmprvalu[0] == '=':
        item = prop.modl.tagprops.get(cmprvalu[1])
        if item is not None:
            yield item.getRuntPode()
        return

    for item in list(prop.modl.tagprops.values()):
        yield item.getRuntPode()
