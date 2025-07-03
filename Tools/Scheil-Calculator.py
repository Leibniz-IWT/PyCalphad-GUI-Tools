# -*- coding: utf-8 -*-
"""
added fix for the Qt "cocoa" platform plugin issue.
This script dynamically finds the correct plugin path and sets the necessary
environment variable before initializing the Qt application.
"""
import sys
import os
import csv
import re
import webbrowser

# Scheil Solidification Calculator
# Nils Ellendt, University of Bremen, https://www.uni-bremen.de/mvt/dpp
# This Software is a part of: PyCalphad GUI Tools
# https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools



# --- START: CRITICAL QT PLATFORM PLUGIN FIX (REVISED) ---
def find_qt_plugin_path():
    """
    Dynamically finds the path to the Qt plugins directory.
    Searches for PySide6, PyQt6, PySide2, and PyQt5 in that order.
    """
    qt_bindings = [
        ('PySide6.QtCore', 'plugins'),
        ('PyQt6.QtCore', os.path.join('Qt6', 'plugins')),
        ('PySide2.QtCore', 'plugins'),
        ('PyQt5.QtCore', os.path.join('Qt', 'plugins'))
    ]
    for module_name, plugins_subdir in qt_bindings:
        try:
            module = __import__(module_name, fromlist=['QtCore'])
            base_path = os.path.dirname(module.__file__)
            plugin_path = os.path.join(base_path, plugins_subdir)
            if os.path.isdir(plugin_path):
                return plugin_path
        except ImportError:
            continue
    return None


print("--- Searching for Qt platform plugins...")
qt_plugin_path = find_qt_plugin_path()
if qt_plugin_path:
    print(f"--- Found Qt plugins directory: {qt_plugin_path}")
    os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
    print(f"--- Set QT_PLUGIN_PATH to: {os.environ['QT_PLUGIN_PATH']}")
else:
    print("--- Fatal Error: Could not find the Qt platform plugin directory.")
    print("--- Please ensure PyQt6, PySide6, PyQt5, or PySide2 is installed correctly.")
    sys.exit(1)

# --- END: CRITICAL QT PLATFORM PLUGIN FIX ---

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QComboBox, QFileDialog,
    QCheckBox, QDialog, QDialogButtonBox, QScrollArea
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, QTimer

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from pycalphad import Database, variables as v
from scheil import simulate_scheil_solidification
import numpy as np


