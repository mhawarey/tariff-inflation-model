import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
import os
import sys

def tariff_inflation_model(
    tariff_rate=1.45,            # 145% tariff
    affected_imports_share=0.15, # Share of US imports from China affected by tariffs
    china_import_share=0.18,     # Share of total US imports from China
    import_cpi_weight=0.18,      # Weight of imports in CPI basket
    passthrough_rate=0.75,       # Share of tariff passed to consumers
    substitution_rate=0.4,       # Rate at which importers switch to non-Chinese sources
    domestic_sub_price_premium=0.25, # Price premium for domestic substitutes
    foreign_sub_price_premium=0.15,  # Price premium for non-Chinese foreign substitutes
    input_cost_multiplier=0.3,    # Secondary effects on US production costs
    months=24                     # Simulation period
):
    """
    Model the inflation impact of tariffs on Chinese imports
    
    Returns:
        DataFrame with monthly inflation impacts
    """
    # Calculate direct price effect
    china_cpi_weight = import_cpi_weight * china_import_share
    affected_cpi_weight = china_cpi_weight * affected_imports_share
    
    # Initial direct price impact (annualized)
    direct_effect = affected_cpi_weight * tariff_rate * passthrough_rate
    
    # Initialize results dataframe
    results = pd.DataFrame(index=range(months), columns=[
        'month', 
        'direct_effect', 
        'substitution_effect',
        'secondary_effect',
        'total_effect',
        'cumulative_effect'
    ])
    
    # Apply effects over time with different lag structures
    for month in range(months):
        # Direct effect phases in over first 3 months
        direct_phase = min(1.0, (month + 1) / 3)
        month_direct = direct_effect * direct_phase
        
        # Substitution effect grows over time (reducing the impact)
        sub_phase = min(1.0, (month + 1) / 6)  # Takes 6 months to fully phase in
        month_substitution = -(direct_effect * substitution_rate * sub_phase)
        
        # But substitution comes at a price premium
        substitution_premium = (
            substitution_rate * affected_cpi_weight * 
            (domestic_sub_price_premium * 0.4 + foreign_sub_price_premium * 0.6) * 
            sub_phase
        )
        
        # Secondary effects on input costs grow over time
        secondary_phase = min(1.0, max(0, (month - 2)) / 10)  # Delayed effect
        month_secondary = direct_effect * input_cost_multiplier * secondary_phase
        
        # Total monthly effect
        month_total = month_direct + month_substitution + substitution_premium + month_secondary
        
        # Store results
        results.loc[month, 'month'] = month + 1
        results.loc[month, 'direct_effect'] = month_direct * 100  # Convert to percentage points
        results.loc[month, 'substitution_effect'] = (month_substitution + substitution_premium) * 100
        results.loc[month, 'secondary_effect'] = month_secondary * 100
        results.loc[month, 'total_effect'] = month_total * 100
    
    # Calculate cumulative effect (approximating compounding)
    cumulative = np.zeros(months)
    for month in range(months):
        if month == 0:
            cumulative[month] = results.loc[month, 'total_effect'] / 12  # Monthly rate
        else:
            cumulative[month] = cumulative[month-1] + results.loc[month, 'total_effect'] / 12
    
    results['cumulative_effect'] = cumulative
    
    return results

def run_sensitivity_analysis(baseline_params, param_variations):
    """
    Run sensitivity analysis by varying key parameters
    
    Args:
        baseline_params: Dictionary of baseline parameters
        param_variations: Dictionary with parameter names and lists of values
    
    Returns:
        Dictionary of results for each parameter variation
    """
    results = {}
    
    for param, values in param_variations.items():
        param_results = []
        for value in values:
            # Create modified parameters
            test_params = baseline_params.copy()
            test_params[param] = value
            
            # Run model with modified parameters
            model_result = tariff_inflation_model(**test_params)
            
            # Store final cumulative impact
            final_impact = model_result['cumulative_effect'].iloc[-1]
            param_results.append((value, final_impact))
        
        results[param] = param_results
    
    return results

