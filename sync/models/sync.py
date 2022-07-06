# -*- coding: utf-8 -*-

import ast
import logging
import json
import re

import requests
import werkzeug.urls
import base64

from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT, TIMEOUT
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class sync(models.Model):
	_name = "sync.sync"
	
	_inherit = "sync.sheets"
	
	DatabaseURL = fields.Char(default="")
	
	_description = "Sync App"
	
	# STARTING POINT
	def start_sync(self, psw=None):
		_logger.info("Starting Sync")
		
		# Checks authentication values
		if(psw == None):
			msg = "<h1>Sync Error</h1><p>Authentication values Missing</p>"
			_logger.info(msg)
			self.sendSyncReport(msg)
			return
		
		# next funct
		self.getSyncData(psw)
		_logger.info("Ending Sync")
		
	def getSyncData(self, psw):
		
		template_id = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"
		
		# get the database data; reading in the sheet
		try:
			sync_data = self.getDoc(psw, template_id, 0)
		except Exception as e:
			_logger.info(e)
			msg = "<h1>Source Document Invalid</h1><p>Sync Fail</p>"
			self.sendSyncReport(msg)
			return
		
		i = 1
		sheetIndex = ""
		syncType = ""
		msg = ""
		
		# loop through entries in first sheet
		while(True):
			_logger.info(sync_data[i][3])
			if(str(sync_data[i][3]) != "TRUE"):
				break
				
			sheetIndex = int(sync_data[i][1])
			syncType = str(sync_data[i][2])
			
			quit, msgr = self.getSyncValues(psw, template_id, sheetIndex, syncType)
			msg = msg + msgr
			i = i + 1
			if(quit):
				self.syncCancel(msg)
				return
			
		# error
		if(msg != ""):
			self.syncFail(msg)
			
	def getSyncValues(self, psw, template_id, sheetIndex, syncType):
		try:
			sheet = self.getDoc(psw, template_id, sheetIndex)
		except Exception as e:
			_logger.info(e)
			msg = ("<h1>Source Document Invalid<\h1><p>Page: %s</p><p>Sync Fail</p>" % sheetIndex) 
			self.sendSyncReport(msg)
			return False, ""
		
		# identify the type of sheet
		if(syncType == "Companies"):
			_logger.info("Companies")
			quit, msg = self.syncCompanies(sheet)
			_logger.info("Done Companies")
		elif(syncType == "Contacts"):
			_logger.info("Contacts")
			quit, msg = self.syncContacts(sheet)
			_logger.info("Done Contacts")
		elif(syncType == "Products"):
			_logger.info("Products")
			quit, msg = self.syncProducts(sheet)
			_logger.info("Done Products")
		elif(syncType == "CCP"):
			_logger.info("CCP")
			quit, msg = self.syncCCP(sheet)
			_logger.info("DoneCCP")
		elif(syncType == "Pricelist"):
			_logger.info("Pricelist")
			quit, msg = self.syncPricelist(sheet)
			_logger.info("Done Pricelist")
		elif(syncType == "WebHTML"):
			_logger.info("Website")
			quit, msg = self.syncWebCode(sheet)
			_logger.info("Done Website")
		_logger.info(str(quit) + "\n" + str(msg))
		return quit, msg
			
	# same pattern for all sync items
	def syncCompanies(self, sheet):
		
		# check sheet width to filter out invalid sheets
		sheetWidth = 17 # every company tab will have the same amount of columns (Same with others)
		columns = dict()
		missingColumn = False
		
		#Calculate Indexes
		if("Company Name" in  sheet[0]):
			columns["companyName"] = sheet[0].index("Company Name")
		else:
			missingColumn = True
			
		if("Phone" in  sheet[0]):
			columns["phone"] = sheet[0].index("Phone")
		else:
			missingColumn = True
		
		if("Website" in  sheet[0]):
			columns["website"] = sheet[0].index("Website")
		else:
			missingColumn = True
		
		if("Street" in  sheet[0]):
			columns["street"] = sheet[0].index("Street")
		else:
			missingColumn = True
			
		if("City" in  sheet[0]):
			columns["city"] = sheet[0].index("City")
		else:
			missingColumn = True
			
		if("State" in  sheet[0]):
			columns["state"] = sheet[0].index("State")
		else:
			missingColumn = True
			
		if("Country Code" in  sheet[0]):
			columns["country"] = sheet[0].index("Country Code")
		else:
			missingColumn = True
			
		if("Postal Code" in  sheet[0]):
			columns["postalCode"] = sheet[0].index("Postal Code")
		else:
			missingColumn = True
			
		if("Language" in  sheet[0]):
			columns["language"] = sheet[0].index("Language")
		else:
			missingColumn = True
			
		if("Email" in  sheet[0]):
			columns["email"] = sheet[0].index("Email")
		else:
			missingColumn = True
			
		if("Pricelist" in  sheet[0]):
			columns["pricelist"] = sheet[0].index("Pricelist")
		else:
			missingColumn = True
			
		if("OCOMID" in  sheet[0]):
			columns["id"] = sheet[0].index("OCOMID")
		else:
			missingColumn = True
			
		if("Valid" in  sheet[0]):
			columns["valid"] = sheet[0].index("Valid")
		else:
			missingColumn = True
			
		if("Continue" in  sheet[0]):
			columns["continue"] = sheet[0].index("Continue")
		else:
			missingColumn = True
			
		i = 1
		if(len(sheet[i]) != sheetWidth or missingColumn):
			msg = "<h1>Sync Page Invalid<h1>"
			self.sendSyncReport(msg)
			_logger.info("Sheet Width: " + str(len(sheet[i])))
			return True, msg
		
		r = ""
		msg = ""
		msg = self.startTable(msg, sheet, sheetWidth)
		
		# loop through all the rows
		while(True):
			
			# check if should continue
			if(str(sheet[i][columns["continue"]]) != "TRUE"):
				break
			
			# validation checks (vary depending on tab/function)
			if(str(sheet[i][columns["valid"]]) != "TRUE"):
				_logger.info("Invalid")
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			
			if(not self.check_id(str(sheet[i][columns["id"]]))):

				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			
			# if it gets here data should be valid
			try:
				
				# attempts to access existing item (item/row)
				external_id = str(sheet[i][columns["id"]])
				company_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
				if(len(company_ids) > 0):
					self.updateCompany(self.env['res.partner'].browse(company_ids[len(company_ids) - 1].res_id), sheet, sheetWidth, i, columns)
				else:
					self.createCompany(sheet, external_id, sheetWidth, i, columns)
			except Exception as e:
				_logger.info("Companies")
				_logger.info(e)
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				msg = self.endTable(msg)
				return True, msg
			i = i + 1
		msg = self.endTable(msg)
		return False, msg
			
	def updateCompany(self, company, sheet, sheetWidth, i, columns):
		
		# check if any update to item is needed and skips if there is none
		if(company.stringRep == str(sheet[i][:])):
			return
		
		# reads values and puts them in appropriate fields
		company.name = sheet[i][columns["companyName"]]
		company.phone = sheet[i][columns["phone"]]
		company.website = sheet[i][columns["website"]]
		company.street = sheet[i][columns["street"]]
		company.city = sheet[i][columns["city"]]
		if(sheet[i][columns["state"]] != ""):
			stateTup = self.env['res.country.state'].search([('code','=',sheet[i][columns["state"]])])
			if(len(stateTup) > 0):
				company.state_id = int(stateTup[0].id)
		name = sheet[i][columns["country"]]
		if(name != ""):
			if(name == "US"):
				name = "United States"
			company.country_id = int(self.env['res.country'].search([('name','=', name)])[0].id)
		company.zip = sheet[i][columns["postalCode"]]
		company.lang = sheet[i][columns["language"]]
		company.email = sheet[i][columns["language"]]
		if(sheet[i][columns["pricelist"]] != ""):
			company.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i][columns["pricelist"]])])[0].id)
		company.is_company = True
		
		_logger.info("Company StringRep")
		company.stringRep = str(sheet[i][:])
		
	# creates object and updates it
	def createCompany(self, sheet, external_id, sheetWidth, i, columns):
		ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
		company = self.env['res.partner'].create({'name': sheet[i][columns["companyName"]]})[0]
		ext.res_id = company.id
		self.updateCompany(company, sheet, sheetWidth, i, columns)
		
	# follows same pattern
	def syncContacts(self, sheet):
	
		sheetWidth = 17
		columns = dict()
		columnsMissing = False
		
		if("Name" in sheet[0]):
			columns["name"] = sheet[0].index("Name")
		else:
			columnsMissing = True
			
		if("Phone" in sheet[0]):
			columns["phone"] = sheet[0].index("Phone")
		else:
			columnsMissing = True
			
		if("Email" in sheet[0]):
			columns["email"] = sheet[0].index("Email")
		else:
			columnsMissing = True
			
		if("Company" in sheet[0]):
			columns["company"] = sheet[0].index("Company")
		else:
			columnsMissing = True
		
		if("Street Address" in sheet[0]):
			columns["streetAddress"] = sheet[0].index("Street Address")
		else:
			columnsMissing = True
			
		if("City" in sheet[0]):
			columns["city"] = sheet[0].index("City")
		else:
			columnsMissing = True
			
		if("State/Region" in sheet[0]):
			columns["state"] = sheet[0].index("State/Region")
		else:
			columnsMissing = True
			
		if("Country Code" in sheet[0]):
			columns["country"] = sheet[0].index("Country Code")
		else:
			columnsMissing = True
			
		if("Postal Code" in sheet[0]):
			columns["postalCode"] = sheet[0].index("Postal Code")
		else:
			columnsMissing = True
			
		if("Pricelist" in sheet[0]):
			columns["pricelist"] = sheet[0].index("Pricelist")
		else:
			columnsMissing = True
			
		if("Language" in sheet[0]):
			columns["language"] = sheet[0].index("Language")
		else:
			columnsMissing = True
			
		if("OCID" in sheet[0]):
			columns["id"] = sheet[0].index("OCID")
		else:
			columnsMissing = True
			
		if("Valid" in sheet[0]):
			columns["valid"] = sheet[0].index("Valid")
		else:
			columnsMissing = True
			
		if("Continue" in sheet[0]):
			columns["continue"] = sheet[0].index("Continue")
		else:
			columnsMissing = True
		
		i = 1
		if(len(sheet[i]) != sheetWidth or columnsMissing):
			msg = "<h1>Sync Page Invalid<h1>"
			self.sendSyncReport(msg)
			_logger.info("Sheet Width: " + str(len(sheet[i])))
			return True, msg
		r = ""
		msg = ""
		msg = self.startTable(msg, sheet, sheetWidth)
		while(True):
			
			if(i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
				break
				
			if(str(sheet[i][columns["valid"]]) != "TRUE"):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
				
			if(not self.check_id(str(sheet[i][columns["id"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
				
			if(not self.check_id(str(sheet[i][columns["company"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			try:
				external_id = str(sheet[i][columns["id"]])
			
				contact_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
				if(len(contact_ids) > 0):
					self.updateContacts(self.env['res.partner'].browse(contact_ids[len(contact_ids) - 1].res_id), sheet, sheetWidth, i, columns)
				else:
					self.createContacts(sheet, external_id, sheetWidth, i, columns)
			except Exception as e:
				_logger.info("Contacts")
				_logger.info(e)
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				msg = self.endTable(msg)
				return True, msg
			i = i + 1
		msg = self.endTable(msg)
		return False, msg
	
	# follows same pattern
	def updateContacts(self, contact, sheet, sheetWidth, i, columns):
		
		if(contact.stringRep == str(sheet[i][:])):
			return
		
		contact.name = sheet[i][columns["name"]]
		contact.phone = sheet[i][columns["phone"]]
		contact.email = sheet[i][columns["email"]]
		if(sheet[i][columns["company"]] != ""):
			contact.parent_id = int(self.env['ir.model.data'].search([('name','=',sheet[i][columns["company"]]), ('model', '=', 'res.partner')])[0].res_id)
		contact.street = sheet[i][columns["streetAddress"]]
		contact.city = sheet[i][columns["city"]]
		if(sheet[i][columns["state"]] != ""):
			stateTup = self.env['res.country.state'].search([('code','=',sheet[i][columns["state"]])])
			if(len(stateTup) > 0):
				contact.state_id = int(stateTup[0].id)
		
		name = sheet[i][columns["country"]]
		if(name != ""):
			if(name == "US"):
				name = "United States"
			contact.country_id = int(self.env['res.country'].search([('name','=',name)])[0].id)
		contact.zip = sheet[i][columns["postalCode"]]
		
		contact.lang = sheet[i][columns["language"]]
		
		if(sheet[i][columns["pricelist"]] != ""):
			contact.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i][columns["pricelist"]])])[0].id)
		contact.is_company = False
		
		_logger.info("Contact String Rep")
		contact.stringRep = str(sheet[i][:])
	
	# follows same pattern
	def createContacts(self, sheet, external_id, sheetWidth, i, columns):
		ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
		contact = self.env['res.partner'].create({'name': sheet[i][columns["name"]]})[0]
		ext.res_id = contact.id
		self.updateContacts(contact, sheet, sheetWidth, i, columns)
	
	# follows same pattern
	def syncProducts(self, sheet):
	
		sheetWidth = 7
		i = 1
		
		columns = dict()
		columnsMissing = False
		
		if("SKU" in sheet[0]):
			columns["sku"] = sheet[0].index("SKU")
		else:
			columnsMissing = True
			
		if("Name" in sheet[0]):
			columns["name"] = sheet[0].index("Name")
		else:
			columnsMissing = True
			
		if("Description" in sheet[0]):
			columns["description"] = sheet[0].index("Description")
		else:
			columnsMissing = True
			
		if("Price" in sheet[0]):
			columns["price"] = sheet[0].index("Price")
		else:
			columnsMissing = True
			
		if("Product Type" in sheet[0]):
			columns["type"] = sheet[0].index("Product Type")
		else:
			columnsMissing = True
			
		if("Tracking" in sheet[0]):
			columns["tracking"] = sheet[0].index("Tracking")
		else:
			columnsMissing = True
			
		if("Valid" in sheet[0]):
			columns["valid"] = sheet[0].index("Valid")
		else:
			columnsMissing = True
		
		if(len(sheet[i]) != sheetWidth or columnsMissing):
			msg = "<h1>Sync Page Invalid<h1>"
			self.sendSyncReport(msg)
			_logger.info("Sheet Width: " + str(len(sheet[i])))
			return True, msg
		
		r = ""
		msg = ""
		msg = self.startTable(msg, sheet, sheetWidth)
		while(True):
			if(i == len(sheet) or str(sheet[i][columns["valid"]]) != "TRUE"):
				break
				
			if(not self.check_id(str(sheet[i][columns["sku"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			if(not self.check_price(sheet[i][columns["price"]])):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			
			try:
				external_id = str(sheet[i][columns["sku"]])
			
				product_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'product.template')])
				if(len(product_ids) > 0):
					self.updateProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i, columns)
				else:
					self.createProducts(sheet, external_id, sheetWidth, i, columns)
			except Exception as e:
				_logger.info("Products")
				_logger.info(e)
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				msg = self.endTable(msg)
				return True, msg
			i = i + 1
		msg = self.endTable(msg)
		return False, msg
	
	# follows same pattern
	def updateProducts(self, product, sheet, sheetWidth, i, columns):
		
		if(product.stringRep == str(sheet[i][:])):
			return
		
		product.name = sheet[i][columns["name"]]
		product.description_sale = sheet[i][columns["description"]]
		product.price = sheet[i][columns["price"]]
		product.tracking = "serial"
		product.type = "product"
		
		_logger.info("Product String Rep")
		product.stringRep = str(sheet[i][:])
	
	# follows same pattern
	def createProducts(self, sheet, external_id, sheetWidth, i, columns):
		ext = self.env['ir.model.data'].create({'name': external_id, 'model':"product.template"})[0]
		product = self.env['product.template'].create({'name': sheet[i][columns["name"]]})[0]
		ext.res_id = product.id
		self.updateProducts(product, sheet, sheetWidth, i, columns)
	
	# follows same pattern
	def syncCCP(self, sheet):
	
		sheetWidth = 9
		
		columns = dict()
		columnsMissing = False
		
		if("Owner ID" in  sheet[0]):
			columns["ownerId"] = sheet[0].index("Owner ID")
		else:
			columnsMissing = True
		
		if("EID/SN" in  sheet[0]):
			columns["eidsn"] = sheet[0].index("EID/SN")
		else:
			columnsMissing = True
			
		if("External ID" in  sheet[0]):
			columns["externalId"] = sheet[0].index("External ID")
		else:
			columnsMissing = True
		
		if("Product Code" in  sheet[0]):
			columns["code"] = sheet[0].index("Product Code")
		else:
			columnsMissing = True
			
		if("Product Name" in  sheet[0]):
			columns["name"] = sheet[0].index("Product Name")
		else:
			columnsMissing = True
			
		if("Expiration Date" in  sheet[0]):
			columns["date"] = sheet[0].index("Expiration Date")
		else:
			columnsMissing = True
			
		if("Valid" in  sheet[0]):
			columns["valid"] = sheet[0].index("Valid")
		else:
			columnsMissing = True
			
		if("Continue" in  sheet[0]):
			columns["continue"] = sheet[0].index("Continue")
		else:
			columnsMissing = True
			
		
		
		i = 1
		if(len(sheet[i]) != sheetWidth or columnsMissing):
			msg = "<h1>Sync Page Invalid<h1>\n<h2>syncCCP function</h2>"
			self.sendSyncReport(msg)
			_logger.info("Sheet Width: " + str(len(sheet[i])))
			return True, msg
		r = ""
		msg = ""
		msg = self.startTable(msg, sheet, sheetWidth)
		while(True):
			if(i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
				break
			if(str(sheet[i][columns["valid"]]) != "TRUE"):
				i = i + 1
				continue

			if(not self.check_id(str(sheet[i][columns["externalId"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			try:
				external_id = str(sheet[i][columns["externalId"]])
			
				ccp_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'stock.production.lot')])
				if(len(ccp_ids) > 0):
					self.updateCCP(self.env['stock.production.lot'].browse(ccp_ids[-1].res_id), sheet, sheetWidth, i, columns)
				else:
					self.createCCP(sheet, external_id, sheetWidth, i, columns)
			except Exception as e:
				_logger.info("CCP")
				_logger.info(e)
				_logger.info(i)
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				msg = self.endTable(msg)
				msg = msg + str(e)
				return True, msg
			i = i + 1
		msg = self.endTable(msg)
		return False, msg

	# follows same pattern        
	def updateCCP(self, ccp_item, sheet, sheetWidth, i, columns):        
		if(ccp_item.stringRep == str(sheet[i][:])):
			return
		
#         if(i == 8):
		_logger.info("name")
		ccp_item.name = sheet[i][columns["eidsn"]]
		
#         if(i == 8):
		_logger.info("id")
		product_ids = self.env['product.product'].search([('name', '=', sheet[i][columns["name"]])])
		_logger.info(str(len(product_ids)))
		_logger.info(str(sheet[i][columns["name"]]))
		
#         if(i == 8):
		_logger.info("Id Tupple")
		ccp_item.product_id = product_ids[-1].id

		
#         if(i == 8):
		_logger.info("owner")
		owner_ids = self.env['ir.model.data'].search([('name', '=', sheet[i][columns["ownerId"]]), ('model', '=', 'res.partner')])
		if (len(owner_ids) == 0):
			_logger.info("No owner")
		
		
#         if(i == 8):
		_logger.info("Owner Tupple")
		ccp_item.owner = owner_ids[-1].res_id
		if(sheet[i][columns["date"]] != "FALSE"):
			ccp_item.expire = sheet[i][columns["date"]]
		else:
			ccp_item.expire = None
			
		_logger.info("CCP String Rep")
		ccp_item.stringRep = str(sheet[i][:])
	
	# follows same pattern
	def createCCP(self, sheet, external_id, sheetWidth, i, columns):
		ext = self.env['ir.model.data'].create({'name': external_id, 'model':"stock.production.lot"})[0]
		
		product_ids = self.env['product.product'].search([('name', '=', sheet[i][columns["name"]])])
		
		product_id = product_ids[len(product_ids) - 1].id
		
		company_id = self.env['res.company'].search([('id', '=', 1)]).id
		
		ccp_item = self.env['stock.production.lot'].create({'name': sheet[i][columns["eidsn"]],
															'product_id': product_id, 'company_id': company_id})[0]
		ext.res_id = ccp_item.id
		self.updateCCP(ccp_item, sheet, sheetWidth, i, columns)
	
	# follows same pattern
	def syncPricelist(self, sheet):
		sheetWidth = 22
		i = 1
		
		columns = dict()
		columnsMissing = False
		
		if("SKU" in sheet[0]):
			columns["sku"] = sheet[0].index("SKU")
		else:
			columnsMissing = True

		if("EN-Name" in sheet[0]):
			columns["eName"] = sheet[0].index("EN-Name")
		else:
			columnsMissing = True
			
		if("EN-Description" in sheet[0]):
			columns["eDisc"] = sheet[0].index("EN-Description")
		else:
			columnsMissing = True
			
		if("FR-Name" in sheet[0]):
			columns["fName"] = sheet[0].index("FR-Name")
		else:
			columnsMissing = True
			
		if("FR-Description" in sheet[0]):
			columns["fDisc"] = sheet[0].index("FR-Description")
		else:
			columnsMissing = True
		
		if("Price" in sheet[0]):
			columns["canPrice"] = sheet[0].index("Price")
		else:
			columnsMissing = True
			
		if("USD Price" in sheet[0]):
			columns["usPrice"] = sheet[0].index("USD Price")
		else:
			columnsMissing = True
			
		if("Publish_CA" in sheet[0]):
			columns["canPublish"] = sheet[0].index("Publish_CA")
		else:
			columnsMissing = True
			
		if("Publish_USA" in sheet[0]):
			columns["usPublish"] = sheet[0].index("Publish_USA")
		else:
			columnsMissing = True
			
		if("Can_Be_Sold" in sheet[0]):
			columns["canBeSold"] = sheet[0].index("Can_Be_Sold")
		else:
			columnsMissing = True
			
		if("E-Commerce_Website_Code" in sheet[0]):
			columns["ecommerceWebsiteCode"] = sheet[0].index("E-Commerce_Website_Code")
		else:
			columnsMissing = True
		
		if("CAN PL SEL" in sheet[0]):
			columns["canPricelist"] = sheet[0].index("CAN PL SEL")
		else:
			columnsMissing = True
		
		if("CAN PL ID" in sheet[0]):
			columns["canPLID"] = sheet[0].index("CAN PL ID")
		else:
			columnsMissing = True
			
		if("USD PL SEL" in sheet[0]):
			columns["usPricelist"] = sheet[0].index("USD PL SEL")
		else:
			columnsMissing = True
		
		if("US PL ID" in sheet[0]):
			columns["usPLID"] = sheet[0].index("US PL ID")
		else:
			columnsMissing = True
		
		if("Continue" in sheet[0]):
			columns["continue"] = sheet[0].index("Continue")
		else:
			columnsMissing = True
		
		if("Valid" in sheet[0]):
			columns["valid"] = sheet[0].index("Valid")
		else:
			columnsMissing = True
		
		if(len(sheet[i]) != sheetWidth or columnsMissing):
			msg = "<h1>Pricelist page Invalid</h1>\n<p>Sheet width is: " + str(len(sheet[i])) + "</p>"
			self.sendSyncReport(msg)
			_logger.info("Sheet Width: " + str(len(sheet[i])))
			return True, msg
		r = ""
		msg = ""
		msg = self.startTable(msg, sheet, sheetWidth)
		while(True):
			if(i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
				break
			if(str(sheet[i][columns["valid"]]) != "TRUE"):
				i = i + 1
				continue
			
			if(not self.check_id(str(sheet[i][columns["sku"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			if(not self.check_id(str(sheet[i][columns["canPLID"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			if(not self.check_id(str(sheet[i][columns["usPLID"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			if(not self.check_price(sheet[i][columns["canPrice"]])):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			if(not self.check_price(sheet[i][columns["usPrice"]])):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			   
			try:
				product, new= self.pricelistProduct(sheet, sheetWidth, i, columns)
				if(product.stringRep == str(sheet[i][:])):
					i = i + 1
					continue

				self.pricelistCAN(product, sheet, sheetWidth, i, columns)
				self.pricelistUS(product, sheet, sheetWidth, i, columns)
				
				if(new):
					_logger.info("Blank StringRep")
					product.stringRep = ""
				else:
					_logger.info("Pricelist Price StringRep")
					product.stringRep = str(sheet[i][:])
			except Exception as e:
				_logger.info(e)
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				return True, msg
			
			i = i + 1
		msg = self.endTable(msg)
		return False, msg
	
	def pricelistProduct(self, sheet, sheetWidth, i, columns):
		external_id = str(sheet[i][columns["sku"]])  
		product_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'product.template')])
		if(len(product_ids) > 0): 
			return self.updatePricelistProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i, columns), False
		else:
			return self.createPricelistProducts(sheet, external_id, sheetWidth, i, columns), True
	
	def pricelistCAN(self, product, sheet, sheetWidth, i, columns):
		external_id = str(sheet[i][columns["canPLID"]])
		pricelist_id = self.env['product.pricelist'].search([('name','=','CAN Pricelist')])[0].id
		pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
		if(len(pricelist_item_ids) > 0): 
			pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
			pricelist_item.product_tmpl_id = product.id
			pricelist_item.applied_on = "1_product"
			if(str(sheet[i][columns["canPrice"]]) != " " and str(sheet[i][columns["canPrice"]]) != ""):
				pricelist_item.fixed_price = float(sheet[i][columns["canPrice"]])
		else:
			pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
			pricelist_item.applied_on = "1_product"
			if(str(sheet[i][columns["canPrice"]]) != " " and str(sheet[i][columns["canPrice"]]) != ""):
				pricelist_item.fixed_price = sheet[i][columns["canPrice"]]
	
	def pricelistUS(self, product, sheet, sheetWidth, i, columns):
		external_id = str(sheet[i][columns["usPLID"]])
		pricelist_id = self.env['product.pricelist'].search([('name','=','USD Pricelist')])[0].id
		pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
		if(len(pricelist_item_ids) > 0): 
			pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
			pricelist_item.product_tmpl_id = product.id
			pricelist_item.applied_on = "1_product"
			if(str(sheet[i][columns["usPrice"]]) != " " and str(sheet[i][columns["usPrice"]]) != ""):
				pricelist_item.fixed_price = sheet[i][columns["usPrice"]]
				
				
		else:
			pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
			pricelist_item.applied_on = "1_product"
			if(str(sheet[i][columns["usPrice"]]) != " " and str(sheet[i][columns["usPrice"]]) != ""):
				pricelist_item.fixed_price = sheet[i][columns["usPrice"]]
	
	def updatePricelistProducts(self, product, sheet, sheetWidth, i, columns, new=False):
		
		if(product.stringRep == str(sheet[i][:]) and product.stringRep != ""):
			return product
		
		product.name = sheet[i][columns["eName"]]
		product.description_sale = sheet[i][columns["eDisc"]]
		
		if(str(sheet[i][columns["canPrice"]]) != " " and str(sheet[i][columns["canPrice"]]) != ""):
			product.price = sheet[i][columns["canPrice"]]
		

#         _logger.info(str(sheet[i][7]))
#         if(len(str(sheet[i][7])) > 0):
#             url = str(sheet[i][7])
#             req = requests.get(url, stream=True)
#             if(req.status_code == 200):
#                 product.image_1920 = req.content

		if (str(sheet[i][columns["canPublish"]]) == "TRUE"):
			product.is_published = True
		else:
			product.is_published = False
		if (str(sheet[i][columns["canPublish"]]) == "TRUE"):
			product.is_ca = True
		else:
			product.is_ca = False
		if (str(sheet[i][columns["usPublish"]]) == "TRUE"):
			product.is_us = True
		else:
			product.is_us = False
			
		if(str(sheet[i][columns["canBeSold"]]) == "TRUE"):
			product.sale_ok = True
		else:
			product.sale_ok = False
			
		product.storeCode = sheet[i][columns["ecommerceWebsiteCode"]]
		product.tracking = "serial"
		product.type = "product"
		
		if(not new):
			_logger.info("Translate")
			self.translatePricelist(product, sheet, sheetWidth, i, columns["fName"], columns["fDisc"], "fr_CA", new)
			self.translatePricelist(product, sheet, sheetWidth, i, columns["eName"], columns["eDisc"], "en_CA", new)
			self.translatePricelist(product, sheet, sheetWidth, i, columns["eName"], columns["eDisc"], "en_US", new)
		
		return product
		
	def translatePricelist(self, product, sheet, sheetWidth, i, nameI, descriptionI, lang, new):
		if(new == True):
			return
		else:
			product_name = self.env['ir.translation'].search([('res_id', '=', product.id),
																	 ('name', '=', 'product.template,name'),
																	('lang', '=', lang)])
			if(len(product_name) > 0):
				product_name[-1].value = sheet[i][nameI]

			else:
				product_name_new = self.env['ir.translation'].create({'name':'product.template,name', 
																			'lang': lang,
																			'res_id': product.id})[0]
				product_name_new.value = sheet[i][nameI]
			

			product_description = self.env['ir.translation'].search([('res_id', '=', product.id),
																	 ('name', '=', 'product.template,description_sale'),
																	('lang', '=', lang)])

			if(len(product_description) > 0):
				product_description[-1].value = sheet[i][descriptionI]
			else:
				product_description_new = self.env['ir.translation'].create({'name':'product.template,description_sale', 
																			'lang':lang,
																			'res_id': product.id})[0]
				product_description_new.value = sheet[i][descriptionI]
			return
	
	def createPricelistProducts(self, sheet, external_id, sheetWidth, i, columns):
		ext = self.env['ir.model.data'].create({'name': external_id, 'model':"product.template"})[0]
		product = self.env['product.template'].create({'name': sheet[i][columns["eName"]]})[0]
		ext.res_id = product.id
		self.updatePricelistProducts(product, sheet, sheetWidth, i, columns, new=True)
		return product
	
	def syncWebCode(self, sheet):
		# check sheet width to filter out invalid sheets
		sheetWidth =  8# every company tab will have the same amount of columns (Same with others)
		columns = dict()
		missingColumn = False
		
		#Calculate Indexes
		if("Page ID" in  sheet[0]):
			columns["id"] = sheet[0].index("Page ID")
		else:
			missingColumn = True

		if("HTML" in  sheet[0]):
			columns["html"] = sheet[0].index("HTML")
		else:
			missingColumn = True

		if("Valid" in  sheet[0]):
			columns["valid"] = sheet[0].index("Valid")
		else:
			missingColumn = True

		if("Continue" in  sheet[0]):
			columns["continue"] = sheet[0].index("Continue")
		else:
			missingColumn = True

		if(len(sheet[0]) != sheetWidth or missingColumn):
			msg = "<h1>Pricelist page Invalid</h1>\n<p>Sheet width is: " + str(len(sheet[0])) + "</p>"
			self.sendSyncReport(msg)
			_logger.info("Sheet Width: " + str(len(sheet[0])))
			return True, msg
		
		i = 1
		msg = ""
		msg = self.startTable(msg, sheet, sheetWidth)
		while(True):
			if(i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
				break

			if(not self.check_id(str(sheet[i][columns["id"]]))):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue

			if(not sheet[i][columns["valid"]] == "TRUE"):
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				i = i + 1
				continue
			
			try:
				external_id = str(sheet[i][columns["id"]])
				_logger.info(external_id)
				pageIds = self.env['ir.model.data'].search([('name','=', external_id)])
				if(len(pageIds) > 0):
					page = self.env['ir.ui.view'].browse(pageIds[-1].res_id)
				else:
					msg = self.buildMSG(msg, sheet, sheetWidth, i)
					_logger.info(str(external_id) + " Page Not Created")
					return True, msg
				i = i + 1
			except Exception as e:
				_logger.info(e)
				msg = self.buildMSG(msg, sheet, sheetWidth, i)
				return True, msg
		return False, msg

	def check_id(self, id):
		if(" " in id):
			_logger.info("ID: " + str(id))
			return False
		else:
			return True
	
	def check_price(self, price):
		if(price in ("", " ")):
			return True
		try:
			float(price)
			return True
		except Exception as e:
			_logger.info(e)
			return False
	
	def buildMSG(self, msg, sheet, sheetWidth, i):
		if(msg == ""):
			msg = self.startTable(msg, sheet, sheetWidth, True)
		msg = msg + "<tr>"
		j = 0
		while(j < sheetWidth):
			msg = msg + "<td>" + str(sheet[i][j])
			j = j + 1
		msg = msg + "</tr>"
		return msg
			
	def startTable(self, msg, sheet, sheetWidth, force=False):
		if(force):
			msg = msg + "<table><tr>"
			j = 0
			while(j < sheetWidth):
				msg = msg + "<th><strong>" + str(sheet[0][j]) + "</strong></th>"
				j = j + 1
			msg = msg + "</tr>"
		elif(msg != ""):
			msg = msg + "<table><tr>"
			while(j < sheetWidth):
				msg = msg + "<th>" + str(sheet[0][j]) + "</th>"
				j = j + 1
			msg = msg + "</tr>"
			
		return msg
	
	def endTable(self, msg):
		if(msg != ""):
			msg = msg + "</table>"
		return msg
			
	
	def syncCancel(self, msg):
		link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
		msg = "<h1>The Sync Process Was forced to quit and no records were updated</h1><h1> The Following Rows of The Google Sheet Table are invalid<h1>" + msg + "<a href=\"" + link + "\">Manual Retry</a>"
		_logger.info(msg)
		self.sendSyncReport(msg)
	
	def syncFail(self, msg):
		link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
		msg = "<h1>The Following Rows of The Google Sheet Table are invalid and were not Updated to Odoo</h1>" + msg + "<a href=\"" + link + "\">Manual Retry</a>"
		_logger.info(msg)
		self.sendSyncReport(msg)
	
	def sendSyncReport(self, msg):
		values = {'subject': 'Sync Report'}
		message = self.env['mail.message'].create(values)[0]
		
		values = {'mail_message_id': message.id}
		
		email = self.env['mail.mail'].create(values)[0]
		email.body_html = msg
		email.email_to = "sync@store.r-e-a-l.it"
		email_id = {email.id}
		email.process_email_queue(email_id)  

		
		#Send another Sync Report
		values = {'subject': 'Sync Report'}
		message = self.env['mail.message'].create(values)[0]
		
		values = {'mail_message_id': message.id}
		
		email = self.env['mail.mail'].create(values)[0]
		email.body_html = msg
		email.email_to = "ty@r-e-a-l.it"
		email_id = {email.id}
		email.process_email_queue(email_id)   
