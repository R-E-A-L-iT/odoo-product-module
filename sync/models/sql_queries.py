import logging
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class sql_queries(models.Model):

    _name = "sync.sql_runner"
    _description = "SQL Runner"

    def sql_queries_lockout(self):
        _db_name_prod = "https://www.r-e-a-l.it"
        _current_db_name = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')

        if (_db_name_prod == _current_db_name):
            raise UserError("Cannot Execute Raw SQL in Procuction Branch")

    # Log the list of all SQL table in odoo database
    def listSQLTables(self):
        self.sql_queries_lockout()

        _logger.info("listSQLTables")
        self.env.cr.execute("""
            SELECT table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE table_type = 'BASE TABLE'
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)
        raise UserError(res)

    # Log all attributs

    def listTableAttributs(self):
        self.sql_queries_lockout()

        _logger.info("listTableAttributs")
        self.env.cr.execute("""
        SELECT COLUMN_NAME 
        FROM information_schema.columns 
        WHERE table_name = 'product_template'
        """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    # Log all lines in sale_order table

    def listAllLineFromTable(self):
        self.sql_queries_lockout()

        _logger.info("listAllLineFromTable")
        self.env.cr.execute("""
            SELECT * 
            FROM product_attribute
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    # Log a specific sale order

    def listSpecificLineFromTable(self):
        self.sql_queries_lockout()

        _logger.info("listSpecificLineFromTable")
        self.env.cr.execute("""
            SELECT * 
            FROM product_template
            WHERE id = 16923
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    # Log a specific sale order
    def listSpecificProducft(self):
        self.sql_queries_lockout()

        _logger.info("listSpecificLineFromTable")
        self.env.cr.execute("""
            SELECT 
                PT.id,
                PT.name,
                PP.id
            FROM product_template PT
            INNER JOIN product_product PP ON
                PP.product_tmpl_id = PT.id
            WHERE PP.id = 19450
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    def listProductFromSpecificSaleOrder(self):
        self.sql_queries_lockout()

        _logger.info("listProductFromSpecificSaleOrder")
        self.env.cr.execute("""
            SELECT 
                SOL.id,
                SOL.order_id,
                SOL.product_id,
                PT.name            
            FROM sale_order_line SOL
            INNER JOIN sale_order SO ON 
                SO.id = SOL.order_id AND 
                SO.name = 'S00140'
            INNER JOIN product_product PP ON
                PP.id = SOL.product_id
            INNER JOIN product_template PT ON
                PT.id = PP.product_tmpl_id
            """)
        tables = self.env.cr.fetchall()
        res = "\n"
        for table in tables:
            res += str(table)
            res += "\n"
        _logger.info(res)

    def find_translations(self):
        self.sql_queries_lockout()

        _logger.info("listSpecificLineFromTable")
        self.env.cr.execute("""
            SELECT id, name 
            FROM product_template
            WHERE name = '5308158 - Cyclone WORKFLOW - 1 yr Subscription'
            """)
        tables = self.env.cr.fetchall()
        id = tables[0][0]
        self.env.cr.execute("\
            SELECT id, name\
            FROM base_update_translations\
            WHERE res_id= " + str(id))
        result = self.env.cr.fetchall()
        raise UserError(result)
