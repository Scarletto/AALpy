AUTOMATON_TYPES = ['dfa', 'mealy', 'moore']


# =============================================================================
# Tree Node Classes
# =============================================================================

class MooreNode:
    """
    Node in the observation tree for Moore/DFA machines.
    Output is associated with the state (node) itself.
    """
    _id_counter = 0
    __slots__ = ['id', 'output', 'successors', 'parent', 'input_to_parent', 'has_inferred_subtree']

    def __init__(self, parent=None):
        MooreNode._id_counter += 1
        self.id = MooreNode._id_counter
        self.output = None
        self.successors = {}  # input -> successor node
        self.parent = parent
        self.input_to_parent = None  # input that led from parent to this node
        self.has_inferred_subtree = False  # Always False for Moore/DFA (no inferred subtrees)

    def __hash__(self):
        return hash(self.id)

    def add_successor(self, input_val, output_val, successor_node):
        """Add a successor node and set its output"""
        self.successors[input_val] = successor_node
        self.successors[input_val].output = output_val

    def get_successor(self, input_val):
        """Returns the successor node for the given input, or None"""
        return self.successors.get(input_val)

    def extend_and_get(self, inp, output):
        """Get existing successor or create new one with given output"""
        if inp in self.successors:
            return self.successors[inp]
        successor_node = MooreNode(parent=self)
        self.add_successor(inp, output, successor_node)
        successor_node.input_to_parent = inp
        return successor_node


class MealyNode:
    """
    Node in the observation tree for Mealy machines.
    Output is associated with transitions (edges), not states.
    """
    _id_counter = 0
    __slots__ = ['id', 'successors', 'parent', 'input_to_parent', 'has_inferred_subtree']

    def __init__(self, parent=None):
        MealyNode._id_counter += 1
        self.id = MealyNode._id_counter
        self.successors = {}  # input -> (output, successor node)
        self.parent = parent
        self.input_to_parent = None
        self.has_inferred_subtree = False  # True for special leaf nodes

    def __hash__(self):
        return hash(self.id)

    def add_successor(self, input_val, output_val, successor_node):
        """Add a successor with its associated output"""
        self.successors[input_val] = (output_val, successor_node)

    def get_successor(self, input_val):
        """Returns the successor node for the given input, or None"""
        if input_val in self.successors:
            return self.successors[input_val][1]
        return None

    def get_output(self, input_val):
        """Returns the output for the given input transition, or None"""
        if input_val in self.successors:
            return self.successors[input_val][0]
        return None


# =============================================================================
# Special Mealy Node Types for Inferred Subtrees
# These handle outputs that indicate special behavior (crash, retry, goto)
# =============================================================================

class MealyCrashLeaf(MealyNode):
    """
    Leaf node representing a crash state - all transitions loop back to itself.
    Once the system crashes, it stays crashed regardless of input.
    """
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.has_inferred_subtree = True
    
    def add_successor(self, input_val, output_val, successor_node):
        pass  # Cannot add successors to a crash state
    
    def get_successor(self, input_val):
        return self  # All inputs loop back
    
    def get_output(self, input_val):
        return self.parent.get_output(self.input_to_parent)  # Same crash output


class MealyRetryLeaf(MealyNode):
    """
    Leaf node representing a retry - transitions are delegated to parent.
    The retry output indicates the previous input had no effect.
    """
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.has_inferred_subtree = True
    
    def add_successor(self, input_val, output_val, successor_node):
        # Delegate to parent - retry means we're still at parent's state
        successor_node.parent = self.parent
        return self.parent.add_successor(input_val, output_val, successor_node)
    
    def get_successor(self, input_val):
        return self.parent.get_successor(input_val)
    
    def get_output(self, input_val):
        return self.parent.get_output(input_val)

    
class MealyGotoNode(MealyNode):
    """Base class for goto nodes - represents a jump to another state."""
    def __init__(self, parent, representing_node):
        super().__init__(parent=parent)
        self.has_inferred_subtree = True
        self.representing_node = representing_node  # The actual state this represents

    
class MealyGotoSourceNode(MealyGotoNode):
    """First occurrence of a goto output - this becomes the canonical state."""
    def __init__(self, parent):
        super().__init__(parent=parent, representing_node=self)


class MealyGotoLeaf(MealyGotoNode):
    """
    Subsequent occurrences of a goto output - delegates to the source node.
    All goto leaves with the same output share the same representing_node.
    """
    def __init__(self, parent, representing_node):
        super().__init__(parent=parent, representing_node=representing_node)

    def add_successor(self, input_val, output_val, successor_node):
        successor_node.parent = self.representing_node
        return self.representing_node.add_successor(input_val, output_val, successor_node)
    
    def get_successor(self, input_val):
        return self.representing_node.get_successor(input_val)
    
    def get_output(self, input_val):
        return self.representing_node.get_output(input_val)


# =============================================================================
# Observation Tree
# =============================================================================

