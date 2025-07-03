# -*- coding: utf-8 -*-
"""
Database Browser by Nils Ellendt, with an added fix for the Qt "cocoa" platform plugin issue.
This script dynamically finds the correct plugin path and sets the necessary
environment variable before initializing the Qt application.
"""
import sys
import re
import os


# --- START: CRITICAL QT PLATFORM PLUGIN FIX (REVISED) ---
# This entire block must run BEFORE any other Qt modules are imported.
# It solves the "Could not find the Qt platform plugin 'cocoa'" error.

def find_qt_plugin_path():
    """
    Dynamically finds the path to the Qt plugins directory.
    Searches for PySide6, PyQt6, PySide2, and PyQt5 in that order.
    """
    # List of potential Qt bindings and their path structures
    qt_bindings = [
        ('PySide6.QtCore', 'plugins'),
        ('PyQt6.QtCore', os.path.join('Qt6', 'plugins')),
        ('PySide2.QtCore', 'plugins'),
        ('PyQt5.QtCore', os.path.join('Qt', 'plugins'))
    ]

    for module_name, plugins_subdir in qt_bindings:
        try:
            # Dynamically import the QtCore module from the current binding
            module = __import__(module_name, fromlist=['QtCore'])
            # Get the directory of the imported module
            base_path = os.path.dirname(module.__file__)
            # Construct the full path to the plugins directory
            plugin_path = os.path.join(base_path, plugins_subdir)

            if os.path.isdir(plugin_path):
                # If the plugins directory exists, we've found our path.
                # We return the parent 'plugins' directory, which is more robust.
                return plugin_path

        except ImportError:
            # This Qt binding is not installed, so we continue to the next one
            continue

    # If no path was found after checking all bindings
    return None


# Find and set the plugin path
print("--- Searching for Qt platform plugins...")
qt_plugin_path = find_qt_plugin_path()

if qt_plugin_path:
    print(f"--- Found Qt plugins directory: {qt_plugin_path}")
    os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
    print(f"--- Set QT_PLUGIN_PATH to: {os.environ['QT_PLUGIN_PATH']}")
else:
    print("--- Fatal Error: Could not find the Qt platform plugin directory.")
    print("--- Please ensure PyQt6, PySide6, PyQt5, or PySide2 is installed correctly.")
    sys.exit(1)  # Exit if no valid path is found

# --- END: CRITICAL QT PLATFORM PLUGIN FIX ---


# --- START: ORIGINAL DATABASE BROWSER CODE ---
# The rest of the code is the original script. It can now be imported and run safely.

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QFileDialog,
    QListWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QMessageBox,
    QLabel,
    QTextEdit,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

from pycalphad import Database


# Database Browser
# Nils Ellendt, University of Bremen, https://www.uni-bremen.de/mvt/dpp
# This Software is a part of: PyCalphad GUI Tools
# https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools

class TDBReaderApp(QMainWindow):
    """
    A PyQt6 application to read a TDB file and list its elements, phases,
    and show details about a selected item.
    """

    def __init__(self):
        super().__init__()

        # This will hold the loaded database object and the file path
        self.db = None
        self.current_file_path = None

        # --- Window Properties ---
        self.setWindowTitle("Database Browser")
        self.setGeometry(100, 100, 700, 600)  # x, y, width, height

        # --- Central Widget and Main Layout ---
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # --- Top Section with Grid Layout for Alignment ---
        top_grid_layout = QGridLayout()

        # --- Row 0: Buttons and DB Label ---
        button_layout = QHBoxLayout()
        self.open_button = QPushButton("Open TDB File")
        self.open_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.open_button.clicked.connect(self.open_file_dialog)

        self.about_button = QPushButton("About")
        self.about_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.about_button.clicked.connect(self.show_about_dialog)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.about_button)
        button_layout.addStretch()  # Spacer to keep buttons to the left

        top_grid_layout.addLayout(button_layout, 0, 0)

        self.db_label = QLabel("No database loaded.")
        self.db_label.setStyleSheet("color: grey;")
        top_grid_layout.addWidget(self.db_label, 0, 1, Qt.AlignmentFlag.AlignRight)

        # --- Row 1: List Labels ---
        element_label = QLabel("Elements")
        phase_label = QLabel("Phases")
        top_grid_layout.addWidget(element_label, 1, 0)
        top_grid_layout.addWidget(phase_label, 1, 1)

        # --- Row 2: List Widgets ---
        self.element_list_widget = QListWidget(self)
        self.phase_list_widget = QListWidget(self)
        top_grid_layout.addWidget(self.element_list_widget, 2, 0)
        top_grid_layout.addWidget(self.phase_list_widget, 2, 1)

        top_grid_layout.setColumnStretch(0, 1)
        top_grid_layout.setColumnStretch(1, 1)

        main_layout.addLayout(top_grid_layout)

        # --- Bottom Section for Details ---
        details_widget = QWidget()
        details_layout = QVBoxLayout()
        details_widget.setLayout(details_layout)
        details_label = QLabel("Details")
        details_layout.addWidget(details_label)
        self.details_text_edit = QTextEdit(self)
        self.details_text_edit.setReadOnly(True)
        self.details_text_edit.setFontFamily("Courier")
        details_layout.addWidget(self.details_text_edit)
        main_layout.addWidget(details_widget)

        main_layout.setStretch(0, 1)  # Grid layout gets 1 part
        main_layout.setStretch(1, 1)  # Details section gets 1 part

        # --- Connect Signals ---
        self.phase_list_widget.itemClicked.connect(self.display_phase_details)
        self.element_list_widget.itemClicked.connect(self.display_element_interactions)

    def open_file_dialog(self):
        """
        Opens a file dialog to allow the user to select a .tdb file.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open TDB File",
            "",
            "TDB Files (*.tdb);;All Files (*)",
        )
        if file_path:
            self.current_file_path = file_path
            self.read_tdb_file(file_path)
            self.db_label.setText(f"Current DB: {os.path.basename(file_path)}")
            self.db_label.setStyleSheet("color: black;")

    def read_tdb_file(self, file_path):
        """
        Reads the selected TDB file using pycalphad and populates the list widgets.
        """
        self.element_list_widget.clear()
        self.phase_list_widget.clear()
        self.details_text_edit.clear()

        try:
            self.db = Database(file_path)
            elements = sorted([str(el) for el in self.db.elements if str(el).upper() != '/-'])
            self.element_list_widget.addItems(elements)
            phases = sorted(list(self.db.phases.keys()))
            self.phase_list_widget.addItems(phases)
        except Exception as e:
            self.db = None
            self.current_file_path = None
            self.db_label.setText("Failed to load DB.")
            self.db_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Error", f"Failed to read TDB file:\n{e}")

    def display_phase_details(self, item):
        """
        Displays details for the selected phase in the text edit area.
        """
        if not self.db: return
        self.details_text_edit.clear()
        phase_name = item.text()
        phase_obj = self.db.phases.get(phase_name)
        if not phase_obj: return

        details_text = f"--- Details for {phase_name} ---\n\n"
        all_constituents = set()
        for sublattice in phase_obj.constituents:
            all_constituents.update(sublattice)

        constituents = sorted([str(c) for c in all_constituents if str(c).upper() != '/-'])
        details_text += f"Constituents: {', '.join(constituents)}\n\n"

        sublattice_model = ""
        try:
            site_ratios = phase_obj.sublattices
            sublattices = phase_obj.constituents
            formatted_sublattices = []
            for i, sub in enumerate(sublattices):
                sub_str = "(" + ", ".join(sorted([str(s) for s in sub])) + ")" + str(site_ratios[i])
                formatted_sublattices.append(sub_str)
            sublattice_model = " ".join(formatted_sublattices)
        except Exception as e:
            sublattice_model = f"Could not determine sublattice model. Error: {e}"
        details_text += f"Sublattice Model: {sublattice_model}\n"
        self.details_text_edit.setText(details_text)

    def display_element_interactions(self, item):
        """
        Parses the raw TDB file to find molar mass, reference data, and unique
        interactions involving the selected element.
        """
        if not self.current_file_path: return
        self.details_text_edit.clear()
        selected_element = item.text().upper()

        ref_phase, molar_mass, hser, sser = None, None, None, None
        unique_interactions = set()
        param_regex = re.compile(r'\(([^,]+),([^;]+);')

        try:
            with open(self.current_file_path, 'r', errors='ignore') as tdb_file:
                for line in tdb_file:
                    clean_line = line.strip().upper()
                    if not clean_line or clean_line.startswith('$'): continue

                    if clean_line.startswith("ELEMENT "):
                        parts = clean_line.split()
                        if len(parts) >= 6 and parts[1] == selected_element:
                            ref_phase, molar_mass, hser, sser = parts[2], parts[3], parts[4], parts[5]

                    if clean_line.startswith("PARAMETER"):
                        match = param_regex.search(clean_line)
                        if match:
                            phase_name = match.group(1).strip()
                            constituents_str = match.group(2).strip()
                            elements_str = constituents_str.replace(',', ' ').replace(':', ' ')
                            core_elements = {e for e in elements_str.split() if e}

                            if selected_element in core_elements and len(core_elements) > 1:
                                interaction_tuple = (phase_name, tuple(sorted(list(core_elements))))
                                unique_interactions.add(interaction_tuple)
        except Exception as e:
            self.details_text_edit.setText(f"An unexpected error occurred while parsing the file:\n\n{e}")
            return

        # --- Build the final output string ---
        details_text = f"--- Details for {item.text()} ---\n\n"

        # --- FIX: Use f-string formatting for perfect alignment ---
        label_width = 22
        details_text += f"{'Reference Phase:':<{label_width}}{ref_phase or 'Not found'}\n"
        details_text += f"{'Molar Mass (g/mol):':<{label_width}}{molar_mass or 'Not found'}\n"
        details_text += f"{'HSER (J/mol):':<{label_width}}{hser or 'Not found'}\n"
        details_text += f"{'SSER (J/mol-K):':<{label_width}}{sser or 'Not found'}\n"

        details_text += "\n--- Unique Interactions ---\n\n"

        if not unique_interactions:
            details_text += "No interaction parameters found for this element."
        else:
            formatted_list = []
            for phase, elements in sorted(list(unique_interactions)):
                interaction_str = "-".join(elements)
                formatted_list.append(f"Phase: {phase:<15} Interaction: {interaction_str}")
            details_text += "\n".join(formatted_list)

        self.details_text_edit.setText(details_text)

    def show_about_dialog(self):
        """
        Displays the 'About' information in a message box.
        """
        about_text = """
        <b>Database Browser</b><br><br>
        Version: 1.0<br>
        Author: Nils Ellendt, University of Bremen<br>
        https://www.uni-bremen.de/mvt/dpp<br>
        ellendt@uni-bremen.de<br>
        <br>
        A simple utility to inspect the contents of thermodynamic
        database files (.tdb) using Python, PyQt6, and PyCalphad.<br><br>
        <a href='https://github.com/Leibniz-IWT/PyCalphad-GUI-Tools'>Find it on GitHub</a>
        """
        QMessageBox.about(self, "About TDB Viewer", about_text)


def main():
    app = QApplication(sys.argv)
    window = TDBReaderApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
