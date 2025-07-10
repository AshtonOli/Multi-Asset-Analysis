import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Union


class Logger:
    """
    A flexible, general-purpose logging class with multiple output options.
    
    Features:
    - Console and file logging
    - Rotating file handlers
    - Customizable formatting
    - Multiple log levels
    - Context managers for temporary log level changes
    - Easy configuration
    """
    
    def __init__(
        self,
        name: str = "AppLogger",
        level: Union[str, int] = logging.INFO,
        log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
        date_format: str = "%d-%b-%Y %H:%M:%S",
        log_format: Optional[str] = None
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name (default: "AppLogger")
            level: Logging level (default: INFO)
            log_file: Path to log file (optional)
            max_file_size: Maximum size per log file in bytes (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
            console_output: Whether to output to console (default: True)
            date_format: Date format string (default: "%d-%b-%Y %H:%M:%S")
            log_format: Custom log format (optional)
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self._get_level(level))
        
        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Default format
        if log_format is None:
            log_format = "[%(asctime)s] %(name)s - %(levelname)s - %(message)s"
        
        self.formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # Set up console handler
        if console_output:
            self._setup_console_handler()
        
        # Set up file handler if specified
        if log_file:
            self._setup_file_handler(log_file, max_file_size, backup_count)
    
    def _get_level(self, level: Union[str, int]) -> int:
        """Convert string level to logging constant."""
        if isinstance(level, str):
            return getattr(logging, level.upper())
        return level
    
    def _setup_console_handler(self):
        """Set up console logging handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self, log_file: str, max_size: int, backup_count: int):
        """Set up rotating file handler."""
        # Create directory if it doesn't exist
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, *args, **kwargs)
    
    def set_level(self, level: Union[str, int]):
        """Change the logging level."""
        self.logger.setLevel(self._get_level(level))
    
    def add_file_handler(self, log_file: str, max_size: int = 10*1024*1024, backup_count: int = 5):
        """Add additional file handler."""
        self._setup_file_handler(log_file, max_size, backup_count)
    
    def log_function_call(self, func_name: str, *args, **kwargs):
        """Log function calls for debugging."""
        args_str = ", ".join(str(arg) for arg in args)
        kwargs_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        params = ", ".join(filter(None, [args_str, kwargs_str]))
        self.debug(f"Calling {func_name}({params})")
    
    def log_performance(self, operation: str, duration: float):
        """Log performance metrics."""
        self.info(f"Performance: {operation} took {duration:.4f} seconds")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.exception(f"Exception occurred: {exc_val}")
        return False
    
binance_logger = Logger("BinanceConnector", log_file = "logs/binance.log")
dash_logger = Logger("Dash", log_file = "logs/dash.log")
data_management_logger = Logger("DataManager", log_file = "logs/datamanager.log")