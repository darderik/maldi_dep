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

    def estimate_print_time(self, gcode: str | None = None) -> dict:
        """
        Estimate print time from G-code by parsing movements and calculating time.
        
        Args:
            gcode: G-code string to analyze. If None, uses the last generated G-code.
            
        Returns:
            Dictionary with time breakdown: total, movement, heating, pauses
        """
        if gcode is None:
            gcode = "\n".join(self.gcode_buffer)
        
        lines = gcode.split('\n')
        
        current_x = 0.0
        current_y = 0.0
        current_z = 0.0
        current_feed = 3000.0  # Default feed rate (mm/min)
        
        movement_time = 0.0  # Time spent in actual movements
        heating_time = 0.0   # Time spent heating (estimated)
        pause_time = 0.0     # Time spent in pauses
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            
            # Remove inline comments
            if ';' in line:
                line = line.split(';')[0].strip()
            
            # Parse G1 movements
            if line.startswith('G1'):
                parts = line.split()
                new_x = current_x
                new_y = current_y
                new_z = current_z
                feed = current_feed
                
                for part in parts[1:]:
                    if part.startswith('X'):
                        new_x = float(part[1:])
                    elif part.startswith('Y'):
                        new_y = float(part[1:])
                    elif part.startswith('Z'):
                        new_z = float(part[1:])
                    elif part.startswith('F'):
                        feed = float(part[1:])
                        current_feed = feed
                
                # Calculate distance
                distance = np.sqrt((new_x - current_x)**2 + 
                                 (new_y - current_y)**2 + 
                                 (new_z - current_z)**2)
                
                # Calculate time (feed is in mm/min)
                if feed > 0:
                    time_sec = (distance / feed) * 60.0
                    movement_time += time_sec
                
                current_x = new_x
                current_y = new_y
                current_z = new_z
            
            # Parse heating commands (estimate)
            elif line.startswith('M190') or line.startswith('M109'):
                # Heating time estimates (very rough)
                if 'M190' in line:  # Bed heating
                    heating_time += 180.0  # ~3 minutes estimate
                elif 'M109' in line:  # Nozzle heating
                    heating_time += 120.0  # ~2 minutes estimate
            
            # Parse pause/dwell commands
            elif line.startswith('PAUSE') or line.startswith('M0'):
                pause_time += 5.0  # Assume 5 seconds for user interaction
            elif line.startswith('G4'):
                # G4 P<milliseconds> or S<seconds>
                parts = line.split()
                for part in parts[1:]:
                    if part.startswith('P'):
                        pause_time += float(part[1:]) / 1000.0
                    elif part.startswith('S'):
                        pause_time += float(part[1:])
        
        total_time = movement_time + heating_time + pause_time
        
        return {
            'total_seconds': total_time,
            'total_minutes': total_time / 60.0,
            'total_hours': total_time / 3600.0,
            'movement_seconds': movement_time,
            'heating_seconds': heating_time,
            'pause_seconds': pause_time,
            'formatted': self._format_time(total_time)
        }
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable string."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
