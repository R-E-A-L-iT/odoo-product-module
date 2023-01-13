# -*- coding: utf-8 -*-
import gspread

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac


class sheetsAPI(models.Model):
    _name =  "sync.sheets"
    _inherit = "google.drive.config"
    _description = "Google Sheets API Handler"

    #Method that return the GoogleSheet Master DataBase TemplateID based on the DEV/PROD environnement
    #Input
    #   _db_name : The DB name of the environement that require the template ID
    #              to get it: self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    @staticmethod
    def get_master_database_template_id(_db_name):
        #Production DB name
        _db_name_prod = "https://www.r-e-a-l.it" 

        # R-E-A-L.iT Master Database
        _master_database_template_id_prod = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"

        # DEV R-E-A-L.iT Master Database
        _master_database_template_id_dev = "1PDuK9Nrf_YoVYsE7kZhcPmdTXPiqH7LQNGATLuVaxac"

        #Return the proper GoogleSheet Template ID base on the environement
        if (_db_name == _db_name_prod):
            return _master_database_template_id_prod
        else:
            return _master_database_template_id_dev  


    #Methode to read a googlesheet document.
    #Input
    #   psw             : The password creedential to access the document.
    #   spreadsheetID   : The template_id of the googlesheet
    #   sheet_num       : The index of the sheet to read.
    def getDoc(self, psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)
        
        doc = client.open_by_key(spreadsheetID)
        return doc.get_worksheet(sheet_num).get_all_values()
    