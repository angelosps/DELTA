from abc import ABC
from nl_utils import pluralize
import random


class Concept(ABC):
    """Class representing a Concept."""

    def __init__(self):
        pass


class AtomicConcept(Concept):
    """Class representing an Atomic Concept."""

    def __init__(self, polarity, concept_name):
        self.polarity = polarity
        self.concept_name = concept_name

    def __repr__(self):
        return f"{self.polarity} {self.concept_name}"

    def __eq__(self, other):
        return (
            isinstance(other, AtomicConcept)
            and self.polarity == other.polarity
            and self.concept_name == other.concept_name
        )

    def __hash__(self):
        return hash((self.polarity, self.concept_name))

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "AtomicConcept":
            return AtomicConcept(
                json_dict["polarity"],
                json_dict["concept_name"],
            )
        return None

    def to_json(self):
        return {
            "json_class": "AtomicConcept",
            "polarity": self.polarity,
            "concept_name": self.concept_name,
        }

    def nl(self):
        concept_nl = self.concept_name
        polarity = self.polarity
        if polarity == "+":
            if self.concept_name == "⊤":
                concept_nl = "thing"
            elif self.concept_name == "⊥":
                concept_nl = "nothing"
        else:
            if self.concept_name == "⊤":
                concept_nl = "nothing"
            elif self.concept_name == "⊥":
                concept_nl = "thing"
            else:
                concept_nl = f"not {concept_nl}"

        return concept_nl


class JunctionConcept(Concept):
    """Class representing a con-junction or a dis-junction of two concepts."""

    def __init__(
        self, lhs_concept, relationship, rhs_concept, atomic_in_lhs, atomic_in_rhs
    ):
        self.lhs_concept = lhs_concept
        self.relationship = relationship
        self.rhs_concept = rhs_concept
        self.atomic_in_lhs = atomic_in_lhs
        self.atomic_in_rhs = atomic_in_rhs
        self.has_atomic = self.atomic_in_lhs or self.atomic_in_rhs

    def __repr__(self):
        return f"( {self.lhs_concept} ) {self.relationship} ( {self.rhs_concept} )"

    def __eq__(self, other):
        return (
            isinstance(other, JunctionConcept)
            and self.lhs_concept == other.lhs_concept
            and self.relationship == other.relationship
            and self.rhs_concept == other.rhs_concept
        )

    def __hash__(self):
        return hash((self.lhs_concept, self.relationship, self.rhs_concept))

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "JunctionConcept":
            return JunctionConcept(
                json_dict["lhs_concept"].from_json(),
                json_dict["relationship"],
                json_dict["rhs_concept"].from_json(),
            )
        return None

    def to_json(self):
        return {
            "json_class": "Concept",
            "lhs_concept": self.lhs_concept.to_json(),
            "relationship": self.relationship,
            "rhs_concept": self.rhs_concept.to_json(),
        }

    def nl(self, pronoun=""):
        LHS_nl = self.lhs_concept.nl()
        if isinstance(self.rhs_concept, JunctionConcept):
            RHS_nl = self.rhs_concept.nl(pronoun=pronoun)
        else:
            RHS_nl = self.rhs_concept.nl()

        concept_nl = str()
        connective = "or"

        if pronoun != "":
            pronoun += " "

        if self.relationship == "⊓":
            connective = "and"

        if (self.atomic_in_lhs == False) and (self.atomic_in_rhs == True):
            LHS_nl, RHS_nl = RHS_nl, LHS_nl
            if pronoun == "they ":
                return f"{LHS_nl} {connective} {pluralize(f'{pronoun}{RHS_nl}')}"
            else:
                return f"{LHS_nl} {connective} {pronoun}{RHS_nl}"

        elif isinstance(self.rhs_concept, RestrictionConcept) or (
            isinstance(self.rhs_concept, JunctionConcept)
            and not self.rhs_concept.has_atomic
        ):
            if pronoun == "they ":
                return f"{LHS_nl} {connective} {pluralize(f'{pronoun}{RHS_nl}')}"
            else:
                return f"{LHS_nl} {connective} {pronoun}{RHS_nl}"

        concept_nl = f"{LHS_nl} {connective} {RHS_nl}"
        return concept_nl


