import logging
from colorama import Fore, Style

LEVEL_COLORS = {
    "DEBUG": Fore.CYAN,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
}

class ColoredStreamHandler(logging.StreamHandler):
    def emit(self, record):
        log_message = self.format(record)
        self.stream.write(log_message + "\n")
        self.flush()

    def format(self, record):
        color = LEVEL_COLORS.get(record.levelname, "")
        reset = Style.RESET_ALL
        log_message = super().format(record)
        # Add color to the level name
        log_message = log_message.replace(record.levelname, f"{color}{record.levelname}{reset}", 1)
        return log_message

custom_logger = logging.getLogger("CustomLogger")
custom_logger.setLevel(logging.DEBUG)

# Define the formatter to have levelname first, then timestamp, then message
formatter = logging.Formatter('%(levelname)s:     %(asctime)s  -  %(message)s')

handler = ColoredStreamHandler()
handler.setFormatter(formatter)
custom_logger.addHandler(handler)

# Example usage
if __name__ == "__main__":
    custom_logger.debug("This is a debug message.")
    custom_logger.info("This is an info message.")
    custom_logger.warning("This is a warning message.")
    custom_logger.error("This is an error message.")
    custom_logger.critical("This is a critical message.")
