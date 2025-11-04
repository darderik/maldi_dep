import json
import os
from typing import List
import shutil

import numpy as np


class Config:
    """Singleton configuration manager for MALDI machine and simulation settings."""

    _instance = None
    _config_data = {}
    machine_settings = {}
    simulation_settings = {}
    _sample_defaults = {}
    bed_mesh = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize_config()
        return cls._instance

    def _initialize_config(self):
        """Initialize default configuration values."""
        # Establish a stable config file path at project root (.. from this file)
        self._project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self._config_path = os.path.join(self._project_root, "config.json")

        self.k_sigma = 2.0

        self.machine_settings = {
            "speed": 10,  # Speed for any movement (mm/s)
            "acceleration": 100,  # Acceleration for any movement (mm/s^2)
            "nozzle_temperature": 100,  # Nozzle temperature (°C)
            "bed_temperature": 50,  # Bed temperature (°C)
            "z_height": 5,  # Z-axis height (mm)
            "bed_size_mm": 200.0,  # Bed size (mm)
            "max_speed": 200.0,  # Maximum speed for any movement (mm/s)
        }

        self._sample_defaults = {
            "pattern": "serpentine",
            "x_size": 10,
            "y_size": 10,
            "passes": 1,
            "stride": 1.0,
        }

        self.simulation_settings = {
            "grid_step": 0.5,  # Step size for simulation grid (mm)
            "minimum_stride": 0.5,  # Minimum stride for optimization (mm)
            "maximum_stride": 5.0,  # Maximum stride for optimization (mm)
            "stride_steps": 10,  # Number of stride steps to evaluate during optimization
            "x_points": 20,
            "save_to_json": True,
            "margin": 5.0,
        }

        self.diameter_vs_z = {
            "z": [30.0, 20.0, 10.0, 5.0, 70.0, 40.0],
            "diameter": [4.0, 3.0, 2.0, 1.0, 8.0, 5.0],
            "z_offset": 20.0,
        }

        # Attempt to load persisted configuration, overriding defaults
        self._load_from_json()
        # If no config file existed, save defaults now so users can edit the file
        if not os.path.exists(self._config_path):
            self.save()
        self._cleanup_logs()

    def _cleanup_logs(self):
        """Clean up old log files, keeping only the most recent 10."""
        logs_dir = os.path.join(self._project_root, "logs")
        if not os.path.exists(logs_dir):
            return
        try:
            # List all files in the logs directory, sorted by modification time
            files = sorted(
                [f for f in os.listdir(logs_dir) if os.path.isfile(os.path.join(logs_dir, f))],
                key=lambda x: os.path.getmtime(os.path.join(logs_dir, x))
            )
            # Remove oldest files if there are more than 10
            while len(files) > 10:
                os.remove(os.path.join(logs_dir, files.pop(0)))
        except Exception as e:
            print(f"Error cleaning up logs: {e}")

    def get_standard_dev(self) -> float:
        """Get standard deviation based on current z height."""
        z_height = self.get_height()
        k_sigma = self.k_sigma
        diameter = self._get_diameter_for_z(z_height)
        if diameter <= 0:
            raise ValueError("Invalid diameter computed from z_height.")
        return diameter / (2 * k_sigma)  # Assuming 4 sigma within diameter

    def get_msetting(self, key: str = ""):
        """Get machine setting by key."""
        if key in self.machine_settings:
            return self.machine_settings[key]
        else:
            raise KeyError(f"Machine setting '{key}' not found.")

    def get_ssetting(self, key: str = ""):
        """Get simulation setting by key."""
        if key in self.simulation_settings:
            return self.simulation_settings[key]
        else:
            raise KeyError(f"Simulation setting '{key}' not found.")

    def get_height(self) -> float:
        return self.machine_settings.get("z_height", 0.0)

    def _get_diameter_for_z(self, z: float) -> float:
        """Calculate diameter for a given z height using linear interpolation."""
        diameter = 0.0
        diameters: List[float] = self.diameter_vs_z["diameter"]
        zs: List[float] = self.diameter_vs_z["z"]
        z_offset: float = self.diameter_vs_z.get("z_offset", 0.0)
        z = z + z_offset
        if zs and diameters:
            # Linear fit using numpy for robustness and clearer typing
            slope, intercept = np.polyfit(np.array(zs, dtype=float), np.array(diameters, dtype=float), 1)
            slope = float(slope)
            intercept = float(intercept)
            diameter = slope * float(z) + intercept
        return diameter

    def get(self, key: str = ""):
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
        """Set config value by key and persist to disk."""
        updated = False
        if key in self.machine_settings:
            self.machine_settings[key] = value
            updated = True
        elif key in self.simulation_settings:
            self.simulation_settings[key] = value
            updated = True
        elif key in self._sample_defaults:
            self._sample_defaults[key] = value
            updated = True
        elif key == "k_sigma":
            self.k_sigma = value
            updated = True
        else:
            raise KeyError(f"Config key '{key}' not found.")
        if updated:
            # Auto-save any change
            self.save()

    # ========================== Persistence helpers ==========================
    def to_dict(self) -> dict:
        """Serialize current config to a JSON-serializable dict."""
        return {
            "k_sigma": float(self.k_sigma),
            "machine_settings": self.machine_settings,
            "simulation_settings": self.simulation_settings,
            "sample_defaults": self._sample_defaults,
            "diameter_vs_z": self.diameter_vs_z,
        }

    def save(self, path: str | None = None) -> str:
        """Save current configuration to disk. Returns the file path used."""
        cfg_path = path or self._config_path
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        tmp_path = cfg_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        # Atomic-ish replace
        if os.path.exists(cfg_path):
            try:
                os.replace(tmp_path, cfg_path)
            except Exception:
                # Fallback if replace isn't available
                os.remove(cfg_path)
                os.rename(tmp_path, cfg_path)
        else:
            os.rename(tmp_path, cfg_path)
        return cfg_path

    def _load_from_json(self, path: str | None = None) -> None:
        """Load configuration from disk if present, overriding defaults."""
        cfg_path = path or self._config_path
        if not os.path.exists(cfg_path):
            return
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # If file is corrupted or unreadable, skip loading
            return
        # Merge known fields only
        if isinstance(data, dict):
            if "k_sigma" in data:
                try:
                    self.k_sigma = float(data["k_sigma"])
                except Exception:
                    pass
            ms = data.get("machine_settings")
            if isinstance(ms, dict):
                self.machine_settings.update({k: ms[k] for k in self.machine_settings.keys() if k in ms})
            ss = data.get("simulation_settings")
            if isinstance(ss, dict):
                self.simulation_settings.update({k: ss[k] for k in self.simulation_settings.keys() if k in ss})
            sdef = data.get("sample_defaults") or data.get("_sample_defaults")
            if isinstance(sdef, dict):
                self._sample_defaults.update({k: sdef[k] for k in self._sample_defaults.keys() if k in sdef})
            dvz = data.get("diameter_vs_z")
            if isinstance(dvz, dict):
                # Keep only expected keys if present
                for k in ("z", "diameter", "z_offset"):
                    if k in dvz:
                        self.diameter_vs_z[k] = dvz[k]


class SampleConfig:
    """Configuration for individual sample patterns."""

    def __init__(self, sample_data: dict):
        self.sample_data = sample_data

    def get(self, key: str):
        """Get sample config value by key."""
        if key in self.sample_data:
            return self.sample_data[key]
        else:
            raise KeyError(f"Sample config key '{key}' not found.")
