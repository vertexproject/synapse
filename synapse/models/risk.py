import synapse.exc as s_exc

import synapse.lib.chop as s_chop
import synapse.lib.types as s_types


class CvssV2(s_types.Str):

    async def _normPyStr(self, text, view=None):
        try:
            return s_chop.cvss2_normalize(text), {}
        except s_exc.BadDataValu as exc:
            mesg = exc.get('mesg')
            raise s_exc.BadTypeValu(name=self.name, valu=text, mesg=mesg) from None

class CvssV3(s_types.Str):

    async def _normPyStr(self, text, view=None):
        try:
            return s_chop.cvss3x_normalize(text), {}
        except s_exc.BadDataValu as exc:
            mesg = exc.get('mesg')
            raise s_exc.BadTypeValu(name=self.name, valu=text, mesg=mesg) from None
