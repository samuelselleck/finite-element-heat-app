import numpy as np
import json

import calfem.core as cfc
import calfem.geometry as cfg  # <-- Geometrirutiner
import calfem.mesh as cfm      # <-- Nätgenerering
import calfem.vis_mpl as cfv       # <-- Visualisering
import calfem.utils as cfu     # <-- Blandade rutiner

import pyvtk as vtk
import matplotlib.pyplot as plt


MARKERS = {
    "outer": 1,
    "inner": 2,
}

class Solver(object):
    """Klass för att hantera lösningen av vår beräkningsmodell."""
    def __init__(self, input_data, output_data):
        self.input_data = input_data
        self.output_data = output_data
    
    def execute(self, param_study):

        # -- constants
        cond = np.asarray(self.input_data.conduction)
        outer_temp = self.input_data.outer_temp
        inner_temp = self.input_data.inner_temp
        ep = [self.input_data.thickness]
        
        t_from = self.input_data.t_from
        t_to = self.input_data.t_to
        t_steps = self.input_data.t_steps
        
        space = np.linspace(t_from, t_to, t_steps) if param_study else [t_from]
        
        for index, t_param in enumerate(space):
            geometry = self.input_data.geometry(t_param)
            
            mesh = cfm.GmshMeshGenerator(geometry)
            mesh.el_size_factor = self.input_data.element_max_size/100
            mesh.el_type = 2
            mesh.dofs_per_node = 1
            mesh.return_boundary_elements = True
            
            coords, edof, dofs, bdofs, elementmarkers, boundaryElements = mesh.create()
            
            n = len(coords);
            K = np.zeros([n, n])
            f = np.zeros([n, 1])
            bc_prescr, bc_val =  [], []
            
            # --- Applicera randvillkor/laster
            bc_prescr, bc_val = cfu.applybc(bdofs, bc_prescr, bc_val, MARKERS["outer"] , outer_temp)
            bc_prescr, bc_val = cfu.applybc(bdofs, bc_prescr, bc_val, MARKERS["inner"], inner_temp)
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
            
            flow = [cfc.flw2ts(ex[i], ey[i], D, np.array(t[el-1]).reshape(-1,))[0].tolist()[0] 
                    for i, el, in enumerate(edof)]
    
            max_flow = [np.linalg.norm(flw) for flw in flow]
                    
            element_t = [np.mean(np.array(t[el-1]).reshape(-1,)) for el in edof]
            
            if param_study:
               Solver.export_vtk(param_study, coords, edof, t, flow, max_flow, index)
            else:
                self.output_data.update({   
                    "element_t": element_t,
                    "t": t.tolist(),
                    "r": r,
                    "coords": coords,
                    "edof": edof,
                    "geometry": geometry,
                    "el_type": mesh.el_type,
                    "dofs_per_node": mesh.dofs_per_node,
                    "max_flow": max_flow,
                    "flow": flow,
                })
                
    def export_vtk(filename, coords, edof, t, flow, max_flow, index):
        points = [[*coord, 0] for coord in coords.tolist()]
        polygons = (edof-1).tolist()
        flow_3d = [[*flw, 0] for flw in flow]

        point_data = vtk.PointData(vtk.Scalars(t.tolist(), name="temperature"))
        cell_data = vtk.CellData(vtk.Scalars(max_flow, name="maxflow"), vtk.Vectors(flow_3d, "flow"))
        
        structure = vtk.PolyData(points = points, polygons = polygons)
        
        vtk_data = vtk.VtkData(structure, point_data, cell_data)
        filename = f"{filename}_{index:02d}.vtk"
        vtk_data.tofile(filename, "ascii")
        print(f"saved file: {filename}")
        
        
    
