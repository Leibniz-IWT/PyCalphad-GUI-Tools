# PyCalphad-GUI-Tools

This repository hosts a collection of graphical user interface (GUI) tools built with Python, PyQt6, and the powerful `pycalphad` library. The goal is to provide easy-to-use interfaces for common computational thermodynamics tasks, making them accessible to a broader audience without requiring extensive scripting knowledge.

This project is hosted at: [https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools/](https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools/)

## Tools Included

1.  **Database Browser**: A utility to quickly inspect the contents of Thermo-Calc database files (`.tdb`). It allows you to view elements, phases, and detailed parameters without manually parsing the file.
2.  **Scheil Solidification Calculator**: A comprehensive tool for performing Scheil-Gulliver solidification simulations. It enables users to define an alloy composition, run the simulation, and visualize the results in both graphical and tabular formats.

## Installation and Usage

To use these tools, you need a Python environment with a few key libraries installed.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools.git
    cd PyCalphad-GUI-Tools
    ```

2.  **Install required packages:**
    The tools rely on `PyQt6`, `pycalphad`, `matplotlib`, `numpy`, and `scheil`. You can install them using pip:

    ```bash
    pip install PyQt6 pycalphad matplotlib numpy scheil
    ```

3.  **Run a tool:**
    Navigate to the tool's directory and run the Python script.
    *For the Database Browser:*

    ```bash
    python Database-Browser.py
    ```

    *For the Scheil Calculator:*

    ```bash
    python Scheil-Calculator.py
    ```

## Contributing

Contributions, bug reports, and feature requests are welcome\! Please feel free to open an issue or submit a pull request on the GitHub repository.

-----

## TDB Database Browser

The TDB Database Browser is a straightforward utility designed to help you quickly inspect and understand the contents of your Thermo-Calc database (`.tdb`) files. You can either select an element to show element information and included interactions or you can select a phase to show phase information.

<img src="https://github.com/user-attachments/assets/7b752655-a4b7-4d78-acf3-6a5a1572e450" alt="Database Browser Element Info" width="450">
<img src="https://github.com/user-attachments/assets/0a141b22-58b7-4a18-96d6-a65f99326d13" alt="Database Browser Phase Info" width="450">

### Features

  * **Open and Parse TDB Files**: Easily load any `.tdb` file using a simple file dialog.
  * **List Elements and Phases**: Instantly see two lists populated with all the elements and phases defined in the database.
  * **View Element Details**: Click on an element to see its reference state data (HSER, SSER), molar mass, and a comprehensive list of all binary and higher-order interaction parameters it is involved in.
  * **Inspect Phase Details**: Select a phase to view its constituent elements and its full sublattice model, providing a clear picture of its structure.

### How to Use

1.  **Launch the application**: Run the `Database-Browser.py` script.
2.  **Open a File**: Click the **"Open TDB File"** button and select the database you wish to inspect.
3.  **Explore**:
      * The **Elements** and **Phases** lists will be populated.
      * Click on any element in the left list to see its reference data and interaction parameters in the "Details" panel.
      * Click on any phase in the right list to view its constituents and sublattice model in the "Details" panel.

-----

## Scheil Solidification Calculator

The Scheil Solidification Calculator provides a user-friendly graphical interface for performing Scheil-Gulliver solidification simulations. It leverages `pycalphad` and the `scheil` library to calculate and visualize the phase evolution during cooling under the assumption of no diffusion in the solid phases and infinite diffusion in the liquid.

<img src="https://github.com/user-attachments/assets/ab44d06a-1491-438e-bb35-11b302fbb297" alt="Database Browser Element Info" width="450">
<img src="https://github.com/user-attachments/assets/101abec2-8502-439a-beb1-61be01b837a0" alt="Database Browser Phase Info" width="300">



### Features

  * **Interactive Alloy Definition**:
      * Load any compatible `.tdb` database.
      * Select a base element and up to six solute elements.
      * Define compositions in either **Mass %** or **Atom %**.
      * See the composition in both units update in real-time.
      * Select phases to be included
  * **Flexible Calculation Control**:
      * Set the starting temperature and temperature step for the simulation.
      * Choose between Celsius and Kelvin for temperature inputs and displays.
  * **Rich Results Visualization**:
      * Plots the fraction of each forming phase as a function of temperature.
      * Displays the full solidification data in a clear, sortable table.
  * **Easy Data Export**:
      * Save the solidification plot as a high-quality **SVG** file. Figure size can be changed and a template file is used that can be adjusted to your style. The default template is our neatplot style (https://github.com/Leibniz-IWT/neatplot/tree/main)
      * Export the complete results table to a **CSV** file for further analysis in other software.
  * **Conversion between Mass-% and Atom-%**:
      * If you use the SGTE Pure Element Database (https://www.sgte.net/en/free-pure-elements-database), you can use the tool to easily convert compositions with up to 7 elements
### How to Use

1.  **Launch the application**: Run the `Scheil-Calculator.py` script.
2.  **Load a Database**: Click **"Open TDB file"** and select a valid database. The element dropdowns will be populated automatically.
3.  **Define Composition**:
      * Select the **Base Element**.
      * Choose up to six **Solute Elements** from the dropdowns and enter their concentration values.
      * Select whether the entered concentrations are in **Mass %** or **Atom %**.
4.  **Set Parameters**:
      * Enter the **Start Temperature** and **Step** size for the calculation.
      * Select the desired temperature unit (°C or K).
5.  **Calculate**: Click the **"Calculate"** button. The plot and results table will be updated once the simulation is complete.
6.  **Export (Optional)**:
      * Click **"Save Table (CSV)"** to save the numerical results.
      * Click **"Save Figure (SVG)"** to save the generated plot.
