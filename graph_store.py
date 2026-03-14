import networkx as nx

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_triplets(self, triplets: list):
        for triplet in triplets:
            if len(triplet) == 3:
                u, r, v = triplet
                self.graph.add_node(u)
                self.graph.add_node(v)
                self.graph.add_edge(u, v, label=r)

    def search_graph(self, query_term: str) -> list:
        if self.graph.number_of_nodes() == 0:
            return ["Graph is currently empty."]
        
        results = set()
        
        # Heavily expanded ignore list to prevent false positive graph hits!
        ignore_words = {
            "what", "give", "tell", "show", "this", "that", "with", "about", "some", "find", "all", "have", "been", "the", "and",
            "patient", "patients", "history", "details", "info", "information", "procedure", "procedures", "encounter", "encounters",
            "any", "name", "named", "occurred", "at", "in", "of", "get", "fetch", "search", "me"
        }
        
        clean_query = query_term.replace("?", "").replace(",", "").replace(".", "").replace('"', '').replace("'", "")
        keywords = [w.lower() for w in clean_query.split() if len(w) > 2 and w.lower() not in ignore_words]
        
        # If the user only typed generic words, we MUST force a tool call
        if not keywords:
            return ["No matching graph context. YOU MUST USE A TOOL."]
            
        for u, v, data in self.graph.edges(data=True):
            u_str = str(u).lower()
            v_str = str(v).lower()
            edge_label = str(data.get('label', '')).lower()
            
            if any(kw in u_str or kw in v_str or kw in edge_label for kw in keywords):
                results.add(f"({u}) -[{data['label']}]-> ({v})")
                
        return list(results)[:50] if results else ["No matching graph context. YOU MUST USE A TOOL."]

    def get_vis_data(self):
        nodes = [{"id": str(n), "label": str(n)} for n in self.graph.nodes()]
        edges = [{"from": str(u), "to": str(v), "label": d['label']} for u, v, d in self.graph.edges(data=True)]
        return {"nodes": nodes, "edges": edges}

    def get_graph_stats(self):
        return {"nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges()}