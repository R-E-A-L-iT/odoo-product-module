import logging
import re
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class utilities:
    
    # this is a new and improved sync report function that i will move other files to using, which uses a nice xml template and formats the errors nicely.
    
    # report_content: dict of all errors to send
    # sync_type: the sync type to be printed in the header, like CCP or pricelist
    
    @staticmethod
    def send_report(report_content, sync_type):
        try:
            
            template = database.env.ref("sync.sync_report_template")
            
            body_content = "\n".join(report_content)
            template_values = {
                "subject": f"Sync Report for type: {sync_type}",
                "body_content": body_content,
                "email_to": "sync@store.r-e-a-l.it",
            }
            
            template.with_context(database.env.context).send_mail(0, email_values=template_values, force_send=True)
            _logger.info("send_report: Sync report successfully sent to sync@store.r-e-a-l.it.")
        except Exception as e:
            _logger.error("send_report: Failed to send sync report email: %s", str(e), exc_info=True)
    
    @staticmethod
    def check_id(id):
        if (" " in id):
            _logger.info("ID: " + str(id))
            return False
        else:
            return True

    @staticmethod
    def check_price(price):
        if (price in ("", " ")):
            return True
        try:
            float(price)
            return True
        except Exception as e:
            _logger.info(e)
            return False

    @staticmethod
    def check_date(date) -> bool:
        """
        Validates a date string to ensure it matches the expected format.
        Logs detailed reasons if the date is invalid.

        Args:
            date (str): The date string to validate.

        Returns:
            bool: True if the date is valid, False otherwise.
        """
        if str(date) == "FALSE":
            return True  # "FALSE" is treated as valid by design

        # Check if the date matches the expected format (YYYY-MM-DD)
        date_pattern = r'^\d{4}-\d{1,2}-\d{1,2}$'
        if not re.match(date_pattern, str(date)):
            _logger.error(f"check_date: Date '{date}' does not match the format YYYY-MM-DD.")
            return False

        # Split the date into year, month, day
        try:
            year, month, day = map(int, date.split('-'))
        except ValueError:
            _logger.error(f"check_date: Date '{date}' cannot be split into year, month, and day.")
            return False

        # Check year range
        if year < 1900 or year > 2100:
            _logger.error(f"check_date: Year '{year}' in date '{date}' is out of range (1900-2100).")
            return False

        # Check month range
        if month < 1 or month > 12:
            _logger.error(f"check_date: Month '{month}' in date '{date}' is out of range (1-12).")
            return False

        # Check day range for the given month
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
            days_in_month[1] = 29  # Adjust for leap years

        if day < 1 or day > days_in_month[month - 1]:
            _logger.error(f"check_date: Day '{day}' in date '{date}' is out of range for month '{month}'.")
            return False

        return True
    # @staticmethod
    # def check_date(date) -> bool:
    #     if str(date).strip().upper() == "FALSE":
    #         return True
    #     try:
    #         # Attempt to parse the date into YYYY-MM-DD format
    #         datetime.strptime(date.strip(), "%Y-%m-%d")
    #         return True
    #     except ValueError:
    #         return False

    @staticmethod
    def buildMSG(msg: str, sheetName: str, key: str, problem: str):
        msg = msg + "<p>ERROR -> " + "Sheet: " + str(sheetName) + \
            " | Item: " + str(key) + " | " + str(problem) + "</p>\n"
        return msg

    
    ##################################################
    # Check the header of a sheet to import data
    # Input
    #   pHeaderDict: a dictionary that hold the name of the google sheet row, and
    #                the name in the internal dictionnary
    #   p_sheet: the array of the GS sheet
    #   p_sheetName: the name of the sheet
    @staticmethod
    def checkSheetHeader(p_HeaderDict, p_sheet, p_sheetName):
        o_columns = dict()
        o_msg = ""
        o_columnsMissing = False        

        for row in p_HeaderDict:
            if row in p_sheet[0]:
                o_columns[p_HeaderDict[row]] = p_sheet[0].index(row)
            else:
                o_msg = utilities.buildMSG(o_msg, p_sheetName, "Header", str(row) + " Missing")
                o_columnsMissing = True

        return o_columns, o_msg, o_columnsMissing

