import edu.buffalo.sneps.JavaSnepsAPI;
import edu.buffalo.sneps.Substitution;
import java.util.HashSet;


// Small example on how to use the SNePSAPI

// Copy to your own directory if you want to recompile the code.
// Replace "/projects/snwiz/Install/Sneps-2.7.0" with the location of the
// SNePS directory


// Compile: javac -classpath ".:/projects/snwiz/Install/Sneps-2.7.0/Jlinker/jlinker.jar:/projects/snwiz/Install/Sneps-2.7.0/JavaSnepsAPI/JavaSnepsAPI.jar" TestAPI.java

// My version compiled under Java 1.5
// Run: java -classpath ".:/projects/snwiz/Install/Sneps-2.7.0/Jlinker/jlinker.jar:/projects/snwiz/Install/Sneps-2.7.0/JavaSnepsAPI/JavaSnepsAPI.jar" TestAPI

public class TestAPI {

    
    public static String [] commands
	= {"set-mode-3",
	   "define-frame Isa (nil member class)",
	   "define-frame Ako (nil class1 class2)",
	   "define-frame Believes (nil agent prop)",
	   "Isa(Clyde, Elephant).",
	   "Isa(Dumbo, Elephant).",
	   "Isa(Tweety, Canary).",
	   "Ako(Elephant, Mammal).",
	   "Ako(Mammal, Animal).",
	   "Ako(Bird, Animal)."};

    
    public static void main(String[] args) {
       
	// Create an instance of the API
	JavaSnepsAPI api =
	    new JavaSnepsAPI("/projects/snwiz/Install/Sneps-2.7.0/JavaSnepsAPI/java_sneps_config.config",
			     5668);
       
	// Testing the tell method:
	for (String cmd: commands) {
	    System.out.println("Telling: " + cmd);
	    api.tell(cmd);
	} 

	// Testing the ask method:
	System.out.println("Asking Isa(?x, Elephant)...");
	HashSet<String> answers = api.ask("Isa(?x,Elephant)");

	for(String answer: answers) {
	    System.out.println("Received:" + answer);
	} 
       
       
	// Testing the askwh method:
	System.out.println("Asking Ako(?x,?y)...");
	HashSet<Substitution> substset = api.askwh("Ako(?x,?y)");
	for(Substitution subst: substset) {
	    System.out.println("Received: " + subst.getValFromVar("x")
			       + "s are " + subst.getValFromVar("y") + "s.");
	}
	

       
	api.endLispConnection();

    }
}
