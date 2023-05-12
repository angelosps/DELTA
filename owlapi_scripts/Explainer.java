package msc;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Stack;
import java.util.function.Supplier;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owl.explanation.api.Explanation;
import org.semanticweb.owl.explanation.api.ExplanationGenerator;
import org.semanticweb.owl.explanation.api.ExplanationGeneratorFactory;
import org.semanticweb.owl.explanation.api.ExplanationProgressMonitor;
import org.semanticweb.owl.explanation.impl.blackbox.Configuration;
import org.semanticweb.owl.explanation.impl.blackbox.DivideAndConquerContractionStrategy;
import org.semanticweb.owl.explanation.impl.blackbox.EntailmentCheckerFactory;
import org.semanticweb.owl.explanation.impl.blackbox.InitialEntailmentCheckStrategy;
import org.semanticweb.owl.explanation.impl.blackbox.StructuralTypePriorityExpansionStrategy;
import org.semanticweb.owl.explanation.impl.blackbox.checker.BlackBoxExplanationGeneratorFactory;
import org.semanticweb.owl.explanation.impl.blackbox.checker.SatisfiabilityEntailmentCheckerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.AxiomType;
import org.semanticweb.owlapi.model.OWLAxiom;
import org.semanticweb.owlapi.model.OWLClassAssertionAxiom;
import org.semanticweb.owlapi.model.OWLClassExpression;
import org.semanticweb.owlapi.model.OWLDataFactory;
import org.semanticweb.owlapi.model.OWLDisjointClassesAxiom;
import org.semanticweb.owlapi.model.OWLIndividual;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyCreationException;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.model.OWLSubClassOfAxiom;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.reasoner.OWLReasonerFactory;
import org.semanticweb.owlapi.util.InferredAxiomGenerator;
import org.semanticweb.owlapi.util.InferredClassAssertionAxiomGenerator;
import org.semanticweb.owlapi.util.InferredOntologyGenerator;
import org.semanticweb.owlapi.util.InferredPropertyAssertionGenerator;
import org.semanticweb.owlapi.util.InferredSubClassAxiomGenerator;

public class Explainer {

    public static void explain(OWLAxiom entailment, ExplanationGenerator<OWLAxiom> explanation_generator) {
        try {
            Set<Explanation<OWLAxiom>> explanations = explanation_generator.getExplanations(entailment, 1);
            explanations.forEach(System.out::println);
            System.out.println("EndOfExplanation\n");
        } catch (Exception e) {
        }
    };

    // This method replicates code existing in the owlexplanation project;
    // it's needed because the factories in owlexplanation do not set
    // InitialEntailmentCheckStrategy correctly
    public static ExplanationGeneratorFactory<OWLAxiom> createExplanationGeneratorFactory(
            OWLReasonerFactory reasonerFactory, ExplanationProgressMonitor<OWLAxiom> progressMonitor,
            Supplier<OWLOntologyManager> m) {
        EntailmentCheckerFactory<OWLAxiom> checker = new SatisfiabilityEntailmentCheckerFactory(reasonerFactory, m);
        Configuration<OWLAxiom> config = new Configuration<>(checker,
                new StructuralTypePriorityExpansionStrategy<OWLAxiom>(InitialEntailmentCheckStrategy.PERFORM, m),
                new DivideAndConquerContractionStrategy<OWLAxiom>(), progressMonitor, m);
        return new BlackBoxExplanationGeneratorFactory<>(config);
    };