def plot_inflation_impact(model_results):
    """Plot the inflation impact over time"""
    plt.figure(figsize=(12, 7))
    
    # Increase font sizes
    plt.rcParams.update({'font.size': 14})
    
    # Plot components
    plt.plot(model_results['month'], model_results['direct_effect'], 
             label='Direct Price Effect', linewidth=2)
    plt.plot(model_results['month'], model_results['substitution_effect'], 
             label='Substitution Effect', linewidth=2)
    plt.plot(model_results['month'], model_results['secondary_effect'], 
             label='Secondary Effects', linewidth=2)
    
    # Plot total and cumulative
    plt.plot(model_results['month'], model_results['total_effect'], 
             label='Total Monthly Effect', linewidth=3, color='red')
    plt.plot(model_results['month'], model_results['cumulative_effect'], 
             label='Cumulative Effect', linewidth=3, color='black', linestyle='--')
    
    plt.title('Estimated Inflation Impact of Tariffs on Chinese Imports', fontsize=18)
    plt.xlabel('Months After Implementation', fontsize=16)
    plt.ylabel('Impact on Inflation Rate (Percentage Points)', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=14)
    plt.tight_layout()
    
    return plt.gcf()

def plot_sensitivity(sensitivity_results):
    """Plot sensitivity analysis results"""
    fig, axes = plt.subplots(len(sensitivity_results), 1, figsize=(10, 5*len(sensitivity_results)))
    
    # Increase font sizes
    plt.rcParams.update({'font.size': 14})
    
    for i, (param, results) in enumerate(sensitivity_results.items()):
        values, impacts = zip(*results)
        
        # Readable parameter names
        param_names = {
            'tariff_rate': 'Tariff Rate',
            'affected_imports_share': 'Share of Imports Affected',
            'passthrough_rate': 'Consumer Pass-through Rate',
            'substitution_rate': 'Substitution Rate'
        }
        
        param_name = param_names.get(param, param)
        
        axes[i].plot(values, impacts, 'o-', linewidth=2, markersize=8)
        axes[i].set_title(f'Sensitivity to {param_name}', fontsize=16)
        axes[i].set_ylabel('Inflation Impact (pp)', fontsize=14)
        axes[i].set_xlabel(param_name, fontsize=14)
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

class TariffModelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tariff Inflation Impact Model - By Dr. Mosab Hawarey")
        self.root.geometry("1600x900")
        self.root.minsize(1400, 800)
        
        # Set default font sizes - increase size for better readability
        self.title_font = ("Arial", 16, "bold")
        self.group_font = ("Arial", 14, "bold")
        self.label_font = ("Arial", 13)
        self.value_font = ("Arial", 13, "bold")
        self.button_font = ("Arial", 14, "bold")
        self.results_font = ("Arial", 13)
        
        # Default parameters
        self.default_params = {
            'tariff_rate': 1.45,
            'affected_imports_share': 0.15,
            'china_import_share': 0.18,
            'import_cpi_weight': 0.18,
            'passthrough_rate': 0.75,
            'substitution_rate': 0.4,
            'domestic_sub_price_premium': 0.25,
            'foreign_sub_price_premium': 0.15,
            'input_cost_multiplier': 0.3,
            'months': 24
        }
        
        self.param_variations = {
            'tariff_rate': [0.5, 1.0, 1.45, 2.0, 2.5],
            'affected_imports_share': [0.05, 0.1, 0.15, 0.2, 0.25],
            'passthrough_rate': [0.5, 0.6, 0.75, 0.85, 0.95],
            'substitution_rate': [0.2, 0.3, 0.4, 0.5, 0.6]
        }
        
        self.params = self.default_params.copy()
        
        # Create main frames
        self.create_frames()
        self.create_input_widgets()
        self.create_output_widgets()
        
        # Run initial model
        self.run_model()
    
    def create_frames(self):
        # Calculate panel widths based on total window size
        # Left panel will be 25% of total width
        left_panel_width = int(self.root.winfo_screenwidth() * 0.25)
        
        # Main layout: left panel for inputs, right panel for outputs
        self.left_frame = ttk.Frame(self.root, padding="15")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(15, 5), pady=15)
        
        # Set fixed width for left frame (25% of window width)
        self.left_frame.pack_propagate(False)
        self.left_frame.config(width=left_panel_width)
        
        self.right_frame = ttk.Frame(self.root, padding="15")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 15), pady=15)
        
        # Frame for results text - Don't pass font directly to LabelFrame
        self.results_frame = ttk.LabelFrame(self.right_frame, text="Results Summary", padding="15")
        self.results_frame.pack(fill=tk.X, expand=False, pady=10)
        
        # Frame for plots
        self.plot_frame = ttk.Frame(self.right_frame, padding="15")
        self.plot_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tabs for different plots
        self.plot_tabs = ttk.Notebook(self.plot_frame)
        self.plot_tabs.pack(fill=tk.BOTH, expand=True)
        
        self.impact_tab = ttk.Frame(self.plot_tabs)
        self.sensitivity_tab = ttk.Frame(self.plot_tabs)
        
        self.plot_tabs.add(self.impact_tab, text="Inflation Impact")
        self.plot_tabs.add(self.sensitivity_tab, text="Sensitivity Analysis")
    
    def create_input_widgets(self):
        # Title for inputs
        ttk.Label(self.left_frame, text="Model Parameters", font=self.title_font).pack(anchor=tk.W, pady=(0, 20))
        
        # Create sliders for each parameter
        self.sliders = {}
        
        # Parameter grouping
        param_groups = [
            ("Tariff Parameters", [
                ("tariff_rate", "Tariff Rate (%)", 0, 300, 145),
                ("affected_imports_share", "Share of Imports Affected (%)", 0, 100, 15),
            ]),
            ("Economic Structure", [
                ("china_import_share", "China's Share of US Imports (%)", 0, 50, 18),
                ("import_cpi_weight", "Imports Weight in CPI (%)", 0, 50, 18),
            ]),
            ("Economic Response", [
                ("passthrough_rate", "Consumer Pass-through Rate (%)", 0, 100, 75),
                ("substitution_rate", "Substitution Rate (%)", 0, 100, 40),
                ("domestic_sub_price_premium", "Domestic Sub. Price Premium (%)", 0, 100, 25),
                ("foreign_sub_price_premium", "Foreign Sub. Price Premium (%)", 0, 100, 15),
                ("input_cost_multiplier", "Input Cost Multiplier", 0, 1.0, 0.3),
            ]),
            ("Time Horizon", [
                ("months", "Simulation Months", 6, 60, 24),
            ]),
        ]
        
        for group_name, params in param_groups:
            # Create group frame - Don't pass font directly to LabelFrame
            group_frame = ttk.LabelFrame(self.left_frame, text=group_name, padding="15")
            group_frame.pack(fill=tk.X, expand=False, pady=10)
            
            for param, label, min_val, max_val, default in params:
                # Create frame for each parameter
                param_frame = ttk.Frame(group_frame)
                param_frame.pack(fill=tk.X, expand=True, pady=8)
                
                # Label - shortened to take less space and ensure it fits
                label_width = 30  # Wider label space
                ttk.Label(param_frame, text=label, font=self.label_font, anchor=tk.W).pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
                
                # Value label - positioned at far right
                value_var = tk.StringVar()
                if param in ("tariff_rate", "affected_imports_share", "china_import_share", 
                            "import_cpi_weight", "passthrough_rate", "substitution_rate",
                            "domestic_sub_price_premium", "foreign_sub_price_premium"):
                    # Display as percentage
                    value_var.set(f"{default}%")
                elif param == "input_cost_multiplier":
                    value_var.set(f"{default:.2f}")
                else:
                    value_var.set(str(int(default)))
                
                # Slider container frame (includes slider and value)
                slider_container = ttk.Frame(param_frame)
                slider_container.pack(side=tk.TOP, fill=tk.X, expand=True)
                
                # Slider takes most space
                slider = ttk.Scale(
                    slider_container, 
                    from_=min_val, 
                    to=max_val, 
                    value=default,
                    command=lambda val, p=param, vv=value_var: self.update_param(p, val, vv)
                )
                slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
                
                # Value label at far right
                value_label = ttk.Label(slider_container, textvariable=value_var, font=self.value_font, width=6, anchor=tk.E)
                value_label.pack(side=tk.RIGHT)
                
                # Store references
                self.sliders[param] = {
                    'slider': slider,
                    'value_var': value_var,
                    'is_percent': param != "months" and param != "input_cost_multiplier",
                    'is_float': param == "input_cost_multiplier"
                }
        
        # Button container for consistent spacing
        button_container = ttk.Frame(self.left_frame)
        button_container.pack(fill=tk.X, expand=False, pady=15)
        
        # Run button
        ttk.Button(button_container, 
                  text="Run Model", 
                  command=self.run_model, 
                  style="Bold.TButton").pack(pady=10, fill=tk.X, padx=20)
        
        # Reset button
        ttk.Button(button_container, 
                  text="Reset to Defaults", 
                  command=self.reset_params, 
                  style="Bold.TButton").pack(pady=5, fill=tk.X, padx=20)
    
    def create_output_widgets(self):
        # Results text
        self.results_var = tk.StringVar()
        self.results_var.set("Run the model to see results")
        
        results_label = ttk.Label(self.results_frame, textvariable=self.results_var, 
                                 font=self.results_font, justify=tk.LEFT)
        results_label.pack(anchor=tk.W, pady=8)
        
        # Canvas for plots
        self.impact_canvas_frame = ttk.Frame(self.impact_tab)
        self.impact_canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.sensitivity_canvas_frame = ttk.Frame(self.sensitivity_tab)
        self.sensitivity_canvas_frame.pack(fill=tk.BOTH, expand=True)
    
    def update_param(self, param, value, value_var):
        # Convert slider value to appropriate format
        val = float(value)
        
        # Update display
        if param == "months":
            val = int(val)
            value_var.set(str(val))
        elif param == "input_cost_multiplier":
            value_var.set(f"{val:.2f}")
        else:
            # Percentage parameters
            value_var.set(f"{val:.1f}%")
        
        # Update params dict with appropriate scaling
        if param in ("tariff_rate", "affected_imports_share", "china_import_share", 
                    "import_cpi_weight", "passthrough_rate", "substitution_rate",
                    "domestic_sub_price_premium", "foreign_sub_price_premium"):
            # Convert percentage to decimal
            self.params[param] = val / 100
        else:
            self.params[param] = val
    
    def reset_params(self):
        # Reset all parameters to defaults
        for param, value in self.default_params.items():
            display_value = value
            if param in ("tariff_rate", "affected_imports_share", "china_import_share", 
                        "import_cpi_weight", "passthrough_rate", "substitution_rate",
                        "domestic_sub_price_premium", "foreign_sub_price_premium"):
                display_value = value * 100
            
            self.sliders[param]['slider'].set(display_value)
            
            if param == "months":
                self.sliders[param]['value_var'].set(str(int(display_value)))
            elif param == "input_cost_multiplier":
                self.sliders[param]['value_var'].set(f"{display_value:.2f}")
            else:
                self.sliders[param]['value_var'].set(f"{display_value:.1f}%")
                
            self.params[param] = value
        
        # Run model with reset parameters
        self.run_model()
    
    def run_model(self):
        # Clear existing plots
        for widget in self.impact_canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.sensitivity_canvas_frame.winfo_children():
            widget.destroy()
        
        # Run the model with current parameters
        results = tariff_inflation_model(**self.params)
        
        # Generate sensitivity analysis
        param_variations = {
            'tariff_rate': [0.5, 1.0, self.params['tariff_rate'], 2.0, 2.5],
            'affected_imports_share': [0.05, 0.1, self.params['affected_imports_share'], 0.2, 0.25],
            'passthrough_rate': [0.5, 0.6, self.params['passthrough_rate'], 0.85, 0.95],
            'substitution_rate': [0.2, 0.3, self.params['substitution_rate'], 0.5, 0.6]
        }
        
        sensitivity_results = run_sensitivity_analysis(self.params, param_variations)
        
        # Update results text
        peak_monthly = results['total_effect'].max()
        cumulative = results['cumulative_effect'].iloc[-1]
        
        self.results_var.set(
            f"Peak monthly inflation impact: {peak_monthly:.2f} percentage points\n"
            f"Cumulative {int(self.params['months']//12)}-year inflation impact: {cumulative:.2f} percentage points\n"
            f"------------------------------------------------------\n"
            f"Based on: {int(self.params['tariff_rate']*100)}% tariffs affecting "
            f"{int(self.params['affected_imports_share']*100)}% of Chinese imports"
        )
        
        # Generate and display plots
        impact_fig = plot_inflation_impact(results)
        sensitivity_fig = plot_sensitivity(sensitivity_results)
        
        # Add impact plot to canvas
        impact_canvas = FigureCanvasTkAgg(impact_fig, self.impact_canvas_frame)
        impact_canvas.draw()
        impact_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar for zooming and panning
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar_impact = NavigationToolbar2Tk(impact_canvas, self.impact_canvas_frame)
        toolbar_impact.update()
        
        # Add sensitivity plot to canvas
        sensitivity_canvas = FigureCanvasTkAgg(sensitivity_fig, self.sensitivity_canvas_frame)
        sensitivity_canvas.draw()
        sensitivity_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar for sensitivity plot
        toolbar_sensitivity = NavigationToolbar2Tk(sensitivity_canvas, self.sensitivity_canvas_frame)
        toolbar_sensitivity.update()

# Resource path helper (needed for PyInstaller)
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    # Set app icon if available
    try:
        icon_path = resource_path("tariff_icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except:
        pass
    
    # Configure styles properly
    style = ttk.Style()
    style.configure("Bold.TButton", font=("Arial", 14, "bold"))
    
    # Configure label frame headers font - proper way
    style.configure("TLabelframe.Label", font=("Arial", 14, "bold"))
    
    app = TariffModelApp(root)
    root.mainloop()