def num2word(num):
    if num == "1":
        return "one"
    if num == "2":
        return "two"
    if num == "3":
        return "three"


class RestrictionConcept(Concept):
    """Class representing a Concept restriction.
    i.e., ( > 2 R . C ),
    where R: Role and C: Concept.
    """

    def __init__(self, restriction, role_name, concept):
        self.restriction = restriction
        self.role_name = role_name
        self.concept = concept

    def __repr__(self):
        return f"{self.restriction} {self.role_name} . ( {self.concept} )"

    def __eq__(self, other):
        return (
            isinstance(other, RestrictionConcept)
            and self.restriction == other.restriction
            and self.role_name == other.role_name
            and self.concept == other.concept
        )

    def __hash__(self):
        return hash((self.restriction, self.role_name, self.concept))

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "RestrictionConcept":
            return RestrictionConcept(
                json_dict["restriction"],
                json_dict["role_name"],
                json_dict["concept"].from_json(),
            )
        return None

    def to_json(self):
        return {
            "json_class": "Concept",
            "restriction": self.restriction,
            "role_name": self.role_name,
            "concept": self.concept.to_json(),
        }

    def nl(self):
        restr_concept_nl = str()
        restriction = self.restriction.split()
        role_name = self.role_name

        pronoun = "someone"
        noun = "people"

        if isinstance(self.concept, JunctionConcept):
            concept_nl = self.concept.nl(pronoun="that")
        else:
            concept_nl = self.concept.nl()

        some_suffix = concept_nl
        only_suffix = quantity_suffix = f"{concept_nl} {noun}"

        if isinstance(self.concept, JunctionConcept):
            if not self.concept.has_atomic:
                quantity_suffix = (
                    only_suffix
                ) = f"{noun} that {pluralize(concept_nl, whole=True)}"
                some_suffix = f"that {concept_nl}"
            else:
                quantity_suffix = (
                    only_suffix
                ) = f"{noun} that are {pluralize(concept_nl, whole=True)}"
                some_suffix = f"that is {concept_nl}"
        elif isinstance(self.concept, RestrictionConcept):
            quantity_suffix = (
                only_suffix
            ) = f"{noun} that {pluralize(concept_nl, whole=True)}"
            some_suffix = f"that {concept_nl}"

        if restriction[0] == "∀":
            if (
                isinstance(self.concept, AtomicConcept)
                and self.concept.concept_name == "⊥"
            ):
                restr_concept_nl = f"{role_name.replace('_',' ')} none"
            else:
                restr_concept_nl = f"{role_name.replace('_',' ')} only {only_suffix}"
        elif restriction[0] == "∃":
            if (
                isinstance(self.concept, AtomicConcept)
                and self.concept.concept_name == "⊤"
            ):
                restr_concept_nl = f"{role_name.replace('_',' ')} {pronoun}"
            else:
                restr_concept_nl = (
                    f"{role_name.replace('_',' ')} {pronoun} {some_suffix}"
                )
        else:
            quantifier = restriction[0]
            quantity = restriction[1]
            quantifier_nl = str()

            if quantifier == ">":
                quantifier_nl = "more than"
            elif quantifier == "<":
                quantifier_nl = "less than"
            elif quantifier == ">=":
                quantifier_nl = "at least"
            elif quantifier == "<=":
                quantifier_nl = "at most"
            elif quantifier == "=":
                quantifier_nl = "exactly"
            elif quantifier == "!=":
                quantifier_nl = "either less or more than"
            else:
                print(f"Unknown quantifier: {quantifier}")
                assert False

            restr_concept_nl = f"{role_name.replace('_',' ')} {quantifier_nl} {num2word(quantity)} {quantity_suffix}"

        return restr_concept_nl


