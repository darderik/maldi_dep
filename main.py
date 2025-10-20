"""
MALDI Sample Preparation - Example Workflows using Wrapper

This file demonstrates various workflows for MALDI sample preparation
using the high-level Wrapper API.
"""

import os
import streamlit as st
import numpy as np
import time
from wrapper.MaldiStatus import MaldiStatus, Config
import cProfile

def test_all_methods():
    """Test all methods of MaldiStatus class."""
    print("Testing MaldiStatus methods...")
    
    # Create instance
    ms = MaldiStatus()
    print("✓ MaldiStatus instance created")
    
    # Set some config
    Config().set("grid_step", 0.5)
    Config().set("bed_size_mm", 200.0)
    Config().set("minimum_stride", 1.0)
    Config().set("maximum_stride", 5.0)
    Config().set("stride_steps", 5)
    Config().set("speed", 5.0)
    Config().set("passes", 2)
    Config().set("z_height", 0.5)
    Config().set("bed_temperature", 60.0)
    Config().set("nozzle_temperature", 200.0)
    print("✓ Config set")
    
    # Refresh bed mesh
    ms.refresh_bed_mesh()
    print("✓ Bed mesh refreshed")
    
    # Add samples
    ms.add_sample((10, 10), 20, 30)
    ms.add_sample((50, 50), 15, 25)
    print("✓ Samples added")
    
    # Get samples
    samples = ms.get_samples()
    print(f"✓ Got {len(samples)} samples")
    
    # Get samples info
    samples_info = ms.get_samples_info()
    print(f"✓ Got samples info: {samples_info}")
    
    # Get sample aggregator
    agg = ms.get_sample_aggregator(0)
    print(f"✓ Got sample aggregator: {agg is not None}")
    
    # Optimize strides
    best_strides = ms.optimize_strides(save_to_json=False, plot=True)
    print(f"✓ Optimized strides: {best_strides}")
    ms.generate_gcode("test_optimize.gcode")
    
    
    # Gcode from specific stride
    gcode_file = ms.gcode_from_specific_stride(2.0, "test_specific.gcode")
    print(f"✓ Generated G-code from specific stride: {gcode_file}")
    
    # Load strides from json (if exists)
    try:
        loaded_strides = ms.load_strides_from_json()
        print(f"✓ Loaded strides: {loaded_strides}")
    except FileNotFoundError:
        print("✓ Load strides skipped (no JSON file)")
    
    # Generate G-code
    gcode_file = ms.generate_gcode("test_output.gcode")
    print(f"✓ Generated G-code: {gcode_file}")
    
    # Simulate manual stride
    fig = ms.simulate_manual_stride(2.0, return_fig=True)
    print(f"✓ Simulated manual stride, fig returned: {fig is not None}")
    
    print("All methods tested successfully!")

def main():
    ms = MaldiStatus()

    # Simulation config
    Config().set("grid_step",0.4)
    Config().set("minimum_stride",0.2)
    Config().set("maximum_stride",6.0)
    Config().set("stride_steps",15)
    Config().set("speed",5.0)
    Config().set("passes",2)
    ms.refresh_bed_mesh()
    ms.add_sample((40, 40), 75, 25)
    ms.add_sample((150, 150), 50, 15)
    samples_info = ms.get_samples_info()
    print("Samples added:")
    for info in samples_info:
        print(info)
    
    # Profiling optimize_strides
    profiler = cProfile.Profile()
    profiler.enable()
    ms.optimize_strides()
    profiler.disable()
    # save profiling results to a file
    with open("optimize_strides_profile.txt", "w") as f:
        from pstats import Stats
        stats = Stats(profiler, stream=f)
        stats.sort_stats("cumtime")
        stats.print_stats()
        
if __name__ == "__main__":
    #test_all_methods()
    # main()  # Uncomment to run the original main with profiling
    import streamlit.web.bootstrap
    script_path = os.path.abspath("webapp/entry.py")
    streamlit.web.bootstrap.run(script_path, False, [], {})

