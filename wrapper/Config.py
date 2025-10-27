import json
import os

from meshing.BedMesh import BedMesh
from scipy.interpolate import interp1d
from scipy.stats import linregress
from typing import Any, List
from dataclasses import dataclass
class Config:
    _instance = None
    _config_data = {}
    machine_settings = {}
    simulation_settings = {}
    _sample_defaults = {}
    bed_mesh = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
            # Init methods
            cls._instance._initialize_config()
        return cls._instance

    def _initialize_config(self):
        """Initialize default configuration values."""
        self.k_sigma = 2.0 #Edit at will
        self.machine_settings = {
            "speed": 10, # Speed for any movement (mm/s)
            "acceleration": 100, # Acceleration for any movement (mm/s^2)
            "nozzle_temperature": 100, # Nozzle temperature (°C)
            "bed_temperature": 50, # Bed temperature (°C)
            "z_height": 5, # Z-axis height (mm)(Any movement)
            "bed_size_mm": 200.0, # Bed size (mm)
            "max_speed": 200.0, # Maximum speed for any movement (mm/s)
        }
        self._sample_defaults = {
            "pattern": "serpentine",
            "x_size": 10,
            "y_size": 10,
            "passes":1,
            "stride":1.0,
        }
        self.simulation_settings = {
            "grid_step": 0.5, # Step size for simulation grid (mm)
            "minimum_stride": 0.5, # Minimum stride for optimization (mm)
            "maximum_stride": 5.0, # Maximum stride for optimization (mm)
            "stride_steps": 10, # Number of stride steps to evaluate during optimization
            "x_points" : 20,
            "save_to_json": True,
            "margin":5.0,

            
        }
        self.diameter_vs_z = {
            "z": [
                30.0,
                20.0,
                10.0,
                5.0,
                70.0,
                40.0
            ],
            "diameter": [
                4.0,
                3.0,
            2.0,
            1.0,
            8.0,
            5.0
        ],
            "z_offset": 20.0
        }
    def get_standard_dev(self) -> float:
        """Get standard deviation based on current z height."""
        z_height = self.get_height()
        k_sigma = self.k_sigma #Edit at will
        diameter = self._get_diameter_for_z(z_height)
        if diameter <= 0:
            raise ValueError("Invalid diameter computed from z_height.")
        return diameter / (2*k_sigma)  # Assuming 4 sigma within diameter
    def get_msetting(self,key:str=""):
        """Get machine setting by key."""
        if key in self.machine_settings:
            return self.machine_settings[key]
        else:
            raise KeyError(f"Machine setting '{key}' not found.")
    def get_ssetting(self,key:str=""):
        """Get simulation setting by key."""
        if key in self.simulation_settings:
            return self.simulation_settings[key]
        else:
            raise KeyError(f"Simulation setting '{key}' not found.")
    def get_height(self) -> float:
        return self.machine_settings.get("z_height", 0.0)
    def _get_diameter_for_z(self, z: float) -> float:
        diameter = 0.0
        diameters: List[float] = self.diameter_vs_z["diameter"]
        zs: List[float] = self.diameter_vs_z["z"]
        z_offset: float = self.diameter_vs_z.get("z_offset", 0.0)
        z = z + z_offset
        if zs and diameters:
            # Perform linear regression using scipy.stats.linregress
            result = linregress(zs, diameters)
            slope = result.slope
            intercept = result.intercept
            diameter = slope * z + intercept
        return diameter

    def get(self,key:str=""):
        """Get config value by key."""
        if key in self.machine_settings.keys():
            return self.machine_settings[key]
        elif key in self.simulation_settings.keys():
            return self.simulation_settings[key]
        elif key in self._sample_defaults.keys():
            return self._sample_defaults[key]
        else:
            raise KeyError(f"Config key '{key}' not found.")
    def set(self, key: str, value):
        """Set config value by key."""
        if key in self.machine_settings:
            self.machine_settings[key] = value
        elif key in self.simulation_settings:
            self.simulation_settings[key] = value
        elif key in self._sample_defaults:
            self._sample_defaults[key] = value
        else:
            raise KeyError(f"Config key '{key}' not found.")
class SampleConfig:
    def __init__(self, sample_data: dict):
        self.sample_data = sample_data
        
    def get(self, key: str):
        """Get sample config value by key."""
        if key in self.sample_data:
            return self.sample_data[key]
        else:
            raise KeyError(f"Sample config key '{key}' not found.")
