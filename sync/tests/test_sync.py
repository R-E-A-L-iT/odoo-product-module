from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync

#from odoo.tests.common import TransactionCase


class TestModuleDemo(TransactionCase):

    #def setUp(self):
    #    super(TestModuleDemo, self).setUp()

    def test_that_pass(self):
        self.assertEqual("AAA", "AAA")
        print('test_that_pass: Your test was successful!')
            
    def test_is_psw_empty(self):
        synce_model = self.env['sync.sync']
        print ("Model name: " + synce_model._name)
        print ("Model description: " + synce_model._description)

        result = synce_model.is_psw_empty(None)
        self.assertEqual(result, True)
        print('test_is_psw_empty: Your test was successful!')
           