class ConceptAssertion:
    """Class representing a Concept Assertion"""

    def __init__(self, concept, individual):
        self.concept = concept
        self.individual = individual

    def __repr__(self):
        return f"( {self.concept} ) ( {self.individual} )"

    def __eq__(self, other):
        return (
            isinstance(other, ConceptAssertion)
            and self.concept == other.concept
            and self.individual == other.individual
        )

    def __hash__(self):
        return hash((self.concept, self.individual))

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "ConceptAssertion":
            return ConceptAssertion(
                json_dict["concept"],
                json_dict["individual"],
            )
        return None

    def to_json(self):
        return {
            "json_class": "ConceptAssertion",
            "concept": self.concept.to_json(),
            "individual": self.individual,
        }

    def nl(self):
        assertion_nl = str()
        concept_nl = self.concept.nl()
        if isinstance(self.concept, RestrictionConcept) or (
            isinstance(self.concept, JunctionConcept) and not self.concept.has_atomic
        ):
            if concept_nl.find(" it ") != -1:
                assertion_nl = concept_nl.replace(" it ", f" {self.individual} ")
            else:
                assertion_nl = f"{self.individual} {concept_nl}"
        else:
            assertion_nl = f"{self.individual} is {concept_nl}"

        return assertion_nl


class RoleAssertion:
    """Class representing a Role Assertion"""

    def __init__(self, RoleName, Individual_l, Individual_r):
        self.RoleName = RoleName
        self.Individual_l = Individual_l
        self.Individual_r = Individual_r

    def __repr__(self):
        return f"{self.RoleName} ( {self.Individual_l} , {self.Individual_r} )"

    def __eq__(self, other):
        return (
            isinstance(other, RoleAssertion)
            and self.RoleName == other.RoleName
            and self.Individual_l == other.Individual_l
            and self.Individual_r == other.Individual_r
        )

    def __hash__(self):
        return hash((self.RoleName, self.Individual_l, self.Individual_r))

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "ABoxRole":
            return ConceptAssertion(
                json_dict["RoleName"],
                json_dict["Individual_l"],
                json_dict["Individual_r"],
            )
        return None

    def to_json(self):
        return {
            "json_class": "ABoxRole",
            "RoleName": self.RoleName,
            "Individual_l": self.Individual_l,
            "Individual_r": self.Individual_r,
        }

    def nl(self):
        role_nl = (
            f"{self.Individual_l} {self.RoleName.replace('_', ' ')} {self.Individual_r}"
        )
        return role_nl