class InputData(dict):
    """Klass för att definiera indata för vår modell."""
    def __init__(self):
        pass
    
    def save(self, filename):
        with open(filename, "w") as ofile:
            json.dump(vars(self), ofile, sort_keys = True, indent = 4)
            
    def load(self, filename):
        with open(filename, "r") as ifile:
            self.update(json.load(ifile))
    
    def update(self, attrs):
        for key, val in attrs.items():
            setattr(self, key, val)  
            
    def __str__(self):
       attr = vars(self)
       aliases = {
           "thickness": "Thickness",
           "x_position": "X-position",
           "y_position": "Y-position",
           "outer_width": "Outer Width",
           "outer_height": "Outer Height",
           "inner_width": "Inner Width",
           "inner_height": "Inner Height",
           "conduction": "Conduction",
       }
       return "\n".join(f'{val}:\n{attr[key]}' for key, val in aliases.items())
   
    def geometry(self, t_param):
        """Skapa en geometri instans baserat på definierade parametrar"""
        
        glob = {"__builtins__": {}}
        loc = {"t": t_param}
        
        try:
            w = eval(self.outer_width, glob, loc)
            h = eval(self.outer_height, glob, loc)
            a = eval(self.inner_width, glob, loc)
            b = eval(self.inner_height, glob, loc)
            x = eval(self.x_position, glob, loc)
            y = eval(self.y_position, glob, loc)
        except Exception:
            return
        
        points = [
            [0, 0], [w, 0], [w, h], [0, h],
            [x, h - y], [x + a, h - y], [x + a, h - y - b], [x, h - y - b]
        ]
        
        boundaries = {
            "outer": [[0, 1], [1, 2], [2, 3], [3, 0]],
            "inner": [[4, 5], [5, 6], [6, 7], [7, 4]]
        }
        
        g = cfg.Geometry()
        
        for point in points:
            g.point(point)
        
        for marker_name, splines in boundaries.items():
            for spline in splines:
                g.spline(spline, marker = MARKERS[marker_name])
         
        g.surface([0,1, 2, 3], [[4, 5, 6, 7]])

        return g


class OutputData:
    """Klass för att lagra resultaten från beräkningen."""
    
    def __init__(self):
        pass
    
    def update(self, attrs):
        for key, val in attrs.items():
            setattr(self, key, val);
        
    def __str__(self):
        attr = vars(self)
        aliases = {
           "t": "Temperatures",
        }
        return "\n".join(f'{val}:\n{attr[key]}' for key, val in aliases.items())
        
class Report:
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
        
        plt.ioff()
        self.geom_fig = None
        self.mesh_fig = None
        self.el_value_fig = None
        self.node_value_fig = None
        
    def geometry(self):
        
        self.geom_fig = cfv.figure(self.geom_fig)
        cfv.clf()            
        cfv.draw_geometry(self.output_data.geometry, title="Geometry")
        return self.geom_fig
    
    def mesh(self):
        self.mesh_fig = cfv.figure(self.mesh_fig)
        
        cfv.clf()
        cfv.draw_mesh(
            self.output_data.coords,
            self.output_data.edof, 
            self.output_data.dofs_per_node,
            self.output_data.el_type,
            title="Mesh"
        )
        
        return self.mesh_fig
        
    def nodal_values(self):
        """Visa geometri visualisering"""

        self.node_value_fig = cfv.figure(self.node_value_fig)
        
        cfv.clf()            
        cfv.draw_nodal_values(
            self.output_data.t,
            self.output_data.coords,
            self.output_data.edof,
            12, "Node Values",
            self.output_data.dofs_per_node,
            self.output_data.el_type,
            draw_elements=False
        )
        
        return self.node_value_fig
        
    def element_values(self):
        self.el_value_fig = cfv.figure(self.el_value_fig)
        
        cfv.clf()
        cfv.draw_element_values(
            self.output_data.element_t,
            self.output_data.coords,
            self.output_data.edof,
            self.output_data.dofs_per_node,
            self.output_data.el_type,
            title="Element Values"
        )
        
        return self.el_value_fig
        