class ObservationTree:
    """
    Core observation tree for learning deterministic automata (DFA, Moore, Mealy).
    
    This class handles the basic tree structure for storing input/output observations.
    It provides methods for:
    - Extending the tree with new observations
    - Navigating the tree (access sequences, destination nodes)
    - Querying stored observations
    
    Algorithm-specific logic (like L#'s basis/frontier management) should be
    implemented in subclasses.
    """
    
    def __init__(self, alphabet, sul, automaton_type, 
                 crash_output=None, retry_output=None, goto_outputs=[]):
        """
        Initialize the observation tree.
        
        Args:
            alphabet: Set of input symbols
            sul: System Under Learning interface
            automaton_type: 'dfa', 'mealy', or 'moore'
            crash_output: (Mealy only) Output indicating system crash
            retry_output: (Mealy only) Output indicating input had no effect
            goto_outputs: (Mealy only) Outputs indicating jump to another state
        """
        assert automaton_type in AUTOMATON_TYPES
        assert alphabet is not None and sul is not None
        if automaton_type != 'mealy':
            # Inferred subtrees only make sense for Mealy machines
            assert crash_output is None and retry_output is None and not goto_outputs

        self.automaton_type = automaton_type
        self.alphabet = alphabet
        self.sul = sul
        
        # Mealy-specific: special output handling
        self.crash_output = crash_output
        self.retry_output = retry_output
        self.goto_outputs_map = {output: None for output in goto_outputs}

        # Initialize root node
        if self.automaton_type == 'mealy':
            self.root = MealyNode()
        else:
            self.root = MooreNode()
            # For Moore/DFA, query empty word to get initial state output
            self.root.output = self.sul.query([])[0]

    # =========================================================================
    # Tree Extension and Node Access
    # =========================================================================

    def extend_and_get(self, node, input, output):
        """Extend the tree with a new observation or return existing node"""
        if self.automaton_type == 'mealy':
            return self._extend_and_get_mealy(node, input, output)
        else:
            return node.extend_and_get(input, output)
    
    def _extend_and_get_mealy(self, node, input, output):
        """
        Extend a Mealy node with a new transition, handling special outputs.
        
        Special outputs create inferred subtree nodes:
        - crash_output -> MealyCrashLeaf (absorbing state)
        - retry_output -> MealyRetryLeaf (no state change)
        - goto_output -> MealyGotoSourceNode/MealyGotoLeaf (jump to shared state)
        """
        assert self.automaton_type == 'mealy'

        # Check if transition already exists
        if input in node.successors:
            existing_output = node.get_output(input)
            if existing_output != output:
                raise Exception(
                    f"Inconsistent observation: tree has output '{existing_output}', "
                    f"but received '{output}'")
            return node.get_successor(input)
   
        # Create appropriate successor node based on output type
        if output == self.crash_output:
            successor_node = MealyCrashLeaf(parent=node)
            
        elif output == self.retry_output:
            successor_node = MealyRetryLeaf(parent=node)
            
        elif output in self.goto_outputs_map:
            if self.goto_outputs_map[output] is None:
                # First occurrence of this goto output - create source node
                successor_node = MealyGotoSourceNode(parent=node)
                acc_seq = self.get_access_sequence(node) + [input]
                self.goto_outputs_map[output] = {
                    'node': successor_node, 
                    'access_sequence': acc_seq
                }
            else:
                # Subsequent occurrence - create leaf pointing to source
                successor_node = MealyGotoLeaf(
                    parent=node, 
                    representing_node=self.goto_outputs_map[output]['node']
                )
                # Update access sequence if this path is shorter
                acc_seq = self.get_access_sequence(node) + [input]
                if len(self.goto_outputs_map[output]['access_sequence']) > len(acc_seq):
                    self.goto_outputs_map[output]['access_sequence'] = acc_seq
        else:
            # Regular transition
            successor_node = MealyNode(parent=node)

        node.add_successor(input, output, successor_node)
        successor_node.input_to_parent = input
        return successor_node

    # =========================================================================
    # Tree Observation and Query Methods
    # =========================================================================

    def insert_observation(self, inputs, outputs):
        """Insert an input/output sequence into the tree"""
        if len(inputs) != len(outputs):
            raise ValueError("Inputs and outputs must have the same length.")

        current_node = self.root
        for input_val, output_val in zip(inputs, outputs):
            current_node = self.extend_and_get(current_node, input_val, output_val)

    def get_observation(self, inputs):
        """Retrieve the list of outputs based on a given input sequence"""
        current_node = self.root
        observation = []
        for input_val in inputs:
            if self.automaton_type == 'mealy':
                output = current_node.get_output(input_val)
                current_node = current_node.get_successor(input_val)
            else:
                current_node = current_node.get_successor(input_val)
                output = current_node.output
            if output is None:
                return None
            observation.append(output)
        return observation

    def get_destination_node(self, inputs):
        """Retrieve the node corresponding to the given input sequence from root"""
        current_node = self.root
        for input_val in inputs:
            successor_node = current_node.get_successor(input_val)
            if successor_node is None:
                return None
            current_node = successor_node

        return current_node
    
    def get_destination_node_from(self, from_node, inputs):
        """Retrieve the node corresponding to the given input sequence from a specific node"""
        current_node = from_node
        for input_val in inputs:
            successor_node = current_node.get_successor(input_val)
            if successor_node is None:
                return None
            current_node = successor_node

        return current_node

    def get_transfer_sequence(self, from_node, to_node):
        """Get the input sequence that moves from one node to another"""
        transfer_sequence = []
        current_node = to_node

        while current_node != from_node:
            if current_node.parent is None:
                return None
            transfer_sequence.append(current_node.input_to_parent)
            current_node = current_node.parent

        transfer_sequence.reverse()
        return transfer_sequence

    def get_access_sequence(self, to_node):
        """Get the input sequence to reach a specific node from the root"""
        return self.get_transfer_sequence(self.root, to_node)
    
    def get_outputs_partial(self, from_state, inputs):
        """
        Retrieve outputs for an input sequence, stopping early if undefined.
        Returns the longest prefix of outputs that are defined in the tree.
        """
        current_node = from_state
        observation = []
        for input_val in inputs:
            if self.automaton_type == 'mealy':
                output = current_node.get_output(input_val)
                if output is None:
                    break
                current_node = current_node.get_successor(input_val)
            else:
                current_node = current_node.get_successor(input_val)
                if current_node is None or current_node.output is None:
                    break
                output = current_node.output
            observation.append(output)
        return observation

    def get_tree_size(self):
        """Returns the total number of nodes created (for debugging/metrics)"""
        if isinstance(self.root, MealyNode):
            return MealyNode._id_counter
        else:
            return MooreNode._id_counter

    # =========================================================================
    # Mealy-Specific: Inferred Subtree Handling
    # =========================================================================
    #
    # For Mealy machines, certain outputs indicate special state behavior:
    # - crash_output: System crashed, all future inputs return crash
    # - retry_output: Input had no effect, state unchanged
    # - goto_outputs: State jumped to a specific "goto" state
    #
    # These create "inferred subtrees" - parts of the tree we don't need to
    # explore because their behavior is deterministically known from the output.
    # =========================================================================

    def nodes_represent_same_state_through_inferred(self, first, second):
        """
        Check if two subtree nodes represent the same actual state through inferred subtrees.
        
        Two sink nodes: they always represent the same state.
        Two retry nodes: they represent the same state if their parent is the same.
        Retry node, other node: they represent the same state if the retry's parent is the other node.
        Two goto nodes: they represent the same state if their representing_node is the same.
        """
        match (first, second):
            case (MealyCrashLeaf(), MealyCrashLeaf()):
                return True
            
            case (MealyRetryLeaf(), MealyRetryLeaf()):
                return first.parent == second.parent
            case (MealyRetryLeaf(), _):
                return first.parent == second
            case (_, MealyRetryLeaf()):
                return second.parent == first
            
            case (MealyGotoNode(), MealyGotoNode()):
                return first.representing_node == second.representing_node
            
            case _:
                return False


    def _inferred_preparse_access_sequence(self, inputs):
        """
        Preprocess input sequence to handle inferred subtree nodes.
        
        When building an access sequence to query the SUL, we need to account
        for special outputs that change the effective path:
        
        - Retry outputs: Skip these inputs entirely since they didn't change state.
          The SUL is still in the same state as before the retry input.
          
        - Goto outputs: Replace the path so far with the canonical goto state's
          access sequence. All goto outputs for the same target lead to the
          same state, so we use the shortest known path.
        
        Args:
            inputs: Original input sequence (access sequence + extension)
            
        Returns:
            Preprocessed input sequence suitable for SUL queries
        """
        if self.automaton_type != 'mealy':
            return inputs
        
        parsed_inputs = []
        
        # Get outputs for all inputs
        # We only preparse the "known" part of the sequence
        outputs = self.get_outputs_partial(self.root, inputs)

        for i in range(len(outputs)):
            if outputs[i] == self.retry_output:
                # Skip retry - it didn't change state, so skip this input
                continue
            elif outputs[i] in self.goto_outputs_map:
                # Redirect: replace everything so far with goto target's access sequence
                parsed_inputs.clear()
                parsed_inputs.extend(self.goto_outputs_map[outputs[i]]['access_sequence'])
            else:
                # Normal output - keep the input
                parsed_inputs.append(inputs[i])

        # Append the remaining inputs (extension part that wasn't preparsed)
        parsed_inputs.extend(inputs[len(outputs):])

        return parsed_inputs

    def _get_actual_state_for_inferred(self, inferred_state):
        """
        Get the actual tree node that an inferred subtree node represents.
        
        For retry nodes: the parent (since retry means no state change)
        For goto leaves: the representing_node (the canonical goto target)
        For goto source: itself (it is the canonical target)
        """
        if isinstance(inferred_state, MealyGotoLeaf):
            return inferred_state.representing_node
        elif isinstance(inferred_state, MealyGotoNode):
            return inferred_state
        else:  # MealyRetryLeaf
            return inferred_state.parent

    def _find_unexplored_input(self, state):
        """Find the first input that hasn't been explored from this state"""
        for input_val in self.alphabet:
            if state.get_successor(input_val) is None:
                return input_val
        return None

