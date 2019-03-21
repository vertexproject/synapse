import synapse.lib.syntax as s_syntax

import synapse.tests.utils as s_t_utils

class SyntaxTest(s_t_utils.SynTest):

    def test_isre_funcs(self):

        self.true(s_syntax.isCmdName('testcmd'))
        self.true(s_syntax.isCmdName('testcmd2'))
        self.true(s_syntax.isCmdName('testcmd.yup'))
        self.false(s_syntax.isCmdName('2testcmd'))
        self.false(s_syntax.isCmdName('testcmd:newp'))
        self.false(s_syntax.isCmdName('.hehe'))

        self.true(s_syntax.isUnivName('.hehe'))
        self.true(s_syntax.isUnivName('.hehe:haha'))
        self.true(s_syntax.isUnivName('.hehe.haha'))
        self.true(s_syntax.isUnivName('.hehe4'))
        self.true(s_syntax.isUnivName('.hehe.4haha'))
        self.true(s_syntax.isUnivName('.hehe:4haha'))
        self.false(s_syntax.isUnivName('.4hehe'))
        self.false(s_syntax.isUnivName('test:str'))
        self.false(s_syntax.isUnivName('test:str.hehe'))
        self.false(s_syntax.isUnivName('test:str.hehe:haha'))
        self.false(s_syntax.isUnivName('test:str.haha.hehe'))

        self.true(s_syntax.isFormName('test:str'))
        self.true(s_syntax.isFormName('t2:str'))
        self.true(s_syntax.isFormName('test:str:yup'))
        self.true(s_syntax.isFormName('test:str123'))
        self.false(s_syntax.isFormName('test'))
        self.false(s_syntax.isFormName('2t:str'))
        self.false(s_syntax.isFormName('.hehe'))
        self.false(s_syntax.isFormName('testcmd'))

        self.true(s_syntax.isPropName('test:str'))
        self.true(s_syntax.isPropName('test:str:tick'))
        self.true(s_syntax.isPropName('test:str:str123'))
        self.true(s_syntax.isPropName('test:str:123str'))
        self.true(s_syntax.isPropName('test:str:123:456'))
        self.true(s_syntax.isPropName('test:str.hehe'))
        self.true(s_syntax.isPropName('test:str.hehe'))
        self.true(s_syntax.isPropName('test:str.hehe.haha'))
        self.true(s_syntax.isPropName('test:str.hehe:haha'))
        self.false(s_syntax.isPropName('test'))
        self.false(s_syntax.isPropName('2t:str'))
        self.false(s_syntax.isPropName('.hehe'))
        self.false(s_syntax.isPropName('testcmd'))
