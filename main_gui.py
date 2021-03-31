import sys

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QDialog, QWidget, QMainWindow, QFileDialog
from PyQt5.uic import loadUi

import heatmodel as hm
import calfem.ui as cfui

class SolverThread(QThread):
    """Klass för att hantera beräkning i bakgrunden"""
    
    def __init__(self, solver, callback, paramStudy = False):
        """Klasskonstruktor"""
        QThread.__init__(self)
        self.solver = solver
        self.finished.connect(callback)

    def __del__(self):
        self.wait()

    def run(self):
        self.solver.execute()

class MainWindow(QMainWindow):
    """MainWindow-klass som hanterar vårt huvudfönster"""

    def __init__(self):
        """Constructor"""
        
        # --- Init UI
        super(QMainWindow, self).__init__()

        self.app = app
        self.ui = loadUi('mainwindow.ui', self)

        self.components = {
            "triggered": {
            "action_new",
            "action_open",
            "action_save",
            "action_save_as",
            "action_exit",
            "action_execute"
            },
            "clicked": {
                "geometry_button",
                "mesh_button",
                "nodal_values_button",
                "element_values_button"
            },
            "textfields": {
                "outer_width",
                "outer_height",
                "inner_width",
                "inner_height",
                "x_position",
                "y_position",
            }
        }

        for to_connect in ["triggered", "clicked"]:
            for component_name in self.components[to_connect]:
                component = getattr(self.ui, component_name)
                getattr(component, to_connect).connect(getattr(self, f'on_{component_name}'))

        # --- Init model
        self.input_data = hm.InputData()
        self.output_data = hm.OutputData()
        self.solver = hm.Solver(self.input_data, self.output_data)
        self.report = hm.Report(self.input_data, self.output_data)
        self.visualization = None
        self.calc_done = True
        self.init_input_data()
        # -- Show
        self.ui.show()
        self.ui.raise_()
    
    def init_input_data(self):
        self.filename = None
        self.input_data.update({
            "version": 1,
            "outer_width": 1,
            "outer_height": 1,
            "inner_width": 0.1,
            "inner_height": 0.1,
            "x_position": 0.1,
            "y_position": 0.1,
            "t": 1,
            "cond": 1.7,
            "outer_temp": 20,
            "inner_temp": 120,
        })
        self.update_ui()
        
    def on_action_new(self):
        self.init_input_data()

    def on_action_open(self):
        self.filename, _ = QFileDialog.getOpenFileName(self.ui, 
        "Öppna modell", "", "Modell filer (*.json)")

        if self.filename!="":
            self.input_data.load(self.filename)
            self.update_ui()

    def on_action_save(self):
        if self.filename:
            self.update_model()
            self.input_data.save(self.filename)
        else:
            self.on_action_save_as()

    def on_action_save_as(self):
        self.update_model()

        self.filename, _  = QFileDialog.getSaveFileName(self.ui, 
            "Spara modell", "", "Modell filer (*.json)")
    
        if self.filename!="":
            self.input_data.save(self.filename)

    def on_action_exit(self):
        if self.visualization:
            self.visualization.close_all()
        self.ui.close()
        self.app.quit()

    def on_action_execute(self):
        self.ui.setEnabled(False)
        self.update_model()

        self.solverThread = SolverThread(self.solver, self.on_finished_execute)      
        self.calc_done = False
        self.solverThread.start()
    
    def on_finished_execute(self):
        self.visualization = hm.Visualisation(self.input_data, self.output_data)
        self.ui.report_field.setPlainText(str(self.report)) 
        self.calc_done = True
        self.ui.setEnabled(True)
        
    def on_geometry_button(self):
        if self.visualization:
            self.visualization.show_geometry()

    def on_mesh_button(self):
        if self.visualization:
            self.visualization.show_mesh()

    def on_nodal_values_button(self):
        if self.visualization:
            self.visualization.show_nodal_values()

    def on_element_values_button(self):
        if self.visualization:
            self.visualization.show_element_values()

    def update_ui(self):
        for field in self.components["textfields"]:
            ui_field = getattr(self.ui, field)
            ui_field.setText(str(getattr(self.input_data, field)))

    def update_model(self):
        for field in self.components["textfields"]:
            ui_field = getattr(self.ui, field)
            setattr(self.input_data, field,float(ui_field.text()))

if __name__ == "__main__":

    app = QApplication(sys.argv)

    widget = MainWindow()
    widget.show()

    sys.exit(app.exec_())
