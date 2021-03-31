import heatmodel as hm
import matplotlib.pyplot as plt
import numpy as np

if __name__ == "__main__":
    
    input_data = hm.InputData()
    input_data.load("heat_example.json") #Setup
    
    solver = hm.Solver()
    edge_margin = 0.01;
    
    y_space = np.linspace(edge_margin, input_data.h - input_data.b - edge_margin)
    max_flow = []
    for y in y_space:
        input_data.y = y;
        output_data = solver.execute(input_data)
        max_flow.append(output_data.max_flow)
        
    plt.plot(y_space, max_flow)
    plt.xlabel("Y-position")
    plt.ylabel("Maximum Flow")
    
