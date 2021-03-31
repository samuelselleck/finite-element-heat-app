import numpy as np
import calfem.core as cfc
import json

class Solver(object):
    """Klass för att hantera lösningen av vår beräkningsmodell."""
    def __init__(self):
        pass
    
    def execute(self, input_data):

        # --- Överför modell variabler till lokala referenser
        
        edof = np.asarray(input_data.edof)
        conds = np.asarray(input_data.conds)
        coord = np.asarray(input_data.coords)
        loads = input_data.loads
        bcs = input_data.bcs
        ep = [input_data.t]
        
        n = len(coord);
        K = np.zeros([n, n])
        f = np.zeros([n, 1])
        bc_prescr = np.asarray([ind for ind, _ in bcs])
        bc_val = np.asarray([val for _, val in bcs])
        
        for index, load in loads:
            f[index - 1] = load;
            
        ex, ey = cfc.coordxtr(edof, coord, np.arange(1, n + 1)[..., None])
        
        
        
        for elx, ely, eltopo, cond in zip(ex, ey, edof, conds):
            D = np.array([
                [cond, 0],
                [0, cond],
            ]);
            Ke = cfc.flw2te(elx, ely, ep, D)
            cfc.assem(eltopo, K, Ke)
        
        t, _ = cfc.solveq(K, f, bc_prescr, bc_val)
        
        return OutputData({
            
            "t": t.tolist()
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
           "coords": "Coordinates",
           "edof": "Topology",
           "bcs": "Boundary Conditions",
           "conds": "Conduction",
           "loads": "Thermal Loads",
       }
       return "\n".join(f'{val}:\n{attr[key]}' for key, val in aliases.items())


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
        

