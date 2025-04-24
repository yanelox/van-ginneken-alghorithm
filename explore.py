import argparse
from source.json import read_json
from source import vanginneken
import time
import matplotlib.pyplot as plt
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Explore dependence of RAT and algorithm execution time on len of wire")
    parser.add_argument("tech_file", type=str, help="Technology file")
    start_len = 10
    default_max_len = 10
    parser.add_argument("max_len", type=int, help=f"Maximum len of wire (>10, otherwise ignored and set to {default_max_len})")

    args = parser.parse_args()

    params = read_json(args.tech_file)
    trace_tree = read_json("help/example_simple.json")

    max_len = args.max_len if args.max_len > 10 else default_max_len

    times = []
    Q = []
    lengths = [len for len in range(start_len, max_len + 1)]

    for len in lengths:
        trace_tree["node"][1]["y"] = len
        trace_tree["edge"][0]["segments"][0][1] = len

        module = vanginneken.Module(params, trace_tree)

        start_time = time.time()
        solution = module.start()
        solution.renumber_nodes_and_edges()
        end_time = time.time()

        times.append(end_time - start_time)
        Q.append(solution.Q)

    figsize = (12, 10)
    plt.figure(figsize=figsize)
    plt.plot(lengths, times, linestyle='-', marker='o', markersize=2, markerfacecolor='red', markeredgecolor='red')
    plt.title("Algorithm execution time (in seconds) on length")
    plt.grid(True)
    plt.savefig("times.png", dpi=300)

    plt.figure(figsize=figsize)
    plt.plot(lengths, Q, linestyle='-', marker='o', markersize=2, markerfacecolor='red', markeredgecolor='red')
    plt.title("RAT on length")
    plt.grid(True)
    plt.savefig("Q.png", dpi=300)

if __name__ == "__main__":
    main()
