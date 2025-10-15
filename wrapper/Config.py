import json
import os

class Config:
    _instance = None
    _config_data = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as config_file:
                self._config_data = json.load(config_file)
        else:
            self._config_data = {}
        
    def get(self, key, default=None):
        return self._config_data.get(key, default)
    
    def set(self, key, value):
        """Set a single configuration value and save to file."""
        self._config_data[key] = value
        self._save_config()
    
    def update(self, data_dict):
        """Update multiple configuration values and save to file."""
        self._config_data.update(data_dict)
        self._save_config()
    
    def _save_config(self):
        """Save the current config data to config.json."""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')
        try:
            with open(config_path, 'w') as config_file:
                json.dump(self._config_data, config_file, indent=4)
        except Exception as e:
            raise Exception(f"Failed to save config: {e}")
    
    def get_all(self):
        """Get the entire configuration dictionary."""
        return self._config_data.copy()