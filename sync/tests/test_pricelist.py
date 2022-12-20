from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync


#To run the test, open the console and type : 
# odoo-bin --test-enable -i pricelist

class TestModulePricelist(TransactionCase):

    def setUp(self):
        super(TestModulePricelist, self).setUp()
        self.pricelist_data = [
	        ['SKU', 'Description', 'Price CAD', 'Price USD', 'Product Type', 'Tracking', 'Valid', 'Continue'], 
	        [	'SKU-1111',	'Name of SKU-1111', 'Description  of SKU-1111', '111.11', '131.11', 'product', 'serial', 'TRUE', 'TRUE'], 		
	        [	'SKU-2222', 'Name of SKU-2222', 'Description  of SKU-2222', '222.22', '262.22', 'product', 'serial', 'TRUE', 'TRUE'],
	        [	'SKU-3333', 'Name of SKU-3333', 'Description  of SKU-3333', '333.33', '393.33', 'product', 'serial', 'TRUE', 'FALSE'],
	        [	'Not valid SKU', 'Not valid Name', 'Not valid Description', '-1', '-1', 'Not valid product', 'Not valid serial', 'FALSE', 'FALSE'],		
        ]     
        self.sync_model = self.env['sync.sync']
        self.sync_pricelist = self.sync_model.getSync_pricelist("TEST_DATA_ODOO", self.pricelist_data)
       
    #def addProductToPricelist(self, product, pricelistName, price):
    def test_addProductToPricelist(self):
        product = None
        pricelistName = "cad"
        price = 22
        self.sync_pricelist.addProductToPricelist(product, pricelistName, price)
        self.assertEqual(True, True)