# =============================================================================
# --- Phase Selection Dialog ---
# =============================================================================
class SelectPhasesDialog(QDialog):
    def __init__(self, all_phases, previously_selected_phases, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Solid Phases")
        self.setMinimumWidth(350)
        self.setMinimumHeight(400)
        self.solid_phases = sorted([p for p in all_phases if p.upper() not in ['VA', 'LIQUID']])
        self.checkboxes = []
        layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self._select_all)
        select_none_button = QPushButton("Select None")
        select_none_button.clicked.connect(self._select_none)
        button_layout.addWidget(select_all_button)
        button_layout.addWidget(select_none_button)
        layout.addLayout(button_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_widget)
        for phase in self.solid_phases:
            checkbox = QCheckBox(phase)
            checkbox.setChecked(phase in previously_selected_phases)
            self.checkboxes.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)

    def _select_all(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def _select_none(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def get_selected_phases(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]


class ScheilCalculatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            plt.style.use('standard.mplstyle')
            print("Successfully loaded 'standard.mplstyle'.")
        except OSError:
            print("Warning: 'standard.mplstyle' not found. Using default plot style.")

        self.setWindowTitle("Scheil Solidification Calculator")
        self.setGeometry(100, 100, 1200, 900)

        self.dbf = None
        self.available_elements = []
        self.molar_masses = {}
        self.last_sol_res = None
        self.all_phases = []
        self.selected_phases = []
        self.logo_label = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_input_form()

        action_button_layout = QHBoxLayout()
        self.calc_button = QPushButton("Calculate")
        self.calc_button.setEnabled(False)
        action_button_layout.addWidget(self.calc_button)
        self.select_phases_button = QPushButton("Select Phases")
        self.select_phases_button.setEnabled(False)
        action_button_layout.addWidget(self.select_phases_button)
        self.save_csv_button = QPushButton("Save Table (CSV)")
        self.save_csv_button.setEnabled(False)
        action_button_layout.addWidget(self.save_csv_button)
        self.save_svg_button = QPushButton("Save Figure (SVG)")
        self.save_svg_button.setEnabled(False)
        action_button_layout.addWidget(self.save_svg_button)
        action_button_layout.addWidget(QLabel("Figure Export Size (in):"))
        self.fig_width_entry = QLineEdit("8")
        self.fig_width_entry.setFixedWidth(50)
        action_button_layout.addWidget(self.fig_width_entry)
        action_button_layout.addWidget(QLabel("x"))
        self.fig_height_entry = QLineEdit("6")
        self.fig_height_entry.setFixedWidth(50)
        action_button_layout.addWidget(self.fig_height_entry)
        self.log_scale_checkbox = QCheckBox("Log Scale")
        action_button_layout.addWidget(self.log_scale_checkbox)
        action_button_layout.addStretch()
        self.main_layout.addLayout(action_button_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        canvas_container = self.setup_matplotlib_canvas()
        self.splitter.addWidget(canvas_container)
        self.setup_results_table()
        self.splitter.addWidget(self.results_table)
        self.main_layout.addWidget(self.splitter)

        self._connect_signals()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.update_splitter_position)

    def create_input_form(self):
        """Creates the grid layout for all user inputs and the logo."""
        form_container_layout = QHBoxLayout()
        form_layout = QGridLayout()

        LOGO_FILENAME = 'pycalphad-logo-withtext.png'
        if os.path.exists(LOGO_FILENAME):
            self.logo_label = QLabel()
            pixmap = QPixmap(LOGO_FILENAME)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaledToHeight(75, Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
                self.logo_label.setToolTip("Visit the pycalphad website (pycalphad.org)")
                # MODIFIED: Added AlignHCenter to center the logo horizontally in its cell
                form_layout.addWidget(self.logo_label, 0, 0, 2, 1,
                                      Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            else:
                self.logo_label = None

        title_label = QLabel("Scheil Solidification Calculator")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        form_layout.addWidget(title_label, 0, 1, 1, 4)

        db_layout = QHBoxLayout()
        self.about_button = QPushButton("About")
        self.about_button.setFixedWidth(80)
        db_layout.addWidget(self.about_button)
        self.load_db_button = QPushButton("Browse...")
        self.load_db_button.setFixedWidth(100)
        db_layout.addWidget(self.load_db_button)
        db_layout.addWidget(QLabel("Current Database:"))
        self.current_db_label = QLabel("None loaded")
        self.current_db_label.setStyleSheet("font-style: italic;")
        db_layout.addWidget(self.current_db_label)
        db_layout.addStretch()
        form_layout.addLayout(db_layout, 1, 1, 1, 4)

        form_layout.addWidget(QLabel("Start Temperature:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        temp_layout = QHBoxLayout()
        self.temp_entry = QLineEdit("1500")
        self.temp_entry.setFixedWidth(100)
        self.temp_unit_combo = QComboBox()
        self.temp_unit_combo.addItems(["°C", "K"])
        self.temp_unit_combo.setFixedWidth(60)
        temp_layout.addWidget(self.temp_entry)
        temp_layout.addWidget(self.temp_unit_combo)
        form_layout.addLayout(temp_layout, 2, 1)

        form_layout.addWidget(QLabel("Step:"), 2, 2, Qt.AlignmentFlag.AlignRight)
        step_layout = QHBoxLayout()
        self.temp_step_entry = QLineEdit("1.0")
        self.temp_step_entry.setFixedWidth(60)
        step_layout.addWidget(self.temp_step_entry)
        self.sci_notation_checkbox = QCheckBox("Sci. Notation")
        step_layout.addWidget(self.sci_notation_checkbox)
        form_layout.addLayout(step_layout, 2, 3)

        form_layout.addWidget(QLabel("Concentration Unit:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Mass %", "Atom %"])
        self.unit_combo.setFixedWidth(120)
        form_layout.addWidget(self.unit_combo, 3, 1)

        form_layout.addWidget(QLabel("Base Element:"), 4, 0, Qt.AlignmentFlag.AlignRight)
        self.base_element_combo = QComboBox()
        self.base_element_combo.setFixedWidth(120)
        form_layout.addWidget(self.base_element_combo, 4, 1)

        form_layout.addWidget(QLabel("Atom %:"), 3, 2, Qt.AlignmentFlag.AlignRight)
        self.atom_comp_label = QLabel("...")
        self.atom_comp_label.setMinimumWidth(180)
        form_layout.addWidget(self.atom_comp_label, 3, 3)

        form_layout.addWidget(QLabel("Mass %:"), 4, 2, Qt.AlignmentFlag.AlignRight)
        self.mass_comp_label = QLabel("...")
        self.mass_comp_label.setMinimumWidth(180)
        form_layout.addWidget(self.mass_comp_label, 4, 3)

        solute_header = QLabel("Solute Elements")
        solute_header.setStyleSheet("font-weight: bold; margin-top: 15px;")
        form_layout.addWidget(solute_header, 5, 0, 1, 5)

        solute_grid = QGridLayout()
        solute_grid.addWidget(QLabel("Element"), 0, 1)
        solute_grid.addWidget(QLabel("Concentration"), 0, 2)
        solute_grid.addWidget(QLabel("Element"), 0, 4)
        solute_grid.addWidget(QLabel("Concentration"), 0, 5)

        self.solute_combos, self.conc_entries = [], []
        for i in range(6):
            row = (i % 3) + 1
            col_offset = 0 if i < 3 else 3
            solute_grid.addWidget(QLabel(f"Solute {i + 1}:"), row, col_offset, Qt.AlignmentFlag.AlignRight)
            element_combo = QComboBox()
            element_combo.setFixedWidth(120)
            self.solute_combos.append(element_combo)
            solute_grid.addWidget(element_combo, row, col_offset + 1)
            conc_entry = QLineEdit()
            conc_entry.setFixedWidth(120)
            self.conc_entries.append(conc_entry)
            solute_grid.addWidget(conc_entry, row, col_offset + 2)

        form_layout.addLayout(solute_grid, 6, 0, 1, 5)

        form_layout.setColumnStretch(5, 1)

        form_container_layout.addLayout(form_layout)
        self.main_layout.addLayout(form_container_layout)

    def _connect_signals(self):
        self.calc_button.clicked.connect(self.run_simulation)
        self.select_phases_button.clicked.connect(self._on_select_phases_clicked)
        self.save_csv_button.clicked.connect(self.save_table_csv)
        self.save_svg_button.clicked.connect(self.save_figure_svg)
        self.about_button.clicked.connect(self.show_about_dialog)
        self.load_db_button.clicked.connect(self.open_database_file_dialog)
        self.unit_combo.currentTextChanged.connect(self.update_composition_display)
        self.base_element_combo.currentTextChanged.connect(self.update_composition_display)
        for combo in self.solute_combos:
            combo.currentTextChanged.connect(self.update_composition_display)
        for entry in self.conc_entries:
            entry.textChanged.connect(self.update_composition_display)
        self.temp_unit_combo.currentTextChanged.connect(self.update_output_display)
        self.sci_notation_checkbox.stateChanged.connect(self.update_all_displays)
        self.log_scale_checkbox.stateChanged.connect(self.update_output_display)
        self.fig_width_entry.textChanged.connect(self.update_splitter_position)
        self.fig_height_entry.textChanged.connect(self.update_splitter_position)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)

        if self.logo_label:
            self.logo_label.mousePressEvent = self._open_pycalphad_website

    def _open_pycalphad_website(self, event):
        webbrowser.open('https://pycalphad.org/')

    def on_splitter_moved(self, pos, index):
        if index != 1: return
        try:
            container_widget = self.canvas.parent()
            canvas_height = container_widget.height() - (container_widget.layout().contentsMargins().top() * 2)
            canvas_width = container_widget.width() - (container_widget.layout().contentsMargins().left() * 2)
            if canvas_height <= 0 or canvas_width <= 0: return
            new_width_ratio = (canvas_width / canvas_height) * 6.0
            self.fig_width_entry.blockSignals(True)
            self.fig_height_entry.blockSignals(True)
            self.fig_width_entry.setText(f"{new_width_ratio:.2f}")
            self.fig_height_entry.setText("6.00")
            self.fig_width_entry.blockSignals(False)
            self.fig_height_entry.blockSignals(False)
        except Exception:
            pass

    def update_all_displays(self):
        self.update_composition_display()
        self.update_output_display()

    def open_database_file_dialog(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Load Database", "", "TDB Files (*.tdb *.TDB);;All Files (*)")
        if filePath:
            self.load_database_from_path(filePath)

    def load_database_from_path(self, dbf_path):
        if not os.path.exists(dbf_path):
            self.dbf = None
            self.calc_button.setEnabled(False)
            self.select_phases_button.setEnabled(False)
            self.current_db_label.setText("None loaded")
            return
        try:
            self.dbf = Database(dbf_path)
            self.molar_masses = {}
            with open(dbf_path, 'r', errors='ignore') as f:
                for line in f:
                    clean_line = line.strip().upper()
                    if clean_line.startswith("ELEMENT "):
                        parts = clean_line.split()
                        if len(parts) >= 4:
                            try:
                                self.molar_masses[parts[1]] = float(parts[3])
                            except (ValueError, IndexError):
                                continue
            self.available_elements = sorted([el for el in self.molar_masses.keys() if el not in ['VA', '/-']])
            self.current_db_label.setText(os.path.basename(dbf_path))
            self.base_element_combo.clear()
            self.base_element_combo.addItems(self.available_elements)
            for i in range(len(self.solute_combos)):
                self.solute_combos[i].clear()
                self.solute_combos[i].addItem("")
                self.solute_combos[i].addItems(self.available_elements)
                self.conc_entries[i].clear()

            self.all_phases = sorted(self.dbf.phases.keys())
            self.selected_phases = [p for p in self.all_phases if p.upper() not in ['VA', 'LIQUID']]
            self.select_phases_button.setEnabled(True)
            print(f"Database loaded. Initial solid phases selected: {self.selected_phases}")

            self.ax.clear()
            self.canvas.draw()
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(2)
            self.results_table.setHorizontalHeaderLabels(["Temperature", "Liquid Fraction"])
            self.save_csv_button.setEnabled(False)
            self.save_svg_button.setEnabled(False)
            self.last_sol_res = None
            self.calc_button.setEnabled(True)
            self.update_composition_display()
        except Exception as e:
            self.show_error_message(f"Failed to load database '{dbf_path}':\n{e}")
            self.dbf = None
            self.calc_button.setEnabled(False)
            self.select_phases_button.setEnabled(False)
            self.current_db_label.setText("Load Failed")

    def _on_select_phases_clicked(self):
        if not self.dbf:
            self.show_error_message("Please load a TDB database file first.")
            return
        dialog = SelectPhasesDialog(self.all_phases, self.selected_phases, self)
        if dialog.exec():
            self.selected_phases = dialog.get_selected_phases()
            print(f"New solid phase selection: {self.selected_phases}")
        else:
            print("Phase selection cancelled.")

    def get_composition_from_ui(self):
        base_element = self.base_element_combo.currentText()
        if not base_element or not self.dbf: return "No DB Loaded", "No DB Loaded"
        try:
            comps_in = {base_element: 0.0}
            for i in range(len(self.solute_combos)):
                el = self.solute_combos[i].currentText()
                conc_str = self.conc_entries[i].text().strip()
                if el and conc_str: comps_in[el] = float(conc_str)
        except (ValueError, TypeError):
            return "Invalid Number", "Invalid Number"
        solutes = {k: v for k, v in comps_in.items() if k != base_element}
        if not solutes: return {base_element: 100.0}, {base_element: 100.0}
        total_solute_val = sum(solutes.values())
        if total_solute_val >= 100: return "Total > 100%", "Total > 100%"
        unit = self.unit_combo.currentText()
        atom_percents, mass_percents = {}, {}
        if unit == 'Mass %':
            if any(el not in self.molar_masses for el in comps_in):
                missing = [el for el in comps_in if el not in self.molar_masses][0]
                return f"No mass for {missing}", f"No mass for {missing}"
            mass_percents = solutes.copy();
            mass_percents[base_element] = 100 - total_solute_val
            moles = {el: mass / self.molar_masses[el] for el, mass in mass_percents.items()}
            total_moles = sum(moles.values())
            atom_percents = {el: (mol / total_moles) * 100 for el, mol in moles.items()} if total_moles > 0 else {}
        else:
            atom_percents = solutes.copy();
            atom_percents[base_element] = 100 - total_solute_val
            can_calc_mass = all(el in self.molar_masses for el in atom_percents)
            if can_calc_mass:
                masses = {el: at_pct * self.molar_masses[el] for el, at_pct in atom_percents.items()}
                total_mass = sum(masses.values())
                mass_percents = {el: (m / total_mass) * 100 for el, m in masses.items()} if total_mass > 0 else {}
            else:
                mass_percents = "No mass data"
        return atom_percents, mass_percents

    def update_composition_display(self):
        is_scientific = self.sci_notation_checkbox.isChecked()
        fmt_spec = ".3e" if is_scientific else ".2f"
        atom_pcts, mass_pcts = self.get_composition_from_ui()
        if isinstance(atom_pcts, str):
            self.atom_comp_label.setText(f"<font color='red'>{atom_pcts}</font>")
        elif isinstance(atom_pcts, dict):
            self.atom_comp_label.setText(
                ", ".join([f"{el}: {val:{fmt_spec}}" for el, val in sorted(atom_pcts.items())]))
        if isinstance(mass_pcts, str):
            self.mass_comp_label.setText(f"<font color='orange'>{mass_pcts}</font>")
        elif isinstance(mass_pcts, dict):
            self.mass_comp_label.setText(
                ", ".join([f"{el}: {val:{fmt_spec}}" for el, val in sorted(mass_pcts.items())]))

    def run_simulation(self):
        atom_percents, _ = self.get_composition_from_ui()
        if not isinstance(atom_percents, dict) or len(atom_percents) <= 1:
            self.show_error_message("Invalid composition or no solutes entered. Please check the inputs.")
            return
        try:
            self.last_sol_res = None
            self.ax.clear()
            self.ax.set_title("Calculating...")
            self.canvas.draw()
            self.results_table.setRowCount(0)
            self.save_csv_button.setEnabled(False)
            self.save_svg_button.setEnabled(False)
            QApplication.processEvents()
            start_temp = float(self.temp_entry.text())
            temp_step = float(self.temp_step_entry.text())
            temp_unit = self.temp_unit_combo.currentText()
            start_temp_k = start_temp + 273.15 if temp_unit == "°C" else start_temp
            base_element = self.base_element_combo.currentText()
            mole_fractions = {el: val / 100.0 for el, val in atom_percents.items()}
            initial_composition = {v.X(el): frac for el, frac in mole_fractions.items() if el != base_element}
            component_list = list(atom_percents.keys()) + ['VA']
            phases = ['LIQUID', 'VA'] + self.selected_phases

            self.calc_button.setText("Calculating...");
            self.calc_button.setEnabled(False)
            self.last_sol_res = simulate_scheil_solidification(self.dbf, component_list, phases, initial_composition,
                                                               start_temp_k, temp_step, liquid_phase_name='LIQUID')
            self.last_comps = component_list
            self.update_output_display()
        except Exception as e:
            self.show_error_message(f"An error occurred during simulation:\n{e}")
            self.ax.clear()
            self.ax.set_title("Calculation Failed")
            self.canvas.draw()
        finally:
            self.calc_button.setText("Calculate")
            if self.dbf is not None: self.calc_button.setEnabled(True)

    def show_about_dialog(self):
        about_text = """
        <b>Scheil Solidification Calculator</b><br><br>
        Version: 1.0<br>
        Author: Nils Ellendt, University of Bremen<br>
        https://www.uni-bremen.de/mvt/dpp<br>
        ellendt@uni-bremen.de<br>
        <a href='https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools'>Find it on GitHub</a>        
        """
        msg_box = QMessageBox(self);
        msg_box.setWindowTitle("About Scheil Solidification Calculator")
        msg_box.setTextFormat(Qt.TextFormat.RichText);
        msg_box.setText(about_text);
        msg_box.exec()

    def setup_matplotlib_canvas(self):
        self.figure = Figure(dpi=100)
        self.canvas = FigureCanvas(self.figure)
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(2, 2, 2, 2)
        canvas_layout.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111)
        return canvas_container

    def setup_results_table(self):
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Temperature", "Liquid Fraction"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def update_splitter_position(self):
        try:
            width_ratio = float(self.fig_width_entry.text())
            height_ratio = float(self.fig_height_entry.text())
            if width_ratio <= 0 or height_ratio <= 0: return
            container_widget = self.canvas.parent()
            canvas_height = container_widget.height() - (container_widget.layout().contentsMargins().top() * 2)
            if canvas_height < 50: return
            desired_canvas_width = canvas_height * (width_ratio / height_ratio)
            total_width = self.splitter.width()
            table_width = total_width - desired_canvas_width
            min_table_width = 250
            if table_width < min_table_width:
                table_width = min_table_width
                desired_canvas_width = total_width - table_width
            if desired_canvas_width > 0:
                self.splitter.blockSignals(True)
                self.splitter.setSizes([int(desired_canvas_width), int(table_width)])
                self.splitter.blockSignals(False)
                self.figure.tight_layout(pad=0.5)
                self.canvas.draw_idle()
        except (ValueError, ZeroDivisionError, AttributeError):
            pass

    def _plot_scheil_data(self, ax):
        if self.last_sol_res is None:
            ax.clear()
            ax.set_title("No Data")
            return

        ax.clear()
        temp_unit = self.temp_unit_combo.currentText()
        kelvin_temperatures = np.array(self.last_sol_res.temperatures)
        display_temperatures = kelvin_temperatures - 273.15 if temp_unit == "°C" else kelvin_temperatures
        all_plot_data = []

        for name, amounts in self.last_sol_res.cum_phase_amounts.items():
            if np.sum(amounts) > 1e-6:
                ax.plot(display_temperatures, amounts, label=name, linewidth=2.5)
                all_plot_data.append(np.array(amounts))

        ax.plot(display_temperatures, self.last_sol_res.fraction_liquid, label='LIQUID', linestyle='--', linewidth=2.5)
        all_plot_data.append(np.array(self.last_sol_res.fraction_liquid))

        ax.set_xlabel(f'Temperature ({temp_unit})')
        ax.set_ylabel('Phase Fraction')
        ax.legend(loc='center right')
        ax.grid(False)

        if self.log_scale_checkbox.isChecked():
            ax.set_yscale('log')
            min_val = np.inf
            for data_array in all_plot_data:
                non_zero_vals = data_array[data_array > 0]
                if non_zero_vals.size > 0:
                    current_min = np.min(non_zero_vals)
                    if current_min < min_val:
                        min_val = current_min
            if np.isfinite(min_val) and min_val > 0:
                ax.set_ylim(bottom=min_val)
        else:
            ax.set_yscale('linear')

    def update_output_display(self):
        if self.last_sol_res is None:
            return

        self._plot_scheil_data(self.ax)
        self.figure.tight_layout(pad=0.5)
        self.canvas.draw()

        temp_unit = self.temp_unit_combo.currentText()
        is_scientific = self.sci_notation_checkbox.isChecked()
        frac_fmt_spec = ".4e" if is_scientific else ".4f"
        kelvin_temperatures = np.array(self.last_sol_res.temperatures)
        display_temperatures = kelvin_temperatures - 273.15 if temp_unit == "°C" else kelvin_temperatures

        self.results_table.setRowCount(0)
        forming_phases = [p for p, a in self.last_sol_res.cum_phase_amounts.items() if np.sum(a) > 1e-6]
        headers = [f"Temperature ({temp_unit})", "LIQUID"] + forming_phases
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        num_points = len(self.last_sol_res.temperatures)
        self.results_table.setRowCount(num_points)
        for row in range(num_points):
            self.results_table.setItem(row, 0, QTableWidgetItem(f"{display_temperatures[row]:.1f}"))
            self.results_table.setItem(row, 1,
                                       QTableWidgetItem(format(self.last_sol_res.fraction_liquid[row], frac_fmt_spec)))
            for col, phase in enumerate(forming_phases, 2):
                self.results_table.setItem(row, col, QTableWidgetItem(
                    format(self.last_sol_res.cum_phase_amounts[phase][row], frac_fmt_spec)))
        self.save_csv_button.setEnabled(True)
        self.save_svg_button.setEnabled(True)

    def save_table_csv(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Table Data", "", "CSV Files (*.csv);;All Files (*)")
        if not filePath: return
        try:
            with open(filePath, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = [self.results_table.horizontalHeaderItem(i).text() for i in
                           range(self.results_table.columnCount())]
                writer.writerow(headers)
                for row in range(self.results_table.rowCount()):
                    writer.writerow(
                        [self.results_table.item(row, col).text() for col in range(self.results_table.columnCount())])
            QMessageBox.information(self, "Success", "Table data saved successfully.")
        except Exception as e:
            self.show_error_message(f"Could not save file:\n{e}")

    def save_figure_svg(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Figure", "", "SVG Files (*.svg);;All Files (*)")
        if not filePath: return
        if self.last_sol_res is None:
            self.show_error_message("No data to save. Please run a calculation first.")
            return
        try:
            width = float(self.fig_width_entry.text())
            height = float(self.fig_height_entry.text())
            save_fig = Figure(figsize=(width, height), dpi=300)

            with plt.style.context('standard.mplstyle'):
                save_ax = save_fig.add_subplot(111)
                self._plot_scheil_data(save_ax)
                save_fig.tight_layout(pad=0.5)
                save_fig.savefig(filePath, format='svg')

            QMessageBox.information(self, "Success", "Figure saved successfully.")
        except ValueError:
            self.show_error_message("Invalid figure dimensions. Please enter numeric values.")
        except Exception as e:
            self.show_error_message(f"Could not save figure:\n{e}")

    def show_error_message(self, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("Error")
        msg_box.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = ScheilCalculatorApp()
    main_win.show()
    sys.exit(app.exec())