class TBoxAxiom:
    """Class representing a TBox Axiom (Subsumption or Equivalence)."""

    def __init__(self, LHS_concept, Relationship, RHS_concept):
        self.LHS_concept = LHS_concept
        self.Relationship = Relationship
        self.RHS_concept = RHS_concept

    def __repr__(self):
        return f"{self.LHS_concept} {self.Relationship} {self.RHS_concept}"

    def __eq__(self, other):
        return (
            isinstance(other, TBoxAxiom)
            and self.LHS_concept == other.LHS_concept
            and self.Relationship == other.Relationship
            and self.RHS_concept == other.RHS_concept
        )

    def __hash__(self):
        return hash((self.LHS_concept, self.Relationship, self.RHS_concept))

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "TBoxAxiom":
            return TBoxAxiom(
                json_dict["LHS_concept"].from_json(),
                json_dict["Relationship"],
                json_dict["RHS_concept"].from_json(),
            )
        return None

    def to_json(self):
        return {
            "json_class": "TBoxAxiom",
            "LHS_concept": self.LHS_concept.to_json(),
            "Relationship": self.Relationship,
            "RHS_concept": self.RHS_concept.to_json(),
        }

    def nl(self):
        LHS_representation = str()
        RHS_representation = str()

        lhs_pronoun = "someone"
        rhs_pronoun = "they are"

        ### SPECIAL AXIOMS ###
        if (
            isinstance(self.LHS_concept, AtomicConcept)
            and self.LHS_concept.concept_name == "⊤"
        ):
            # Likes only things that are blue and they chase someone red
            axiom_nl = (
                f"{lhs_pronoun.capitalize()} can {pluralize(self.RHS_concept.nl())}"
            )
            return axiom_nl

        # With some probability, choose one of the attribute templates,
        # and if concept conditions met
        choice = random.randrange(0, 3)
        if (choice == 1 or choice == 2) and (
            isinstance(self.LHS_concept, AtomicConcept)
            or isinstance(self.RHS_concept, AtomicConcept)
        ):
            if isinstance(self.LHS_concept, AtomicConcept):
                if choice == 1:
                    LHS_representation = f"All {self.LHS_concept.nl()} people"
                else:
                    LHS_representation = f"{self.LHS_concept.nl().capitalize()} people"
            elif isinstance(self.LHS_concept, RestrictionConcept):
                if choice == 1:
                    LHS_representation = (
                        f"All people that {pluralize(self.LHS_concept.nl())}"
                    )
                else:
                    LHS_representation = (
                        f"People that {pluralize(self.LHS_concept.nl())}"
                    )
            elif isinstance(self.LHS_concept, JunctionConcept):
                if choice == 1:
                    if self.LHS_concept.has_atomic:
                        LHS_representation = (
                            f"All people that are {self.LHS_concept.nl('they')}"
                        )
                    else:
                        LHS_representation = (
                            f"All people that {self.LHS_concept.nl('they')}"
                        )
                else:
                    if self.LHS_concept.has_atomic:
                        LHS_representation = (
                            f"People that are {self.LHS_concept.nl('they')}"
                        )
                    else:
                        LHS_representation = (
                            f"People that {self.LHS_concept.nl('they')}"
                        )

            if isinstance(self.RHS_concept, AtomicConcept):
                RHS_representation = f"are {self.RHS_concept.nl()}"
            elif isinstance(self.RHS_concept, RestrictionConcept):
                RHS_representation = f"{pluralize(self.RHS_concept.nl())}"
            elif isinstance(self.RHS_concept, JunctionConcept):
                if self.RHS_concept.has_atomic:
                    RHS_representation = f"are {self.RHS_concept.nl(pronoun='they')}"
                else:
                    RHS_representation = (
                        f"{pluralize(self.RHS_concept.nl(pronoun='they'))}"
                    )

            return f"{LHS_representation} {RHS_representation}"

        rhs_pronoun_no_verb = rhs_pronoun.split()[0]

        # CASE: if something is blue and red, then it is nothing ->
        # will be: if something is blue, then it cannot be red.
        # This case happens only when LHS is conjunction as if it was disjunction and the RHS would be nothing,
        # then the ontology would be inconsistent!

        if (
            isinstance(self.RHS_concept, AtomicConcept)
            and self.RHS_concept.concept_name == "⊥"
            and self.RHS_concept.polarity == "+"
            and isinstance(self.LHS_concept, JunctionConcept)
            and self.LHS_concept.relationship == "⊓"
        ):
            if isinstance(self.LHS_concept.lhs_concept, RestrictionConcept):
                if self.LHS_concept.lhs_concept.restriction == "∃":  # existential
                    concept_nl = f"If {self.LHS_concept.lhs_concept.nl()}, then {rhs_pronoun_no_verb} cannot be {self.LHS_concept.rhs_concept.nl()}"
                else:  # universal or quantification
                    concept_nl = f"If {lhs_pronoun} {self.LHS_concept.lhs_concept.nl()}, then {rhs_pronoun_no_verb} cannot {self.LHS_concept.rhs_concept.nl()}"
            else:  # conjunction of two atomic concepts
                concept_nl = f"If {lhs_pronoun} {self.LHS_concept.lhs_concept.nl()}, then {rhs_pronoun_no_verb} cannot be {self.LHS_concept.rhs_concept.nl()}"
        else:
            LHS_junction = isinstance(self.LHS_concept, JunctionConcept)
            LHS_restriction = isinstance(self.LHS_concept, RestrictionConcept)

            if LHS_junction:
                LHS_nl = self.LHS_concept.nl()
            else:
                LHS_nl = self.LHS_concept.nl()

            if LHS_restriction or (LHS_junction and not self.LHS_concept.has_atomic):
                LHS_representation = f"{lhs_pronoun} {LHS_nl}"
            else:
                LHS_representation = f"{lhs_pronoun} is {LHS_nl}"

            RHS_junction = isinstance(self.RHS_concept, JunctionConcept)
            RHS_restriction = isinstance(self.RHS_concept, RestrictionConcept)

            if RHS_junction and (rhs_pronoun_no_verb == "they"):
                RHS_nl = self.RHS_concept.nl(pronoun=rhs_pronoun_no_verb)
            else:
                RHS_nl = self.RHS_concept.nl()

            if rhs_pronoun_no_verb == "they":
                if RHS_nl.split()[0][-2:] in {"es", "ts"}:
                    RHS_nl = pluralize(RHS_nl)

            if RHS_restriction or (RHS_junction and not self.RHS_concept.has_atomic):
                RHS_representation = f"{rhs_pronoun_no_verb} {RHS_nl}"
            else:
                RHS_representation = f"{rhs_pronoun} {RHS_nl}"

            concept_nl = f"If {LHS_representation}, then {RHS_representation}"

        return concept_nl