    public static void main(String[] args) throws OWLOntologyCreationException {
        // ===================== L O A D O N T O L O G Y ===================== //
        OWLOntologyManager onto_manager = OWLManager.createOWLOntologyManager();
        OWLOntology onto = onto_manager.loadOntologyFromOntologyDocument(new File("ALCQ_ontology.owl"));

        OWLDataFactory data_factory = onto.getOWLOntologyManager().getOWLDataFactory();

        // =========================== R E A S O N ============================ //
        OWLReasonerFactory reasoner_factory = new ReasonerFactory();
        OWLReasoner reasoner = reasoner_factory.createReasoner(onto);
        if (reasoner.isConsistent() == false) {
            System.out.println("INCONSISTENT ONTOLOGY!");
            System.exit(0);
        }

        // =========================== U N S A T C L A S S E S
        // ============================ //
        if (reasoner.getUnsatisfiableClasses().getEntitiesMinusBottom().size() > 0) {
            System.out.println("INCOHERENT ONTOLOGY!\n");
            System.exit(0);
        }

        List<InferredAxiomGenerator<? extends OWLAxiom>> inferred_axiom_generator = new ArrayList<InferredAxiomGenerator<? extends OWLAxiom>>();

        // For these types of axioms we care //
        inferred_axiom_generator.add(new InferredClassAssertionAxiomGenerator());
        inferred_axiom_generator.add(new InferredSubClassAxiomGenerator());
        inferred_axiom_generator.add(new InferredPropertyAssertionGenerator());

        // Create a new ontology just for the inferred axioms //
        OWLOntology inferred_axioms_onto = onto_manager.createOntology();
        InferredOntologyGenerator inferred_onto_generator = new InferredOntologyGenerator(reasoner,
                inferred_axiom_generator);
        inferred_onto_generator.fillOntology(data_factory, inferred_axioms_onto);
        inferred_axioms_onto.addAxioms(onto.axioms());

        // Adds negated assertions, e.g., if A subclassOf B, D subclass of C,
        // disjoint(B, C), A(a), it generates: \not D(a), \not C(a).
        inferred_axioms_onto.addAxioms(negativeAssertionsGeneration(inferred_axioms_onto, onto_manager, data_factory));

        // Adds the transitive closure of subclass of, e.g., if A subclassof B, B
        // subclass of C, it generates: A subclass of C.
        addTransitiveClosureOfSubclassOf(inferred_axioms_onto, onto_manager, data_factory);

        // =========================== E X P L A I N =========================== //
        ExplanationGeneratorFactory<OWLAxiom> explanation_generator_factory = createExplanationGeneratorFactory(
                reasoner_factory, null, OWLManager::createOWLOntologyManager);
        ExplanationGenerator<OWLAxiom> explanation_generator = explanation_generator_factory
                .createExplanationGenerator(onto);

        inferred_axioms_onto.logicalAxioms().forEach(e -> explain(e, explanation_generator));
        System.exit(0);
    }

    public static OWLOntology addTransitiveClosureOfSubclassOf(OWLOntology inferred_axioms_onto,
            OWLOntologyManager manager, OWLDataFactory data_factory) {
        Map<OWLClassExpression, Set<OWLClassExpression>> class2superclassesOWL = transitiveClosureSubclassAxioms(
                inferred_axioms_onto);

        for (OWLClassExpression lhs : class2superclassesOWL.keySet()) {
            for (OWLClassExpression rhs : class2superclassesOWL.get(lhs)) {
                OWLSubClassOfAxiom subclassAx = data_factory.getOWLSubClassOfAxiom(lhs, rhs);

                if (!inferred_axioms_onto.containsAxiom(subclassAx)) {
                    manager.addAxiom(inferred_axioms_onto, subclassAx);
                }
            }
        }
        return inferred_axioms_onto;
    }

