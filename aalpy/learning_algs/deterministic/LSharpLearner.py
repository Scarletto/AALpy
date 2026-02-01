import random
from .ObservationTree import ObservationTree, MealyRetryLeaf, MealyGotoNode
from .ADS import Ads
from .Apartness import Apartness
from ... import Dfa, DfaState, MealyState, MealyMachine, MooreMachine, MooreState


class LSharpLearner:
    """
    L# learning algorithm for deterministic automata.
    
    This class implements the L# algorithm which uses an observation tree
    to learn DFA, Moore, or Mealy machines. It maintains:
    - A set of "basis" states: confirmed distinct states of the target automaton
    - A set of "frontier" states: states that may or may not be distinct from basis states
    - Mappings from frontier states to their potential basis state equivalents
    
    The learning algorithm iteratively refines the tree until:
    1. Each frontier state maps to exactly one basis state
    2. All basis states have defined outputs/transitions for all inputs
    """
    
    def __init__(self, alphabet, sul, automaton_type, extension_rule, separation_rule, 
                 crash_output=None, retry_output=None, goto_outputs=[]):
        """
        Initialize the L# learner.
        
        Args:
            alphabet: Set of input symbols
            sul: System Under Learning interface
            automaton_type: 'dfa', 'mealy', or 'moore'
            extension_rule: 'ADS' or 'SepSeq' - how to extend frontier exploration
            separation_rule: 'ADS' or 'SepSeq' - how to separate ambiguous frontiers
            crash_output: (Mealy only) Output indicating system crash
            retry_output: (Mealy only) Output indicating input had no effect
            goto_outputs: (Mealy only) Outputs indicating jump to another state
        """
        # Create the observation tree (composition, not inheritance)
        self.tree = ObservationTree(alphabet, sul, automaton_type, 
                                    crash_output, retry_output, goto_outputs)
        
        self.alphabet = alphabet
        self.sul = sul
        self.automaton_type = automaton_type
        self.extension_rule = extension_rule
        self.separation_rule = separation_rule

        # Basis starts with just the root (initial state)
        self.basis = [self.tree.root]
        
        # Maps frontier states to their candidate basis states
        # A frontier is "identified" when it maps to exactly one basis state
        self.frontier_to_basis_dict = {}

        # Cache for separating sequences between basis state pairs
        self.witness_cache = {}
        
        # Maps basis states to hypothesis automaton states
        self.states_dict = {}
        
        # Track if any goto node becomes a basis state
        self.goto_is_in_basis = False

    # =========================================================================
    # Basis and Frontier Management
    # =========================================================================
    
    def update_frontier_and_basis(self):
        """
        Main update cycle for the basis/frontier partition.
        1. Remove incompatible basis candidates from frontiers
        2. Promote isolated frontiers (no candidates) to basis
        3. Add new frontiers from basis state successors
        4. Re-check compatibility after changes
        """
        self.update_frontier_to_basis_dict()
        self.promote_frontier_state()
        self.check_frontier_consistency()
        self.update_frontier_to_basis_dict()

    def update_basis_candidates(self, frontier_state):
        """
        Filter basis candidates for a single frontier state.
        Removes any basis state that is provably different (apart) from the frontier.
        """
        if frontier_state not in self.frontier_to_basis_dict:
            print(f"Warning: {frontier_state} not found in frontier_to_basis_dict.")
            return

        basis_list = self.frontier_to_basis_dict[frontier_state]
        self.frontier_to_basis_dict[frontier_state] = [
            basis_state for basis_state in basis_list
            if not self.states_are_apart(frontier_state, basis_state)
        ]
        

    def update_frontier_to_basis_dict(self):
        """Remove apart basis states from all frontier candidate lists"""
        for frontier_state, basis_list in self.frontier_to_basis_dict.items():
            self.frontier_to_basis_dict[frontier_state] = [
                basis_state for basis_state in basis_list
                if not self.states_are_apart(frontier_state, basis_state)
            ]

    def promote_frontier_state(self):
        """
        Promote an isolated frontier (with no basis candidates) to become a new basis state.
        An isolated frontier represents a newly discovered distinct state.
        """
        for iso_frontier_state, basis_list in self.frontier_to_basis_dict.items():
            if not basis_list:
                # This frontier is distinct from all existing basis states
                new_basis = iso_frontier_state
                self.basis.append(new_basis)
                self.frontier_to_basis_dict.pop(new_basis)

                # Add new basis as candidate for compatible frontiers
                for frontier_state, candidate_list in self.frontier_to_basis_dict.items():
                    if not self.states_are_apart(new_basis, frontier_state):
                        candidate_list.append(new_basis)

                # Track if any goto node becomes a basis state
                if isinstance(new_basis, MealyGotoNode):
                    self.goto_is_in_basis = True
                break

    def check_frontier_consistency(self):
        """
        Ensure all basis state successors are tracked.
        Any successor that isn't a basis state or existing frontier becomes a new frontier.
        """
        for basis_state in self.basis:
            for inp in self.alphabet:
                maybe_frontier = basis_state.get_successor(inp)
                
                # Skip if undefined, already basis, or already frontier
                if maybe_frontier is None:
                    continue
                if maybe_frontier in self.basis:
                    continue
                if maybe_frontier in self.frontier_to_basis_dict:
                    continue

                # Register as new frontier with compatible basis candidates
                self.frontier_to_basis_dict[maybe_frontier] = [
                    basis for basis in self.basis
                    if not self.states_are_apart(basis, maybe_frontier)
                ]

    def is_observation_tree_adequate(self):
        """
        Check if the tree is ready for hypothesis construction.
        
        Requirements:
        1. Each frontier maps to exactly one basis state (fully identified)
        2. All basis states have defined outputs/transitions for all inputs
        """
        self.check_frontier_consistency()
        
        # Check all frontiers are identified (single candidate)
        for _, basis_list in self.frontier_to_basis_dict.items():
            if len(basis_list) != 1:
                return False

        # Check all basis states are complete (all inputs defined)
        for basis_state in self.basis:
            for inp in self.alphabet:
                if self.automaton_type == 'mealy':
                    if basis_state.get_output(inp) is None:
                        return False
                else:
                    if basis_state.get_successor(inp) is None:
                        return False

        return True
    
    # =========================================================================
    # Frontier Exploration and Extension
    # =========================================================================

    def make_basis_complete(self):
        """Ensure all basis states have transitions for all inputs"""
        for basis_state in self.basis:
            for inp in self.alphabet:
                if basis_state.get_successor(inp) is None:
                    self.explore_frontier(basis_state, inp)

    def find_basis_candidates(self, new_frontier):
        """Find all basis states that could potentially be equivalent to this frontier"""
        return {
            basis for basis in self.basis
            if not self.states_are_apart(basis, new_frontier)
        }

    def explore_frontier(self, basis_state, inp):
        """
        Explore a new transition from a basis state.
        
        This is called when a basis state doesn't have a defined transition for
        some input. We query the SUL to discover the output and resulting state.
        
        Steps:
        1. Build access sequence to the new state (basis access + inp)
        2. Query SUL to get the output
        3. Extend tree with new frontier node
        4. Register frontier's basis candidates
        5. Apply extension rule (ADS or SepSeq) to gather distinguishing info
        
        Args:
            basis_state: The basis state to extend from
            inp: The input symbol to explore
        """
        # Build access sequence to the new state
        inputs = self.tree.get_access_sequence(basis_state) + [inp]
        # For Mealy: preprocess to handle retry/goto outputs in the path
        inputs = self.tree._inferred_preparse_access_sequence(inputs)

        self.sul.start_query()
        output = self.sul.steps(inputs)[-1]
        frontier_state = self.tree.extend_and_get(basis_state, inp, output)

        # Register frontier with its compatible basis candidates
        self.frontier_to_basis_dict[frontier_state] = self.find_basis_candidates(frontier_state)

        # For Mealy: handle special outputs that create inferred subtrees
        if self.automaton_type == 'mealy':
            frontier_state = self._inferred_try_extend_frontier_exploration(frontier_state)

        # Apply extension rule to gather distinguishing information
        # This helps identify the frontier faster by pre-emptively querying
        # sequences that separate basis states
        if self.extension_rule == "ADS":
            self._extend_with_ads(frontier_state)
        elif self.extension_rule == "SepSeq" and len(self.basis) > 1:
            self._extend_with_sepseq(frontier_state)

        self.sul.end_query()

    def _extend_with_ads(self, frontier_state):
        """
        Extend frontier using Adaptive Distinguishing Sequence (ADS).
        
        An ADS is a decision tree that determines which basis state a frontier
        is equivalent to by adaptively choosing inputs based on observed outputs.
        """
        ads = Ads(self.tree, self.basis)
        current_state = frontier_state
        
        # Check how much of the ADS is already in the tree
        known_inputs, ads_in_tree = self._get_ads_sequence_contained_in_tree(ads, frontier_state)

        while not ads_in_tree:
            # Follow known path in tree
            if known_inputs:
                output = self.sul.steps(known_inputs)[-1]
            else: 
                output = None
            current_state = self.tree.get_destination_node_from(current_state, known_inputs)
            
            # Adaptively query the rest of the ADS
            current_state = self.adaptive_query_extension(ads, current_state, output)
            output = current_state.parent.get_output(current_state.input_to_parent)
            
            # Check again how much is now in tree
            known_inputs, ads_in_tree = self._get_ads_sequence_contained_in_tree(ads, current_state, output)

    def _extend_with_sepseq(self, frontier_state):
        """
        Extend frontier using Separating Sequence (SepSeq).
        
        A separating sequence (witness) is a fixed input sequence that produces
        different outputs from two states, proving they are distinct.
        """
        basis_candidates = list(self.frontier_to_basis_dict[frontier_state])
        if len(basis_candidates) < 2:
            return  # Already identified - only one candidate

        # Get a separating sequence between two candidates
        witness = self.get_or_compute_witness(basis_candidates[0], basis_candidates[1])
        current_state = frontier_state
        
        # Check how much of the witness is already in the tree
        known_inputs = witness[:len(self.tree.get_outputs_partial(frontier_state, witness))]
        witness_in_tree = (len(known_inputs) == len(witness))
        witness = witness[len(known_inputs):]
        
        while not witness_in_tree:
            # Follow known path in tree
            if known_inputs:
                self.sul.steps(known_inputs)
                current_state = self.tree.get_destination_node_from(current_state, known_inputs)

            # Query remaining witness inputs one at a time
            i = 0
            while i < len(witness):
                output = self.sul.single_step(witness[i])
                current_state = self.tree.extend_and_get(current_state, witness[i], output)
                
                # Stop early if we hit an inferred subtree (Mealy special outputs)
                if current_state.has_inferred_subtree:
                    break
                i += 1
            
            # Update for next iteration
            witness = witness[i:]
            known_inputs = witness[:len(self.tree.get_outputs_partial(current_state, witness))]
            witness_in_tree = (len(known_inputs) == len(witness))
            witness = witness[len(known_inputs):]

    def _inferred_try_extend_frontier_exploration(self, current_state):
        """
        Handle exploration past inferred subtree nodes in Mealy machines.
        
        When we reach a special output (retry/goto), we may need to continue
        exploring to find a "real" frontier state to work with.
        """
        while isinstance(current_state, (MealyRetryLeaf, MealyGotoNode)):
            # Get the actual state the SUL is in
            actual_state = self.tree._get_actual_state_for_inferred(current_state)

            # For Goto nodes: if the goto target isn't a basis state yet,
            # treat it as a normal frontier (don't try to extend through it)
            if isinstance(current_state, MealyGotoNode) and not self.goto_is_in_basis:
                break
            
            # Find an unexplored input from the actual state
            extension_input = self.tree._find_unexplored_input(actual_state)
            
            if extension_input is None:
                # All inputs explored - pick a random regular successor
                return self._select_random_regular_frontier(actual_state)

            # Query the unexplored input and extend the tree
            extension_output = self.sul.single_step(extension_input)
            current_state = self.tree.extend_and_get(current_state, extension_input, extension_output)
            
            # Register the new frontier with its basis candidates
            self.frontier_to_basis_dict[current_state] = self.find_basis_candidates(current_state)

        return current_state

    def _select_random_regular_frontier(self, state):
        """
        Select a random non-inferred successor and navigate to it.
        """
        # Find all successors that are not inferred subtree nodes
        regular_frontiers = [
            state.get_successor(inp) for inp in state.successors.keys()
            if not state.get_successor(inp).has_inferred_subtree
        ]
        
        if not regular_frontiers:
            raise RuntimeError(
                "Frontier state only has inferred subtree successors, cannot extend further."
            )
        
        # Pick one randomly and step the SUL to it
        choice_state = random.choice(regular_frontiers)
        self.sul.single_step(choice_state.input_to_parent)
        return choice_state

    def _get_ads_sequence_contained_in_tree(self, ads, from_node, prev_output=None):
        """
        Determine how much of an ADS path is already in the observation tree.
        """
        input_sequence = []
        current_node = from_node
        next_input = ads.next_input(prev_output)

        while next_input is not None:
            # Check if this input's successor exists in tree
            successor_from_node = current_node.get_successor(next_input)
            if successor_from_node is None:
                # ADS path goes beyond what's in the tree
                ads.to_parent()  # Reset ADS position for later continuation
                return input_sequence, False
            
            # Get output for this transition
            if self.automaton_type == 'mealy':
                output_from_node = current_node.get_output(next_input)
            else:
                output_from_node = successor_from_node.output

            # Move to next position
            prev_output = output_from_node
            current_node = successor_from_node
            input_sequence.append(next_input)

            next_input = ads.next_input(prev_output)

        # Reached end of ADS path - entire sequence is in tree
        return input_sequence, True
    
    def adaptive_query_extension(self, ads, from_node, last_output=None):
        """
        Query the SUL following an Adaptive Distinguishing Sequence.
        """
        outputs_received = []
        current_state = from_node

        # Query the SUL and extend the tree following ADS
        next_input = ads.next_input(last_output)
        while next_input is not None:
            if next_input is tuple():  # Empty tuple = check current state (DFA/Moore)
                if outputs_received:
                    last_output = outputs_received[-1]
                else:
                    # Query empty step to get current state's output
                    last_output = self.sul.single_step(None)
            else:
                # Normal input - query SUL and record output
                output = self.sul.single_step(next_input)
                outputs_received.append(output)
                last_output = output

            # Extend tree with this observation
            current_state = self.tree.extend_and_get(current_state, next_input, last_output)

            # Stop if we hit an inferred subtree (Mealy crash/retry/goto)
            if current_state.has_inferred_subtree:
                return current_state
            
            # Get next input from ADS based on observed output
            next_input = ads.next_input(last_output)

        return current_state

    def get_or_compute_witness(self, state_one, state_two):
        """
        Get a separating sequence (witness) between two states.
        """
        # Use canonical ordering for cache key to ensure (a,b) == (b,a)
        if state_one.id < state_two.id:
            pair = (state_one.id, state_two.id)
        else:
            pair = (state_two.id, state_one.id)

        if pair in self.witness_cache:
            return self.witness_cache[pair]

        # Compute witness using apartness relation
        witness = Apartness.compute_witness(state_one, state_two, self.tree)
        self.witness_cache[pair] = witness
        return witness

    # =========================================================================
    # Frontier Identification
    # =========================================================================

    def make_frontiers_identified(self):
        """Reduce each frontier's basis candidates to exactly one"""
        for frontier_state in self.frontier_to_basis_dict:
            self.identify_frontier(frontier_state)

    def identify_frontier(self, frontier_state):
        """
        Reduce basis candidates for a frontier by querying a separating sequence.
        Uses either SepSeq or ADS strategy based on separation_rule.
        """
        if frontier_state not in self.frontier_to_basis_dict:
            raise Exception(f"Warning: {frontier_state} not found in frontier_to_basis_dict.")

        self.update_basis_candidates(frontier_state)
        old_candidate_size = len(self.frontier_to_basis_dict[frontier_state])

        if old_candidate_size < 2:
            return  # Already identified or isolated

        # Choose separation strategy
        if self.separation_rule == "SepSeq" or old_candidate_size == 2:
            self._identify_frontier_sepseq(frontier_state)
        else:
            self._identify_frontier_ads(frontier_state)

        self.update_basis_candidates(frontier_state)

        if len(self.frontier_to_basis_dict[frontier_state]) == old_candidate_size:
            raise RuntimeError("Identification did not reduce candidates")

    def _identify_frontier_sepseq(self, frontier_state):
        """Identify frontier using separating sequence between two candidates"""
        basis_candidates = self.frontier_to_basis_dict[frontier_state]
        basis_one = basis_candidates[0]
        basis_two = basis_candidates[1]

        # Query the frontier state with the witness between two candidates
        witness = self.get_or_compute_witness(basis_one, basis_two)
        inputs = self.tree.get_access_sequence(frontier_state) + witness
        inputs = self.tree._inferred_preparse_access_sequence(inputs)

        outputs = self.sul.query(inputs)
        self.tree.insert_observation(inputs, outputs)

    def _identify_frontier_ads(self, frontier_state):
        """Identify frontier using Adaptive Distinguishing Sequence"""
        access_inputs = self.tree.get_access_sequence(frontier_state)

        # Build ADS for the basis candidates of this frontier
        basis_candidates = self.frontier_to_basis_dict[frontier_state]
        ads = Ads(self.tree, basis_candidates)

        current_state = self.tree.root
        known_inputs, ads_in_tree = self._get_ads_sequence_contained_in_tree(ads, frontier_state)

        if not ads_in_tree:
            self.sul.start_query()

            known_flag = (len(known_inputs) > 0)
            access_inputs = access_inputs + known_inputs
            known_inputs = self.tree._inferred_preparse_access_sequence(access_inputs)

            output = self.sul.steps(known_inputs)[-1]
            if not known_flag:
                output = None

            current_state = self.tree.get_destination_node_from(current_state, known_inputs)
            current_state = self.adaptive_query_extension(ads, current_state, output)
            output = current_state.parent.get_output(current_state.input_to_parent)
            known_inputs, ads_in_tree = self._get_ads_sequence_contained_in_tree(ads, current_state, output)

            # Continue until ADS is fully explored
            while not ads_in_tree:
                if known_inputs:
                    output = self.sul.steps(known_inputs)[-1]
                else: 
                    output = None
                current_state = self.tree.get_destination_node_from(current_state, known_inputs)
                current_state = self.adaptive_query_extension(ads, current_state, output)
                output = current_state.parent.get_output(current_state.input_to_parent)
                known_inputs, ads_in_tree = self._get_ads_sequence_contained_in_tree(ads, current_state, output)

            self.sul.end_query()

    # =========================================================================
    # Hypothesis Construction
    # =========================================================================

    def construct_hypothesis_states(self):
        """
        Create hypothesis automaton states from basis states.
        """
        self.states_dict = {}
        state_counter = 0

        for basis_state in self.basis:
            state_id = f's{state_counter}'
            
            if self.automaton_type == 'dfa':
                self.states_dict[basis_state] = DfaState(state_id)
                self.states_dict[basis_state].is_accepting = basis_state.output
            elif self.automaton_type == 'moore':
                self.states_dict[basis_state] = MooreState(state_id, output=basis_state.output)
            else:  # mealy
                self.states_dict[basis_state] = MealyState(state_id)
                
            state_counter += 1

    def construct_hypothesis_transitions(self):
        """
        Create transitions between hypothesis states.
        """
        for basis_state in self.basis:
            for input_val in self.alphabet:
                successor = basis_state.get_successor(input_val)
                
                # Resolve frontier states to their basis candidate
                if successor in self.frontier_to_basis_dict:
                    candidates = self.frontier_to_basis_dict[successor]
                    if len(candidates) > 1:
                        raise RuntimeError(
                            "Multiple basis candidates for frontier - tree not adequate"
                        )
                    successor = next(iter(candidates))
                    
                if successor not in self.states_dict:
                    raise RuntimeError(
                        "Successor not in states_dict - tree structure error"
                    )

                # Create the transition
                destination = self.states_dict[successor]
                self.states_dict[basis_state].transitions[input_val] = destination
                
                # For Mealy: also set the output function
                if self.automaton_type == 'mealy':
                    self.states_dict[basis_state].output_fun[input_val] = basis_state.get_output(input_val)

    def construct_hypothesis(self):
        """
        Build complete hypothesis automaton from current tree state.
        """
        self.construct_hypothesis_states()
        self.construct_hypothesis_transitions()

        # Create the appropriate automaton type
        automaton_class = {'dfa': Dfa, 'mealy': MealyMachine, 'moore': MooreMachine}
        hypothesis = automaton_class[self.automaton_type](
            self.states_dict[self.tree.root],  # Root becomes initial state
            list(self.states_dict.values())
        )
        
        # Compute useful metadata for equivalence checking
        hypothesis.compute_prefixes()
        hypothesis.characterization_set = hypothesis.compute_characterization_set(raise_warning=False)

        return hypothesis

    def build_hypothesis(self):
        """
        Main learning loop: iteratively build and refine hypothesis.
        """
        while True:
            # Step 1: Ensure tree is adequate for hypothesis construction
            self.make_observation_tree_adequate()
            
            # Step 2: Build hypothesis from current tree state
            hypothesis = self.construct_hypothesis()
            
            # Step 3: Check for inconsistency between tree and hypothesis
            counter_example = Apartness.compute_witness_in_tree_and_hypothesis_states(
                self.tree, self.tree.root, hypothesis.initial_state
            )

            if not counter_example:
                # No inconsistency - hypothesis is valid for current tree
                return hypothesis

            # Step 4: Process the internal counterexample to refine tree
            cex_outputs = self.tree.get_observation(counter_example)
            self.process_counter_example(hypothesis, counter_example, cex_outputs)

    def make_observation_tree_adequate(self):
        """
        Refine tree until it's ready for hypothesis construction.
        """
        self.update_frontier_and_basis()
        while not self.is_observation_tree_adequate():
            self.make_basis_complete()      # Explore missing transitions
            self.make_frontiers_identified() # Reduce ambiguous frontiers
            self.promote_frontier_state()    # Promote any newly isolated frontiers

    # =========================================================================
    # Counterexample Processing
    # =========================================================================

    def process_counter_example(self, hypothesis, cex_inputs, cex_outputs):
        """
        Process a counterexample to refine the observation tree.
        """
        # Step 1: Add the counterexample to our observation tree
        self.tree.insert_observation(cex_inputs, cex_outputs)
        
        # Step 2: Get hypothesis outputs and find divergence point
        hyp_outputs = hypothesis.compute_output_seq(
            hypothesis.initial_state, cex_inputs)
        prefix_index = self._get_counter_example_prefix_index(
            cex_outputs, hyp_outputs)
        
        # Step 3: Use binary search on the prefix where divergence occurs
        self._process_binary_search(
            hypothesis, cex_inputs[:prefix_index], cex_outputs[:prefix_index])

    def _get_counter_example_prefix_index(self, cex_outputs, hyp_outputs):
        """
        Find the index where counterexample and hypothesis outputs first differ.
        """
        for index in range(len(cex_outputs)):
            if cex_outputs[index] != hyp_outputs[index]:
                return index
        raise RuntimeError("counterexample and hypothesis outputs are equal")

    def _process_binary_search(self, hypothesis, cex_inputs, cex_outputs):
        """
        Use binary search to find a witness from a counterexample.
        """
        # Get the tree node reached by the counterexample
        tree_node = self.tree.get_destination_node(cex_inputs)
        self.update_frontier_and_basis()

        # If tree_node is already tracked, no further processing needed
        if tree_node in self.frontier_to_basis_dict or tree_node in self.basis:
            return

        # Find the corresponding hypothesis state and its tree node
        hyp_state = self._get_automaton_successor(
            hypothesis, hypothesis.initial_state, cex_inputs)
        hyp_node = list(self.states_dict.keys())[list(
            self.states_dict.values()).index(hyp_state)]

        # Find the longest prefix that reaches a known frontier or basis state
        prefix = []
        current_state = self.tree.root
        for input in cex_inputs:
            if current_state in self.frontier_to_basis_dict:
                break
            current_state = current_state.get_successor(input)
            prefix.append(input)

        # Binary search: split counterexample in half
        h = (len(prefix) + len(cex_inputs)) // 2
        sigma1 = list(cex_inputs[:h])  # First half
        sigma2 = list(cex_inputs[h:])  # Second half

        # Get the hypothesis state after sigma1 and find its tree representation
        hyp_state_p = self._get_automaton_successor(
            hypothesis, hypothesis.initial_state, sigma1)
        hyp_node_p = list(self.states_dict.keys())[list(
            self.states_dict.values()).index(hyp_state_p)]
        hyp_p_access = self.tree.get_transfer_sequence(self.tree.root, hyp_node_p)

        # Compute witness between tree_node and hypothesis node
        witness = Apartness.compute_witness(tree_node, hyp_node, self.tree)
        if witness is None:
            raise RuntimeError("Binary search: There should be a witness")

        # Query: access_to_hyp_state_p + sigma2 + witness
        query_inputs = hyp_p_access + sigma2 + witness
        query_outputs = self.sul.query(query_inputs)

        self.tree.insert_observation(query_inputs, query_outputs)

        # Get the tree node after sigma1
        tree_node_p = self.tree.get_destination_node(sigma1)

        # Check if we can now distinguish tree_node_p from hyp_node_p
        witness_p = Apartness.compute_witness(tree_node_p, hyp_node_p, self.tree)

        if witness_p is not None:
            # Distinguishing behavior is in the first half - recurse on sigma1
            self._process_binary_search(hypothesis, sigma1, cex_outputs[:h])
        else:
            # Distinguishing behavior is in the second half - recurse on sigma2
            new_inputs = list(hyp_p_access) + sigma2
            self._process_binary_search(
                hypothesis, new_inputs, query_outputs[:len(new_inputs)])

    def _get_automaton_successor(self, automaton, from_state, inputs):
        """
        Simulate the automaton on an input sequence and return final state.
        """
        automaton.current_state = from_state
        for inp in inputs:
            automaton.current_state = automaton.current_state.transitions[inp]

        return automaton.current_state

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_tree_size(self):
        """Returns the total number of nodes in the observation tree"""
        return self.tree.get_tree_size()
    
    def get_size(self):
        """Returns the number of basis states (for compatibility)"""
        return len(self.basis)
    
    def states_are_apart(self, state_one, state_two):
        """Check if two states are apart using the apartness relation. First see if they do not represent the same node via inferred subtree."""
        if self.tree.nodes_represent_same_state_through_inferred(state_one, state_two):
            return False
        
        return Apartness.states_are_apart(state_one, state_two, self.tree)
