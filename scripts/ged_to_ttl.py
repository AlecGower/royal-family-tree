
from royal_family_tree.royal_graph import RoyalsGraph

GED_FILE_PATH = 'data/Queen_Eliz_II.ged'

if __name__ == "__main__":
    # Create graph
    g = RoyalsGraph(GED_FILE_PATH)
    g.load_ged_data()

    # Serialize the graph to Turtle format
    g.serialize(destination='data/royals.ttl', format='turtle')
    print("Graph serialized to data/royals.ttl")