    @SuppressWarnings("deprecation")
    public static HashSet<OWLClassAssertionAxiom> negativeAssertionsGeneration(OWLOntology inferred_axioms_onto,
            OWLOntologyManager manager, OWLDataFactory data_factory) {

        HashSet<OWLClassAssertionAxiom> newClassAssertions = new HashSet<OWLClassAssertionAxiom>();
        OWLAxiom[] axiomsArray = inferred_axioms_onto.axioms().toArray(OWLAxiom[]::new);
        for (OWLAxiom a : axiomsArray) {
            if (a.isOfType(AxiomType.DISJOINT_CLASSES)) {
                OWLDisjointClassesAxiom disjointnessAxiom = (OWLDisjointClassesAxiom) a;

                OWLSubClassOfAxiom disjointnessAxiom_asSubclassAx_0 = (OWLSubClassOfAxiom) disjointnessAxiom
                        .asOWLSubClassOfAxioms().toArray()[0];
                OWLSubClassOfAxiom disjointnessAxiom_asSubclassAx_1 = (OWLSubClassOfAxiom) disjointnessAxiom
                        .asOWLSubClassOfAxioms().toArray()[1];

                ArrayList<OWLSubClassOfAxiom> disjointessAxioms = new ArrayList<OWLSubClassOfAxiom>();
                disjointessAxioms.add(disjointnessAxiom_asSubclassAx_0);
                disjointessAxioms.add(disjointnessAxiom_asSubclassAx_1);

                for (int i = 0; i < 2; i++) {
                    OWLSubClassOfAxiom ax = disjointessAxioms.get(i);
                    OWLClassExpression subclass = ax.getSubClass();
                    OWLClassExpression superclass = ax.getSuperClass();
                    if (!subclass.toString().contains("ObjectComplementOf(owl:Nothing)")
                            && !superclass.toString().contains("ObjectComplementOf(owl:Nothing)")) {
                        for (OWLClassAssertionAxiom assertionAxiomOfSubclass : inferred_axioms_onto
                                .getClassAssertionAxioms(subclass)) {
                            OWLIndividual individual = assertionAxiomOfSubclass.getIndividual();
                            OWLClassAssertionAxiom classAssertion = data_factory
                                    .getOWLClassAssertionAxiom(superclass.getNNF(), individual);
                            if (!newClassAssertions.contains(classAssertion)) {
                                manager.addAxiom(inferred_axioms_onto, classAssertion);
                                newClassAssertions.add(classAssertion);
                            }
                        }
                    }
                }
            }
        }

        return newClassAssertions;
    }

    public static Map<OWLClassExpression, Set<OWLClassExpression>> transitiveClosureSubclassAxioms(
            OWLOntology inferred_axioms_onto) {
        Map<OWLClassExpression, Set<OWLClassExpression>> class2superclassesOWL = new HashMap<OWLClassExpression, Set<OWLClassExpression>>();
        Set<OWLSubClassOfAxiom> subclassAxioms = new HashSet<OWLSubClassOfAxiom>();

        OWLAxiom[] axiomsArray = inferred_axioms_onto.axioms().toArray(OWLAxiom[]::new);
        for (OWLAxiom axiom : axiomsArray) {
            if (axiom.isOfType(AxiomType.SUBCLASS_OF)) {
                subclassAxioms.add((OWLSubClassOfAxiom) axiom);
            }
        }

        for (OWLSubClassOfAxiom subclassAxiom : subclassAxioms) {
            Stack<OWLClassExpression> supclasses_stack = new Stack<OWLClassExpression>();
            Set<OWLClassExpression> addedClassInStack = new HashSet<OWLClassExpression>();
            OWLClassExpression sbclass = subclassAxiom.getSubClass();
            OWLClassExpression spclass = subclassAxiom.getSuperClass();
            supclasses_stack.push(spclass);
            addedClassInStack.add(spclass);
            while (!supclasses_stack.isEmpty()) {
                OWLClassExpression supClass = supclasses_stack.pop();
                if (!class2superclassesOWL.keySet().contains(sbclass)) {
                    Set<OWLClassExpression> tempspcls1 = new HashSet<OWLClassExpression>();
                    tempspcls1.add(supClass);
                    class2superclassesOWL.put(sbclass, tempspcls1);
                } else {
                    class2superclassesOWL.get(sbclass).add(supClass);
                }
                for (OWLSubClassOfAxiom d : subclassAxioms) {
                    if (d.getSubClass().equals(supClass)) {
                        OWLClassExpression sp_c = d.getSuperClass();
                        if (!addedClassInStack.contains(sp_c)) {
                            supclasses_stack.push(sp_c);
                            addedClassInStack.add(sp_c);
                        }
                    }
                }
            }
        }

        return class2superclassesOWL;
    }
}