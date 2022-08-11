import logging
_logger = logging.getLogger(__name__)


class utilities:
    @staticmethod
    def check_id(id):
        if(" " in id):
            _logger.info("ID: " + str(id))
            return False
        else:
            return True

    @staticmethod
    def check_price(price):
        if(price in ("", " ")):
            return True
        try:
            float(price)
            return True
        except Exception as e:
            _logger.info(e)
            return False

    @staticmethod
    def buildError(msg, sheetName, key, problem):
        pass
