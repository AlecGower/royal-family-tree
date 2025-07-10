import sys

from tqdm.auto import tqdm
from pprint import pprint, pformat

from urllib.error import HTTPError

from gedcom.element.individual import IndividualElement
from gedcom.parser import Parser

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, FOAF, XSD

from royal_family_tree.namespaces import REL, ROYALS, SCHEMA
from royal_family_tree.helpers import find_country_from_pob


class RoyalsGraph(Graph):
    """A custom graph class for royals loaded from GED dataset."""

    def __init__(self, ged_file_path):
        super().__init__()
        self.gedcom_parser = Parser()
        self.gedcom_parser.parse_file(ged_file_path, strict=False)

        print(
            f"There are {sum(1 for i in self.gedcom_parser.get_root_child_elements() if isinstance(i, IndividualElement))} Individuals in the file.")

        # self.gender_lookup = {'M': 'male', 'F': 'female'}
        self.gender_lookup = {'M': ROYALS["Man"], 'F': ROYALS["Woman"]}
        self.countries = []

        self.parse_ontology_structures({
            'foaf': 'http://xmlns.com/foaf/spec/index.rdf',
            'schema': 'https://schema.org/version/latest/schemaorg-current-https.rdf',
            'rel': 'https://vocab.org/relationship/rel-vocab-20100607.rdf'
        })
        print(f"Loaded ontologies: {pformat(list(self.namespaces()))}")

        self.extend_foaf()
        L = len(self)
        self.fix_schema()
        print(
            f"Fixed `schema`, now has {len(self)} triples (was {L}).", file=sys.stderr)

    def parse_ontology_structures(self, ontology_urls: dict, verbose=True):

        for ns in list(self.namespaces()):
            prefix = ns[0]
            url = ontology_urls.get(prefix)
            if url is not None:
                try:
                    self.parse(url, format='xml' if url.endswith(
                        '.rdf') else 'turtle')
                    if verbose:
                        print(
                            f"SUCCESS: Namespace {ns} successfully loaded.", file=sys.stderr)
                except HTTPError as e:
                    print(f"{e} : {url}")
                    raise
            else:
                if verbose:
                    print(
                        f"WARN:    Namespace {ns} not found in ontologies.", file=sys.stderr)
                continue

    def fix_schema(self):
        # These uris were causing problems, because they were listed
        # as both individuals of a class, and as a class.
        #
        # Or at least this holds for the medical ones, for the datatypes
        # I am not so sure.
        problematic_uris = [
            "https://schema.org/Boolean",
            "https://schema.org/CommunityHealth",
            "https://schema.org/Dermatology",
            "https://schema.org/DietNutrition",
            "https://schema.org/Emergency",
            "https://schema.org/Geriatric",
            "https://schema.org/Gynecologic",
            "https://schema.org/Midwifery",
            "https://schema.org/Number",
            "https://schema.org/Nursing",
            "https://schema.org/Obstetric",
            "https://schema.org/Oncologic",
            "https://schema.org/Optometric",
            "https://schema.org/Otolaryngologic",
            "https://schema.org/Pediatric",
            "https://schema.org/Physiotherapy",
            "https://schema.org/PlasticSurgery",
            "https://schema.org/Podiatric",
            "https://schema.org/PrimaryCare",
            "https://schema.org/Psychiatric",
            "https://schema.org/PublicHealth",
            "https://schema.org/RespiratoryTherapy",
            "https://schema.org/Text",
        ]

        for uri in problematic_uris:
            self.remove((URIRef(uri), None, None))
            self.remove((None, None, URIRef(uri)))

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

        self.add((uri, RDF.type, self.gender_lookup.get(
            ind.get_gender(), FOAF.Person)))

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

    def load_ged_data(self):
        # Iterate through all root child elements
        for element in tqdm(self.gedcom_parser.get_root_child_elements()):
            # Is the `element` an actual `IndividualElement`? (Allows usage of extra functions such as `surname_match` and `get_name`.)
            if isinstance(element, IndividualElement):
                element_uri = self.add_individual(element)

                # Get parents of the individual
                for parent in self.gedcom_parser.get_parents(element):
                    if isinstance(parent, IndividualElement):
                        parent_id = parent.get_pointer().strip('@')
                        parent_uri = ROYALS[parent_id]
                        self.add((parent_uri, REL.parentOf, URIRef(
                            element_uri)))

                # Get spouses of the individual
                for spouse in self.gedcom_parser.get_spouses(element):
                    if isinstance(spouse, IndividualElement):
                        spouse_id = spouse.get_pointer().strip('@')
                        spouse_uri = ROYALS[spouse_id]
                        self.add((spouse_uri, REL.spouseOf, URIRef(
                            element_uri)))

                # Get children of the individual
                for child in self.gedcom_parser.get_children(element):
                    if isinstance(child, IndividualElement):
                        child_id = child.get_pointer().strip('@')
                        child_uri = ROYALS[child_id]
                        self.add(
                            (URIRef(element_uri), REL.parentOf, child_uri))
                        self.add((child_uri, REL.childOf, URIRef(
                            element_uri)))
