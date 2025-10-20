import numpy as np
from numpy.typing import NDArray
from typing import Any, List
# Create gcode from numpy array of points
from dataclasses import dataclass
from meshing import Mask
from simulation import Movement


@dataclass
class MaskMovement:
    mask: Mask
    movements: List[Movement]  # List of Movement objects representing the path


class GCodeCreator:
    def __init__(self, data, z_height: float = 5.0, safe_z_offset: float = 10.0, park_x: float = 0.0, park_y: float = 0.0, bed_temp: float = 0.0, nozzle_temp: float = 0.0, max_speed: float = 200.0):
        from wrapper.MaldiStatus import SampleAggregator

        self.data: List[SampleAggregator] = data
        self.gcode_buffer: List[str] = []
        self.z_height: float = z_height
        self.safe_z_offset: float = safe_z_offset
        self.park_x: float = park_x
        self.park_y: float = park_y
        self.bed_temp: float = bed_temp  # Default bed temperature
        self.nozzle_temp: float = nozzle_temp  # Default nozzle temperature
        self.max_speed: float = max_speed  # Max travel speed (non-deposition)
        
    def generate_gcode(self) -> str:
        # Header: Initial setup commands
        # Samples, serpentines info
        for s_agg in self.data:
            self.gcode_buffer.append("; Sample at ({} , {})".format(s_agg.bl_corner[0], s_agg.bl_corner[1]))
            self.gcode_buffer.append(";  - Size: {} x {}".format(s_agg.x_size, s_agg.y_size))
            self.gcode_buffer.append(";  - Stride: {}".format(s_agg.serpentine.get_stride()))
        self.gcode_buffer.append("; Start of G-code")
        self.gcode_buffer.append("G28 ; Home all axes")
        self.gcode_buffer.append("G21 ; Set units to millimeters")
        self.gcode_buffer.append("G90 ; Use absolute coordinates")
        self.gcode_buffer.append("G1 F3000 ; Set default feed rate")
        # self.gcode_buffer.append("M107 ; Ensure spray/fan is off")  # Commented out since spray is manual
        # Move to WORKING Z (will not change during the deposition)
        self.gcode_buffer.append("G1 Z{:.2f} F3000 ; Move to working height".format(self.z_height))
        # Move to 0,0 and wait
        self.gcode_buffer.append("G1 X0.1 Y0.1 F3000 ; Move to (0,0)")
        self.gcode_buffer.append("PAUSE; Wait for user confirmation to start")
        # Set temperatures if specified
        if self.bed_temp > 0:
            self.gcode_buffer.append(f"M140 S{self.bed_temp} ; Set bed temperature")
            self.gcode_buffer.append(f"M190 S{self.bed_temp} ; Wait for bed temperature to reach target")
        if self.nozzle_temp > 0:
            self.gcode_buffer.append(f"M104 S{self.nozzle_temp} ; Set nozzle temperature")
            self.gcode_buffer.append(f"M109 S{self.nozzle_temp} ; Wait for nozzle temperature to reach target")
        first_serpentine = True
        for data_entry in self.data:
            first_movement = True
            cur_mask = data_entry.sample_mask
            movs = data_entry.serpentine.movements
            self.gcode_buffer.append("; Deposition for Mask")
            for mov in movs:
                cur_x = mov.x
                cur_y = mov.y
                speed = mov.speed
                if first_movement:
                    # First movement, move without spraying
                    speed = self.max_speed  # max speed to starting pointMALDI_S
                    self.gcode_buffer.append("G1 X{:.2f} Y{:.2f} F{} ; Approach to start without spray".format(cur_x, cur_y, self.max_speed * 60))
                    #self.gcode_buffer.append("M106 S255 ; Turn on spray/fan at full speed")
                    first_movement = False
                else:
                    self.gcode_buffer.append("G1 X{:.2f} Y{:.2f} F{} ; Deposition move".format(cur_x, cur_y, speed * 60))

            # After each mask, turn off spray briefly if needed, but keep on for continuity
            # For now, leave on; add logic if masks are separate

        # Footer: Cleanup
        self._add_footer()
        self.gcode_buffer.append("; End of G-code")
        return "\n".join(self.gcode_buffer)

    def _add_footer(self):
        """Add footer commands for safe shutdown."""
        self.gcode_buffer.append("; Footer: Safe shutdown")
        # Raise head to safe height
        safe_z = self.z_height + self.safe_z_offset
        self.gcode_buffer.append("G1 Z{:.2f} F3000 ; Raise to safe height".format(safe_z))
        # Park head
        self.gcode_buffer.append("G1 X{:.2f} Y{:.2f} F3000 ; Park at safe position".format(self.park_x, self.park_y))
        self.gcode_buffer.append("M140 S0 ; Turn off bed heater")
        self.gcode_buffer.append("M104 S0 ; Turn off nozzle heater")
        # self.gcode_buffer.append("M107 ; Turn off spray/fan")  # Commented out since spray is manual
        # End program
        self.gcode_buffer.append("M30 ; End of program")