class DifferentIndividualsAssertion:
    """Class representing a Role Assertion."""

    def __init__(self, Individual_l, Individual_r):
        self.Individual_l = Individual_l
        self.Individual_r = Individual_r

    def __repr__(self):
        return f"{self.Individual_l} ≠ {self.Individual_r}"

    def __eq__(self, other):
        return (
            isinstance(other, DifferentIndividualsAssertion)
            and self.Individual_l == other.Individual_l
            and self.Individual_r == other.Individual_r
        )

    def __hash__(self):
        return hash((self.Individual_l, self.Individual_r))

    def to_json(self):
        return {
            "json_class": "DifferentIndividualsAssertion",
            "Individual_l": self.Individual_l,
            "Individual_r": self.Individual_r,
        }

    def nl(self):
        diff_assertion_nl = (
            f"{self.Individual_l} and {self.Individual_r} are different entities"
        )
        return diff_assertion_nl


class Theory:
    """Class representing a "theory": collection of ABox Assertions and TBox Axioms."""

    def __init__(
        self, ABoxAssertions, TBoxAxioms, generated_statements, statements_as_texts=None
    ):
        self.ABoxAssertions = ABoxAssertions
        self.TBoxAxioms = TBoxAxioms
        self.generated_statements = generated_statements

        if statements_as_texts is None:
            self.statements_as_texts = []
            for assertion in ABoxAssertions:
                if isinstance(assertion, DifferentIndividualsAssertion):
                    continue
                self.statements_as_texts.append(str(assertion))
            for axiom in TBoxAxioms:
                self.statements_as_texts.append(str(axiom))
        else:
            self.statements_as_texts = statements_as_texts

    def __eq__(self, other):
        return (
            isinstance(other, Theory)
            and set(self.ABoxAssertions) == set(other.ABoxAssertions)
            and set(self.TBoxAxioms) == set(other.TBoxAxioms)
        )

    def __hash__(self):
        return hash(
            (tuple(sorted(self.ABoxAssertions)), tuple(sorted(self.TBoxAxioms)))
        )

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "Theory":
            ABoxAssertions = [
                assertion.from_json(assertion)
                for assertion in json_dict["ABoxAssertions"]
            ]
            TBoxAxioms = [axiom.from_json(axiom) for axiom in json_dict["TBoxAxioms"]]
            return Theory(ABoxAssertions, TBoxAxioms)
        return None

    def to_json(self):
        ABoxAssertions = [assertion.to_json() for assertion in self.ABoxAssertions]
        TBoxAxioms = [axiom.to_json() for axiom in self.TBoxAxioms]
        return {
            "json_class": "Theory",
            "ABoxAssertions": ABoxAssertions,
            "TBoxAxioms": TBoxAxioms,
        }

    def constants(self):
        """All the constant terms that appear in this theory. Correspond to
        terminals in the grammar from which the theory was built."""
        constants_in_theory = set()
        for assertion in self.ABoxAssertions:
            constants_in_theory = constants_in_theory.union(assertion.constants())
        for axiom in self.TBoxAxioms:
            constants_in_theory = constants_in_theory.union(axiom.constants())
        return constants_in_theory

    def nl(self):
        nl = self.generated_statements
        return nl


