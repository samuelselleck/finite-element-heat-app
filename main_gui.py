import sys

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QDialog, QWidget, QMainWindow, QFileDialog, QMessageBox, QVBoxLayout
from PyQt5.uic import loadUi

import heatmodel as hm
import calfem.ui as cfui
import calfem.vis_mpl as cfv 

class SolverThread(QThread):
    """Klass för att hantera beräkning i bakgrunden"""
    
    def __init__(self, solver, callback, param_study = ""):
        """Klasskonstruktor"""
        QThread.__init__(self)
        self.solver = solver
        self.param_study = param_study
        self.finished.connect(callback)

    def __del__(self):
        self.wait()

    def run(self):
        self.solver.execute(self.param_study)

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
                "parameter_study_button",
                "save_tool_button",
                "open_tool_button",
                "execute_tool_button"
            },
            "textfields": {
                "outer_width",
                "outer_height",
                "inner_width",
                "inner_height",
                "x_position",
                "y_position",
            },
            "numfields": {
                "t_from",
                "t_to",
                "t_steps",
                "element_max_size"
            }
        }

        # --- Bind controls to methods
        for to_connect in ["triggered", "clicked"]:
            for component_name in self.components[to_connect]:
                component = getattr(self.ui, component_name)
                getattr(component, to_connect).connect(getattr(self, f'on_{component_name}'))
        
        # --- Bind controls to update geometry
        for component_name in self.components["textfields"]:
            component = getattr(self.ui, component_name)
            component.returnPressed.connect(self.update_geometry)
            
        self.ui.t_from.valueChanged.connect(self.update_geometry)
        
        # --- Init model
        self.input_data = hm.InputData()
        self.output_data = hm.OutputData()
        self.solver = hm.Solver(self.input_data, self.output_data)
        self.report = hm.Report(self.input_data, self.output_data)
        self.visualization = hm.Visualisation(self.input_data, self.output_data)
        self.calc_done = True
        self.init_input_data()
        
        # --- Show
        self.ui.show()
        self.ui.raise_()
        self.update_geometry()
    
    def init_input_data(self):
        self.filename = None
        self.input_data.reset()
        self.update_ui(self.input_data)
    
    def on_save_tool_button(self):
        self.on_action_save()
    
    def on_open_tool_button(self):
        self.on_action_open()
    
    def on_execute_tool_button(self):
        self.on_action_execute()
    
    def on_action_new(self):
        self.init_input_data()

    def on_action_open(self):
        temp_name, _ = QFileDialog.getOpenFileName(self.ui, 
        "Öppna modell", "", "Modell filer (*.json)")
        if temp_name != "":
            self.filename = temp_name
            self.input_data.load(self.filename)
            self.update_ui(self.input_data)
            self.update_geometry()

    def on_action_save(self):
        if self.filename:
            self.update_model(self.input_data)
            self.input_data.save(self.filename)
        else:
            self.on_action_save_as()

    def on_action_save_as(self):
        self.update_model(self.input_data)

        self.filename, _  = QFileDialog.getSaveFileName(self.ui, 
            "Spara modell", "", "Modell filer (*.json)")
    
        if self.filename!="":
            self.input_data.save(self.filename)

    def on_action_exit(self):
        self.ui.close()
        self.app.quit()

    def on_action_execute(self):
        self.ui.setEnabled(False)
        self.update_model(self.input_data)

        self.solverThread = SolverThread(self.solver, self.on_finished_execute)      
        self.calc_done = False
        self.solverThread.start()
    
    def on_finished_execute(self):
        self.ui.report_field.setPlainText(str(self.report)) 
        
        figure_names = ["geometry", "mesh", "nodal_values", "element_values"]
        for name in figure_names:
            self.update_figure(name)

        self.calc_done = True
        self.ui.setEnabled(True)
    
    def on_parameter_study_button(self):
        if self.filename:
            self.on_action_save()
            self.ui.setEnabled(False)
            self.update_model(self.input_data)
            
            self.solverThread = SolverThread(self.solver, self.on_finished_param_study, self.filename.split(".")[0])      
            self.calc_done = False
            self.solverThread.start()
        else:
             msg = QMessageBox(
                QMessageBox.Information,
                "No save file.",
                "A project save file needs to exist to perform a parameter study."
             )
             msg.exec_()
        
        
    def on_finished_param_study(self):
        self.calc_done = True
        self.ui.setEnabled(True)
        msg = QMessageBox(
            QMessageBox.Information,
            "Parameter Study Done",
            "The parameter study is finished, vtk files exported."
        )
        msg.exec_()

    def update_ui(self, model):
        for field in self.components["textfields"]:
            ui_field = getattr(self.ui, field)
            ui_field.setText(getattr(model, field))
        for field in self.components["numfields"]:
            ui_field = getattr(self.ui, field)
            ui_field.setValue(int(getattr(model, field)))

    def update_model(self, model):
        for field in self.components["textfields"]:
            ui_field = getattr(self.ui, field)
            setattr(model, field,ui_field.text())
        for field in self.components["numfields"]:
            ui_field = getattr(self.ui, field)
            setattr(model, field, ui_field.value())
    
    def update_figure(self, name):
        fig = getattr(self.visualization, name)()
        widget = cfv.figure_widget(fig)
        box = getattr(self.ui, f"{name}_box")
        box.takeAt(0).widget().deleteLater()  
        box.addWidget(widget)
    
    def update_geometry(self):
        cfv.close_all()
        input_data = hm.InputData()
        self.update_model(input_data)
        self.visualization.output_data.geometry = input_data.geometry(input_data.t_from)
        self.update_figure("geometry")
        
        
if __name__ == "__main__":

    app = QApplication(sys.argv)

    widget = MainWindow()
    widget.show()

    sys.exit(app.exec_())
