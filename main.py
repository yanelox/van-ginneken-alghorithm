import argparse
from source.json import read_json
from source import vanginneken
import os
import matplotlib.pyplot as plt
import networkx as nx

def main():
    parser = argparse.ArgumentParser(description="Realisation of Van Ginneken alghorithm")
    parser.add_argument("input_files", nargs=2, help="Technology file, Trace tree file")
    parser.add_argument("--save_graph", action="store_true", help="Save result graph to graph.png")
    parser.add_argument("--output_file", help="Output file name", default=None, required=False)

    args = parser.parse_args()

    params = read_json(args.input_files[0])
    trace_tree = read_json(args.input_files[1])

    test_name = os.path.basename(args.input_files[1])[:-5]

    module = vanginneken.Module(params, trace_tree)
    solution = module.start()
    solution.renumber_nodes_and_edges()

    outputfile = f"{test_name}_out.json" if not args.output_file else args.output_file

    solution.dump_to_json(outputfile)

    if args.save_graph:
        G = nx.Graph()
        edges = [(edge.vertices[0], edge.vertices[1]) for edge in solution.edges]
        G.add_edges_from(edges)
        pos = nx.spring_layout(G)

        labels = {node.id : f"{node.id}{node.type}:{node.name}\n{node.x, node.y}" for node in solution.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, font_color='black', font_size=5)

        nx.draw(G, pos, with_labels=False, node_color='skyblue', node_size=1000, edge_color='gray')
        plt.savefig("graph.png", dpi=300)

if __name__ == "__main__":
    main()
