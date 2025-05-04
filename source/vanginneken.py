import copy
import json

debug = False

class Node:
    id : int
    x : int
    y : int
    type : str
    name : str
    children : list[int]
    C : float
    Q : float

    def __init__(self, _id, x, y, _type, name, children, C, Q):
        self.id = _id
        self.x = x
        self.y = y
        self.type = _type
        self.name = name
        self.children = children
        self.C = C
        self.Q = Q

    def dump_dict (self):
        res = {"id" : self.id, "x" : self.x, "y" : self.y, "type" : self.type, "name" : self.name}
        if self.C:
            res["capacitance"] = self.C

        if self.Q:
            res["rat"] = self.Q

        global debug
        if debug:
            res["children"] = self.children

        return res

    def __str__(self):
        return str(self.dump_dict())

def new_Node_from_dict (node_dict):
    _type = node_dict['type']
    C = 0 if _type != 't' else node_dict['capacitance']
    Q = 0 if _type != 't' else node_dict['rat']
    return Node (_id=node_dict['id'], x=node_dict['x'], y=node_dict['y'], _type=_type,
                   name=node_dict['name'], children=[], C=C, Q=Q)
class Edge:
    id : int
    vertices : list[int]
    segments : list[list[int]]

    def __init__(self, _id, vertices, segments):
        self.id = _id
        self.vertices = vertices
        self.segments = segments

    def dump_dict(self):
        return {"id" : self.id, "vertices" : self.vertices, "segments" : self.segments}

    def __str__(self):
        return str(self.dump_dict())

    def len(self):
        res = 0.0
        for i in range(len(self.segments)-1):
            res += abs(self.segments[i + 1][0] + self.segments[i + 1][1]
                         - self.segments[i][0] - self.segments[i][1])

        return res

def new_Edge_from_dict (edge_dict):
    return Edge(_id=edge_dict['id'], vertices=edge_dict['vertices'], segments=edge_dict['segments'])

class Candidate:
    nodes : list[Node]
    edges : list[Edge]
    C : float
    Q : float
    top_edge : None | Edge

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.C = 0
        self.Q = 0
        self.top_edge = None

    def _dump(self):
        nodes = [node.dump_dict() for node in self.nodes]

        edges = [edge.dump_dict() for edge in self.edges]

        res = {"node" : nodes, "edge" : edges}
        if self.top_edge:
            res["top_edge"] = {"id" : self.top_edge.id, "vertices" : self.top_edge.vertices, "segments" : self.top_edge.segments}

        global debug
        if debug:
            res["C"] = self.C
            res["Q"] = self.Q

        return res

    def __str__(self):
        return json.dumps(self._dump(), indent=4)

    def dump_to_json (self, filename : str):
        with open(filename, 'w') as json_file:
            json.dump(self._dump(), json_file, indent=4)

    def renumber_nodes_and_edges (self):
        new_nodes_number = {}
        for i in range(len(self.nodes)):
            new_nodes_number[self.nodes[i].id] = i
            self.nodes[i].id = i

        for i in range(len(self.nodes)):
            self.nodes[i].children = [new_nodes_number[id] for id in self.nodes[i].children]

        for i in range(len(self.edges)):
            self.edges[i].id = i
            self.edges[i].vertices = [new_nodes_number[old_id] for old_id in self.edges[i].vertices]


