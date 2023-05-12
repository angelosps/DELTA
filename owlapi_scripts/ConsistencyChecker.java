package msc;

import java.io.File;
import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyCreationException;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.reasoner.OWLReasoner;
import org.semanticweb.owlapi.reasoner.OWLReasonerFactory;

public class ConsistencyCheck {
	public static void main(String[] args) throws OWLOntologyCreationException {
		// ===================== L O A D  O N T O L O G Y ===================== //
		OWLOntologyManager onto_manager = OWLManager.createOWLOntologyManager(); 
		OWLOntology onto = onto_manager.loadOntologyFromOntologyDocument(new File("ALCQCC.owl"));
		
		// =========================== R E A S O N ============================ //
		OWLReasonerFactory reasoner_factory = new ReasonerFactory();
		OWLReasoner reasoner = reasoner_factory.createReasoner(onto);
		if (reasoner.isConsistent() == false) {
			System.out.println("INCONSISTENT ONTOLOGY!");
		}
		System.exit(0);
	}
}