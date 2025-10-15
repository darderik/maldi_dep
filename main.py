"""
MALDI Sample Preparation - Example Workflows using Wrapper

This file demonstrates various workflows for MALDI sample preparation
using the high-level Wrapper API.
"""

import os
from turtle import st
import numpy as np
from wrapper.Wrapper import Wrapper


def example_1_load_from_config():
    """
    Example 1: Load samples from config.json and generate G-code with optimization
    
    This workflow:
    1. Loads configuration from config.json
    2. Loads sample positions from config.json
    3. Creates serpentine patterns
    4. Optimizes stride parameters
    5. Generates G-code
    """
    print("=" * 60)
    print("Example 1: Load from Config with Optimization")
    print("=" * 60)
    
    # Initialize wrapper (automatically loads from config.json)
    wrapper = Wrapper()
    
    # Load sample masks from config.json
    
    # Create serpentine patterns for all samples
    wrapper.create_serpentines()
    
    # Optimize stride parameters
    print("Optimizing strides...")
    best_strides = wrapper.optimize_strides(
        sample_idx=0,
        save_to_json=True,
        plot=True
    )
    print(f"Best strides found: {best_strides}")
    
    # Generate G-code (strides already applied by optimize_strides)
    output_file = wrapper.generate_gcode("example1_optimized.gcode")
    print(f"✓ G-code saved to: {output_file}")
    print()

def main():
    """
    Main function - run all examples or select specific ones
    """
    print("\n" + "=" * 60)
    print("MALDI Wrapper - Example Workflows")
    print("=" * 60 + "\n")
    
    # Run individual examples
    # Uncomment the ones you want to run:
    
    example_1_load_from_config()      # Full optimization workflow
    # example_2_manual_samples()        # Manual definition, no optimization
    # example_3_use_saved_optimization() # Reuse previous optimization
    # example_4_multiple_samples()      # Multiple sample regions
    # example_5_custom_parameters()     # Custom parameters
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    import streamlit.web.bootstrap
    script_path = os.path.abspath("webapp/entry.py")
    streamlit.web.bootstrap.run(script_path, False, [], {})

    