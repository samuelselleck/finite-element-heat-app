
import heatmodel as hm

if __name__ == "__main__":
    
    input_data = hm.InputData()
    input_data.load("heat_example.json")
    solver = hm.Solver()
    output_data = solver.execute(input_data)

    report = hm.Report(input_data, output_data)
    print(report)
    
    vis = hm.Visualisation(input_data, output_data); vis.show(); vis.wait()