class Module:
    D_intr : float
    C_buf : float
    R_buf : float
    Unit_r : float
    Unit_c : float
    nodes : list[Node]
    edges : list[Edge]

    def generator(self, start=1):
        while True:
            yield start
            start += 1

    def __init__(self, params, _trace_tree, _debug = False):
        global debug
        debug = _debug

        trace_tree = copy.deepcopy(_trace_tree)
        self.D_intr = params['module'][0]['input'][0]['intrinsic_delay']
        self.C_buf  = params['module'][0]['input'][0]['C']
        self.R_buf  = params['module'][0]['input'][0]['R']

        self.Unit_r = params['technology']['unit_wire_resistance']
        self.Unit_c = params['technology']['unit_wire_capacitance']

        self.nodes = []
        for node_dict in trace_tree['node']:
            self.nodes.append(new_Node_from_dict(node_dict))

        self.edges = []
        for edge_dict in trace_tree['edge']:
            self.edges.append(new_Edge_from_dict(edge_dict))

        for edge in self.edges:
            parent = edge.vertices[0]
            child  = edge.vertices[1]
            self.nodes[parent].children.append(child)

        self.node_id_gen = self.generator(self.nodes[-1].id + 1)
        self.edge_id_gen = self.generator(self.edges[-1].id + 1)

    def get_new_node_id (self):
        return next(self.node_id_gen)

    def get_new_edge_id (self):
        return next(self.edge_id_gen)

    def found_edge (self, child : Node, parent : Node, edge_list : None | list[Edge] = None):
        if not edge_list:
            edge_list = self.edges

        for edge in edge_list:
            if (edge.vertices[0] == parent.id and edge.vertices[1] == child.id):
                return edge

        raise RuntimeError

    def get_buf_D (self, C_load : float):
        return self.D_intr + self.R_buf * C_load

    def get_edge_C (self, edge : Edge):
        return self.Unit_c * edge.len()

    def get_edge_D (self, edge : Edge, C_load : float):
        return 0.5 * self.Unit_r * self.Unit_c * edge.len() ** 2 + self.Unit_r * edge.len() * C_load

    def compare_soluitons (self, sol1 : Candidate, sol2 : Candidate):
        # 0 if noone is inferior to noone
        # 1 if sol2 is inferior to sol1 (throw sol2)
        # 2 if sol1 is inferior to sol2 (throw sol1)
        if (sol1.C <= sol2.C and sol1.Q >= sol2.Q):
            return 1
        if (sol2.C <= sol1.C and sol2.Q >= sol1.Q):
            return 2

        return 0

    def increase_top_edge (self, sol : Candidate, x : int, y : int):
        if sol.top_edge:
            old_top_edge = copy.deepcopy(sol.top_edge)

            x1 = sol.top_edge.segments[-2][0]
            y1 = sol.top_edge.segments[-2][1]

            x2 = sol.top_edge.segments[-1][0]
            y2 = sol.top_edge.segments[-1][1]

            if ((x1 == x2 and x2 == x) or (y1 == y2 and y2 == y)):
                sol.top_edge.segments[-1][0] = x
                sol.top_edge.segments[-1][1] = y
            elif ((x1 == x2 and y2 == y) or (y1 == y2 and x2 == x)):
                sol.top_edge.segments.append([x, y])
            else:
                raise RuntimeError

            C_load = sol.C - self.get_edge_C(old_top_edge)
            sol.C += self.get_edge_C(sol.top_edge) - self.get_edge_C(old_top_edge)
            sol.Q += self.get_edge_D(old_top_edge, C_load) - self.get_edge_D(sol.top_edge, C_load)

        else:
            top_node_x = sol.nodes[-1].x
            top_node_y = sol.nodes[-1].y
            top_node_id = sol.nodes[-1].id

            if (top_node_x != x and top_node_y != y):
                raise RuntimeError

            new_edge = Edge(_id=self.get_new_edge_id(), vertices=[top_node_id, -1],
                               segments=[[top_node_x, top_node_y], [x, y]])

            sol.top_edge = new_edge
            C_load = sol.C
            sol.C += self.get_edge_C(sol.top_edge)
            sol.Q -= self.get_edge_D(sol.top_edge, C_load)

    def maybe_add_new_sol (self, solutions : list[Candidate], new_sol : Candidate):
        res_solutions = []

        if not solutions:
            return [new_sol]

        for sol in solutions:
            compare_res = self.compare_soluitons(sol, new_sol)
            if compare_res == 1:
                return solutions
            if compare_res == 0:
                res_solutions.append(sol)

        res_solutions.append(new_sol)

        return res_solutions

    def try_insert_boof (self, sol : Candidate, x : int, y : int):
        res_sol = Candidate()

        if sol.top_edge:
            res_sol = copy.deepcopy(sol)
            top_node = sol.nodes[-1]
            new_boof = Node(_id=self.get_new_node_id(), x=x, y=y, _type="b", name="buf1x",
                               children=[top_node.id], C=None, Q=None)

            new_edge = copy.deepcopy(res_sol.top_edge)
            new_edge.vertices[1] = new_edge.vertices[0]
            new_edge.vertices[0] = new_boof.id
            new_edge.segments.reverse()

            res_sol.nodes.append(new_boof)
            res_sol.edges.append(new_edge)
            res_sol.top_edge = None
            res_sol.C = self.C_buf
            res_sol.Q -= self.get_buf_D(sol.C)

            self.increase_top_edge(res_sol, x, y)
        else:
            raise RuntimeError

        return res_sol

    def step_through_edge (self, child : Node, parent : Node, child_solutions : list[Candidate]):
        edge = self.found_edge(child, parent)
        edge.vertices.reverse()
        edge.segments.reverse()

        res_solutions = child_solutions

        for seg_index in range(len(edge.segments) - 1):
            start_x = cur_x = edge.segments[seg_index][0]
            start_y = cur_y = edge.segments[seg_index][1]

            end_x = edge.segments[seg_index + 1][0]
            end_y = edge.segments[seg_index + 1][1]

            left_x = min(start_x, end_x)
            right_x = max(start_x, end_x)

            left_y = min(start_y, end_y)
            right_y = max(start_y, end_y)

            x_step = 0
            y_step = 0

            if start_x == end_x:
                y_step = 1 if end_y >  start_y else -1
            elif start_y == end_y:
                x_step = 1 if end_x >  start_x else -1
            else:
                raise RuntimeError

            while True:
                for new_sol in res_solutions:
                    self.increase_top_edge(new_sol, cur_x, cur_y)

                new_solutions_with_buf = [self.try_insert_boof(new_sol, cur_x, cur_y) for new_sol in res_solutions]
                dummy = 0
                for new_sol_with_buf in new_solutions_with_buf:
                    res_solutions = self.maybe_add_new_sol(res_solutions, new_sol_with_buf)
                dummy = 1
                cur_x += x_step
                cur_y += y_step

                if not (((left_x < cur_x < right_x) and x_step != 0) or
                        ((left_y < cur_y < right_y) and y_step != 0)):
                    break

        last_x = edge.segments[-1][0]
        last_y = edge.segments[-1][1]
        for new_sol in res_solutions:
            self.increase_top_edge(new_sol, last_x, last_y)

        return res_solutions

    def insert_top_node_to_unfinished_sol (self, sol : Candidate, node : Node):
        res_sol = Candidate()
        if sol.top_edge:
            res_sol = copy.deepcopy(sol)

            old_top_node = sol.nodes[-1]

            new_node = copy.deepcopy(node)
            new_node.children = [old_top_node.id]

            new_edge = copy.deepcopy(sol.top_edge)
            new_edge.vertices[1] = new_edge.vertices[0]
            new_edge.vertices[0] = new_node.id
            new_edge.segments.reverse()

            res_sol.nodes.append(new_node)
            res_sol.edges.append(new_edge)
            # may be we should update C and Q here, but it's only affected on root buffer
            res_sol.top_edge = None

            if node.type == "b":
                D_buf = self.D_intr + self.R_buf * res_sol.C
                res_sol.Q -= D_buf
                res_sol.C = self.C_buf

        else:
            raise RuntimeError

        return res_sol

    def merge_solutions (self, solutions_1 : list[Candidate], solutions_2 : list[Candidate]):
        res_solutions = []

        if not solutions_1:
            return solutions_2

        if not solutions_2:
            return solutions_1

        for sol1 in solutions_1:
            for sol2 in solutions_2:
                new_C = sol1.C + sol2.C
                new_Q = min(sol1.Q, sol2.Q)

                new_top_node = copy.deepcopy(sol1.nodes[-1])
                new_top_node.children += sol2.nodes[-1].children

                merged_sol = Candidate()
                merged_sol.nodes = sol1.nodes[:-1] + sol2.nodes[:-1]
                merged_sol.nodes.append(new_top_node)

                merged_sol.edges = sol1.edges + sol2.edges
                merged_sol.C = new_C
                merged_sol.Q = new_Q

                res_solutions.append(merged_sol)

        return res_solutions

    def step (self, node : Node):
        if node.type == 't':
            result = Candidate()
            result.nodes = [node]
            result.C = node.C
            result.Q = node.Q
            return [result]

        solutions = []

        for child_id in node.children:
            child_solutions = self.step(self.nodes[child_id])
            solutions_without_top_node = self.step_through_edge(child=self.nodes[child_id], parent=node, child_solutions=child_solutions)
            child_solutions = [self.insert_top_node_to_unfinished_sol(sol, node) for sol in solutions_without_top_node]
            solutions = self.merge_solutions(solutions, child_solutions)

        res_solutions = []

        for sol in solutions:
            res_solutions = self.maybe_add_new_sol(res_solutions, sol)

        return res_solutions


    def start (self):
        top_node = None

        for node in self.nodes:
            if node.type == "b":
                top_node = node

        if not top_node:
            raise RuntimeError

        all_solutions = self.step(top_node)

        max_Q = float("-inf")
        res = None
        for sol in all_solutions:
            if sol.Q > max_Q:
                max_Q = sol.Q
                res = sol

        return res
