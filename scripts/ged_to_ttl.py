import sys

from gedcom.element.individual import IndividualElement
from gedcom.parser import Parser

from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import RDF, RDFS, FOAF, XSD

from pycountry import countries, historic_countries, subdivisions

from tqdm.auto import tqdm

from urllib.error import HTTPError

REL = Namespace("http://purl.org/vocab/relationship/")
ROYALS = Namespace("http://example.org/royals/")
SCHEMA = Namespace("http://schema.org/")


def find_country_from_pob(pob, verbose=False):
    search_term = pob.split(",")[-1].strip(" ,.:;-")
    if search_term == "":
        return None
    try:
        res = countries.search_fuzzy(search_term)
        country = res[0].name
        if verbose:
            print(f"{search_term} -> {country} ({pob})", file=sys.stderr)
        return country
    except (LookupError, AttributeError):
        try:
            res = subdivisions.search_fuzzy(search_term)
            country = res[0].country.name
            if verbose:
                print(f"{search_term} -> {country} ({pob})", file=sys.stderr)
            return country
        except (LookupError, AttributeError):
            try:
                res = historic_countries.search_fuzzy(search_term)
                country = res[0].name
                if verbose:
                    print(f"{search_term} -> {country} ({pob})",
                          file=sys.stderr)
                return country
            except (LookupError, AttributeError):
                if verbose:
                    print(f"{search_term} -> {None} ({pob})", file=sys.stderr)
                return None


class RoyalsGraph(Graph):
    """A custom graph class for royals."""

    def __init__(self):
        super().__init__()
        self.bind("rel", REL)
        self.bind("royals", ROYALS)
        self.bind("schema", SCHEMA)
        # self.gender_lookup = {'M': 'male', 'F': 'female'}
        self.gender_lookup = {'M': ROYALS["Man"], 'F': ROYALS["Woman"]}
        self.countries = []

        self.parse_ontology_structures({
            'foaf': 'http://xmlns.com/foaf/spec/index.rdf',
            'schema': 'https://schema.org/version/latest/schemaorg-current-https.ttl',
            'rel': 'https://vocab.org/relationship/rel-vocab-20100607.rdf'
        })

        self.extend_foaf()

    def parse_ontology_structures(self, ontology_urls: dict, verbose=False):

        for ns in list(self.namespaces()):
            prefix = ns[0]
            url = ontology_urls.get(prefix)
            if url is not None:
                try:
                    self.parse(url, format='xml' if url.endswith(
                        '.rdf') else 'turtle')
                except HTTPError as e:
                    print(f"{e} : {url}")
                    raise
            else:
                if verbose:
                    print(
                        f"Namespace {ns} not found in ontologies.", file=sys.stderr)
                continue

    def extend_foaf(self):
        self.add((ROYALS["Man"], RDFS.subClassOf, FOAF.Person))
        self.add((ROYALS["Man"], RDFS.label,
                 Literal("Man", datatype=XSD.string)))
        self.add((ROYALS["Woman"], RDFS.subClassOf, FOAF.Person))
        self.add((ROYALS["Woman"], RDFS.label,
                 Literal("Woman", datatype=XSD.string)))

    def add_individual(self, ind):
        """Add an individual to the graph."""
        id = ind.get_pointer().strip('@')
        uri = ROYALS[id]

        # TODO Insteaed of using gender as a string, create a subclass
        # structure so there is more of a heirarchy
        self.add((uri, RDF.type, self.gender_lookup.get(
            element.get_gender(), FOAF.Person)))

        givenName = ind.get_name()[0].strip()
        familyName = ind.get_name()[1].strip()
        fullName = "" if givenName + \
            familyName == "" else givenName if familyName == "" else familyName if givenName == "" else givenName + " " + familyName
        if givenName != "":
            self.add((uri, FOAF.givenName, Literal(
                givenName, datatype=XSD.string)))
        if familyName != "":
            self.add((uri, FOAF.familyName, Literal(
                familyName, datatype=XSD.string)))
        if fullName != "":
            self.add((uri, FOAF.name, Literal(fullName, datatype=XSD.string)))

        country = find_country_from_pob(ind.get_birth_place())
        if country is not None:
            country_uri = self.add_country(country)
            if country_uri is not None:
                self.add((uri, SCHEMA.birthPlace, country_uri))

        return uri

    def add_country(self, country):
        if country == "":
            return None
        else:
            try:
                tc = 0
                for t in self.triples((None, RDFS.label, Literal(country, datatype=XSD.string))):
                    tc += 1
                    assert tc < 2
                    if len(
                            list(self.triples((t[0], RDF.type, SCHEMA.Country)))) == 1:
                        country_uri = t[0]
                    else:
                        assert False
                country_uri
            except (AssertionError, UnboundLocalError):
                id = f"C{len(self.countries)+1:0>3}"
                country_uri = ROYALS[id]

                self.add((country_uri, RDF.type, SCHEMA.Country))
                self.add((country_uri, RDFS.label, Literal(
                    country, datatype=XSD.string)))
                self.countries.append(country_uri)
            return country_uri


if __name__ == "__main__":

    file_path = 'data/Queen_Eliz_II.ged'

    gedcom_parser = Parser()
    gedcom_parser.parse_file(file_path, strict=False)

    elements = gedcom_parser.get_root_child_elements()

    print(
        f"There are {sum(1 for i in elements if isinstance(i, IndividualElement))} Individuals in the file.")

    # Create graph
    g = RoyalsGraph()

    # Iterate through all root child elements
    for element in tqdm(elements):
        # Is the `element` an actual `IndividualElement`? (Allows usage of extra functions such as `surname_match` and `get_name`.)
        if isinstance(element, IndividualElement):
            element_uri = g.add_individual(element)

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
