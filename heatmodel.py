import numpy as np
import json
import math

import calfem.core as cfc
import calfem.geometry as cfg  # <-- Geometrirutiner
import calfem.mesh as cfm      # <-- Nätgenerering
import calfem.vis_mpl as cfv       # <-- Visualisering
import calfem.utils as cfu     # <-- Blandade rutiner



class Solver(object):
    """Klass för att hantera lösningen av vår beräkningsmodell."""
    def __init__(self):
        pass
    
    def execute(self, input_data):

        # --- Överför modell variabler till lokala referenser
        
        cond = np.asarray(input_data.cond)
        outer_temp = input_data.outer_temp
        inner_temp = input_data.inner_temp
        ep = [input_data.t]
        geometry = input_data.geometry()
        
        mesh = cfm.GmshMeshGenerator(geometry)
        mesh.el_size_factor = 0.05     # <-- Anger max area för element
        mesh.el_type = 2
        mesh.dofs_per_node = 1
        mesh.return_boundary_elements = True
        
        coords, edof, dofs, bdofs, elementmarkers, boundaryElements = mesh.create()
        
        n = len(coords);
        K = np.zeros([n, n])
        f = np.zeros([n, 1])
        bc_prescr, bc_val =  [], []
        
        # --- Applicera randvillkor/laster
        bc_prescr, bc_val = cfu.applybc(bdofs, bc_prescr, bc_val, 1 , outer_temp)
        bc_prescr, bc_val = cfu.applybc(bdofs, bc_prescr, bc_val, 2, inner_temp)
        bc_prescr = bc_prescr.astype(int)
        
        ex, ey = cfc.coordxtr(edof, coords, np.arange(1, n + 1)[..., None])
        
        D = np.array([
            [cond, 0],
            [0, cond],
        ]);
        
        for elx, ely, eltopo, in zip(ex, ey, edof):          
            Ke = cfc.flw2te(elx, ely, ep, D)
            cfc.assem(eltopo, K, Ke)
        
        t, r = cfc.solveq(K, f, bc_prescr, bc_val)
        
        max_flow = max(
            np.linalg.norm(
                cfc.flw2ts(ex[i], ey[i], D, np.array(t[el-1]).reshape(-1,))[0])
            for i, el, in enumerate(edof)
        )
        
        return OutputData({
            
            "t": t.tolist(),
            "r": r,
            "coords": coords,
            "edof": edof,
            "geometry": geometry,
            "el_type": mesh.el_type,
            "dofs_per_node": mesh.dofs_per_node,
            "max_flow": max_flow,
        })

class InputData(object):
    """Klass för att definiera indata för vår modell."""
    def __init__(self):
        pass
    
    def save(self, filename):
        with open(filename, "w") as ofile:
            json.dump(vars(self), ofile, sort_keys = True, indent = 4)
            
    def load(self, filename):
        with open(filename, "r") as ifile:
            for key, val in json.load(ifile).items():
                setattr(self, key, val)
                
    def __str__(self):
       attr = vars(self)
       aliases = {
           "t": "Thickness",
           "x": "x",
           "y": "y",
           "w": "w",
           "h": "h",
           "a": "a",
           "b": "b",
           "cond": "Conduction",
       }
       return "\n".join(f'{val}:\n{attr[key]}' for key, val in aliases.items())
   
    def geometry(self):
        """Skapa en geometri instans baserat på definierade parametrar"""

        w = self.w
        h = self.h
        a = self.a
        b = self.b
        x = self.x
        y = self.y
        
        g = cfg.Geometry()
        
        # --- Yttre vägg
         
        g.point([0, 0])
        g.point([w, 0])
        g.point([w, h])
        g.point([0, h])

        g.spline([0, 1], marker=1)            
        g.spline([1, 2], marker=1)           
        g.spline([2, 3], marker=1)
        g.spline([3, 0], marker=1)
        
         # --- Inre vägg
         
        g.point([x, h - y])
        g.point([x + a, h - y])
        g.point([x + a, h - y - b])
        g.point([x, h - y - b])

        g.spline([4, 5], marker=2)            
        g.spline([5, 6], marker=2)           
        g.spline([6, 7], marker=2)
        g.spline([7, 4], marker=2)
        
        g.surface([0,1, 2, 3], [[4, 5, 6, 7]])

        return g


class OutputData(object):
    """Klass för att lagra resultaten från beräkningen."""
    def __init__(self, attrs):
        for key, val in attrs.items():
            setattr(self, key, val);
        
    def __str__(self):
        attr = vars(self)
        aliases = {
           "t": "Temperatures",
        }
        return "\n".join(f'{val}:\n{attr[key]}' for key, val in aliases.items())
        
class Report(object):
    """Klass för presentation av indata och utdata i rapportform."""
    def __init__(self, input_data, output_data):
        self.input_data = input_data
        self.output_data = output_data


    def __str__(self):
        return f'''
-------------- Model input ----------------------------------
{self.input_data}
-------------- Model output ---------------------------------
{self.output_data}
        '''
        
class Visualisation(object):
    def __init__(self, input_data, output_data):
        self.input_data = input_data
        self.output_data = output_data

    def show(self):

        geometry = self.output_data.geometry
        t = self.output_data.t
        max_flow = self.output_data.max_flow
        coords = self.output_data.coords
        edof = self.output_data.edof
        dofs_per_node = self.output_data.dofs_per_node
        el_type = self.output_data.el_type
        
        cfv.figure()
        cfv.draw_geometry(geometry, title="Geometry")
        cfv.figure()
        cfv.draw_mesh(coords, edof, dofs_per_node, el_type, title="Mesh")
        cfv.figure()
        cfv.draw_nodal_values(t, coords, edof, 12, "Temp", dofs_per_node, el_type, draw_elements=False)
        cfv.figure()
        cfv.draw_element_values(max_flow, coords, edof, dofs_per_node, el_type, title="Max Flow")

    def wait(self):
        """Denna metod ser till att fönstren hålls uppdaterade och kommer att returnera
        När sista fönstret stängs"""

        cfv.show_and_wait()
        