class TheoryAssertionInstance:
    """Class representing a theory-assertion pair instance to be input to a model.
    Consists a gold truth label for the assertion's truthiness with respect to the theory.
    The `exception` field is a placeholder to store any exceptions thrown by the theorem prover
    on existing theory datasets generated outside of ruletaker. Other theory datasets can be validated
    or evaluated by running them through theorem provers supported in this repo by using the
    `theory_label_generator` tool.
    `min_proof_depth` is an integer field containing the depth of the
    proof; the depth of the simplest (shortest) proof if there are multiple.
    `proof` is a string representation of the proof from the theorem prover.
    The proof related fields are only present (not None) if the `label` is True."""

    def __init__(self, theory, questions):
        self.theory = theory
        self.questions = questions

    def __eq__(self, other):
        return (
            isinstance(other, TheoryAssertionInstance)
            and self.theory == other.theory
            and self.questions == other.questions
        )

    def __hash__(self):
        return hash(
            (
                self.theory,
                self.questions,
            )
        )

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "TheoryAssertionInstance":
            return TheoryAssertionInstance(
                Theory.from_json(json_dict["theory"]), json_dict["questions"]
            )
        return None

    def to_json(self):
        return {
            "json_class": "TheoryAssertionInstance",
            "theory": self.theory.to_json(),
            "questions": self.questions,
        }


class DescriptionLogicsForm:
    def __init__(self, theory_statements_in_DL, question_statements_in_DL):
        self.theory_statements_in_DL = theory_statements_in_DL
        self.question_statements_in_DL = question_statements_in_DL

    def __hash__(self):
        return hash(
            (tuple(self.theory_statements_in_DL), self.question_statements_in_DL)
        )

    def __eq__(self, other):
        return (
            isinstance(other, DescriptionLogicsForm)
            and set(self.theory_statements_in_DL) == set(other.theory_statements_in_DL)
            and self.question_statements_in_DL == other.question_statements_in_DL
        )

    @classmethod
    def from_json(cls, json_dict):
        json_class = json_dict.get("json_class")
        if json_class == "DescriptionLogicsForm":
            return DescriptionLogicsForm(json_dict["theory"], json_dict["questions"])
        return None

    def to_json(self):
        return {
            "json_class": "DescriptionLogicsForm",
            "theory": self.theory_statements_in_DL,
            "questions": self.question_statements_in_DL,
        }


class Example:
    """Class representing a generated example, which constitutes a TheoryAssertionInstance
    and its representations as logical forms in prefix notation and natural language."""

    def __init__(self, id, theory_assertion_instance, logical_forms=None, english=None):
        self.id = id
        self.theory_assertion_instance = theory_assertion_instance
        if logical_forms is not None:
            self.logical_forms = logical_forms
        else:  # Make the Logical Forms
            self.logical_forms = theory_assertion_instance.theory.statements_as_texts
        if english is not None:
            self.english = english
        else:
            raise RuntimeError

    def __eq__(self, other):
        return (
            isinstance(other, Example)
            and self.id == other.id
            and self.theory_assertion_instance == other.theory_assertion_instance
            and self.logical_forms == other.logical_forms
            and self.english == other.english
        )

    def __hash__(self):
        return hash(
            (
                self.id,
                self.theory_assertion_instance,
                self.logical_forms,
                self.english,
            )
        )

    def to_json(self):
        return {
            "id": self.id,
            "context": self.english,
            "questions": self.theory_assertion_instance.questions,
            "context_logical_form": self.logical_forms,
        }
