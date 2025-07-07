from gedcom.element.individual import IndividualElement
from gedcom.parser import Parser

from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDF, RDFS, FOAF, XSD

REL = Namespace("http://purl.org/vocab/relationship/")
ROYALS = Namespace("http://example.org/royals/")


class RoyalsGraph(Graph):
    """A custom graph class for royals."""

    def __init__(self):
        super().__init__()
        self.gender_lookup = {'M': 'male', 'F': 'female'}

    def add_individual(self, ind):
        """Add an individual to the graph."""
        id = ind.get_pointer().strip('@')
        uri = ROYALS[id]

        self.add((uri, RDF.type, FOAF.Person))
        self.add((uri, FOAF.name, Literal(ind.get_name()[
                 0] + " " + ind.get_name()[1], datatype=XSD.string)))
        self.add((uri, FOAF.givenName, Literal(
            ind.get_name()[0], datatype=XSD.string)))
        self.add((uri, FOAF.familyName, Literal(
            ind.get_name()[1], datatype=XSD.string)))
        self.add((uri, FOAF.gender, Literal(self.gender_lookup.get(
            element.get_gender(), 'unknown'), datatype=XSD.string)))


if __name__ == "__main__":

    file_path = 'data/Queen_Eliz_II.ged'

    gedcom_parser = Parser()
    gedcom_parser.parse_file(file_path, strict=False)

    elements = gedcom_parser.get_root_child_elements()

    print(
        f"There are {sum(1 for i in elements if isinstance(i, IndividualElement))} Individuals in the file.")

    # Create graph
    g = RoyalsGraph()
    g.bind("rel", REL)
    g.bind("royals", ROYALS)

    # Iterate through all root child elements
    for element in elements:
        # Is the `element` an actual `IndividualElement`? (Allows usage of extra functions such as `surname_match` and `get_name`.)
        if isinstance(element, IndividualElement):
            g.add_individual(element)
            element_uri = ROYALS[element.get_pointer().strip('@')]

            # Get parents of the individual
            for parent in gedcom_parser.get_parents(element):
                if isinstance(parent, IndividualElement):
                    parent_id = parent.get_pointer().strip('@')
                    parent_uri = ROYALS[parent_id]
                    g.add((parent_uri, REL.parentOf, URIRef(
                        element_uri)))

            # Get spouses of the individual
            for spouse in gedcom_parser.get_spouses(element):
                if isinstance(spouse, IndividualElement):
                    spouse_id = spouse.get_pointer().strip('@')
                    spouse_uri = ROYALS[spouse_id]
                    g.add((spouse_uri, REL.spouseOf, URIRef(
                        element_uri)))

            # Get children of the individual
            for child in gedcom_parser.get_children(element):
                if isinstance(child, IndividualElement):
                    child_id = child.get_pointer().strip('@')
                    child_uri = ROYALS[child_id]
                    g.add(
                        (URIRef(element_uri), REL.parentOf, child_uri))
                    g.add((child_uri, REL.childOf, URIRef(
                        element_uri)))

    # Serialize the graph to Turtle format
    g.serialize(destination='data/royals.ttl', format='turtle')
    print("Graph serialized to data/royals.ttl")
