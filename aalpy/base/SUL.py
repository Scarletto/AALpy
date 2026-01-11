from abc import ABC, abstractmethod

from aalpy.base.CacheTree import CacheTree, CacheDict


class SUL(ABC):
    """
    System Under Learning (SUL) abstract class. Defines the interaction between the learning algorithm and the system
    under learning. All systems under learning have to implement this class, as it is
    passed to the learning algorithm and the equivalence oracle.
    """

    def __init__(self):
        self.num_queries = 0
        self.num_steps = 0
        self.num_cached_queries = 0
        self.num_inferred_outputs = 0
        self.num_inferred_outputs_end_of_query = 0
        self.output_tracker = []

    def query(self, word: tuple) -> list:
        """
        Performs a membership query on the SUL. Before the query, pre() method is called and after the query post()
        method is called. Each letter in the word (input in the input sequence) is executed using the step method.

        Args:

            word: membership query (word consisting of letters/inputs)

        Returns:

            list of outputs, where the i-th output corresponds to the output of the system after the i-th input

        """
        self.pre()
        # Empty string for DFA
        if len(word) == 0:
            out = [self.step(None)]
        else:
            out = [self.step(letter) for letter in word]
        self.post()
        self.num_queries += 1
        self.num_steps += len(word)
        for o in out:
            if o == " 221" or o == " 500":
                self.num_inferred_outputs += 1
        if out and (out[-1] == " 221" or out[-1] == " 500"):
            self.num_inferred_outputs_end_of_query += 1
        return out

    def io_query(self, word : tuple):
        return list(zip(word, self.query(word)))
    
    def start_query(self):
        self.pre()
        self.num_queries += 1

    def end_query(self):
        if self.output_tracker and (self.output_tracker[-1] == " 221" or self.output_tracker[-1] == " 500"):
            self.num_inferred_outputs_end_of_query += 1
        self.output_tracker = []
        self.post()

    def single_step(self, letter):
        """
        Executes a single input on the SUL using the step method. Does not clean anything (no pre() or post() call).

        Args:

            letter: single input

        Returns:

            output received after executing the input

        """
        out = self.step(letter)
        self.num_steps += 1
        # if out == " 221" or out == " 500":
        #     self.num_inferred_outputs += 1
        # self.output_tracker.append(out)
        return out
    
    def steps(self, word):
        """
        Executes a sequence of inputs on the SUL using the step method. Does not clean anything (no pre() or post() call).

        Args:

            word: sequence of inputs

        Returns:

            list of outputs, where the i-th output corresponds to the output of the system after the i-th input

        """
        if len(word) == 0:
            out = [self.step(None)]
        else:
            out = [self.step(letter) for letter in word]
        self.num_steps += len(word)
        for o in out:
            if o == " 221" or o == " 500":
                self.num_inferred_outputs += 1
        self.output_tracker.extend(out)
        return out

    @abstractmethod
    def pre(self):
        """
        Resets the system. Called after post method in the equivalence query.
        """
        pass

    @abstractmethod
    def post(self):
        """
        Performs additional cleanup on the system in necessary. Called before pre method in the equivalence query.
        """
        pass

    @abstractmethod
    def step(self, letter):
        """
        Executes an action on the system under learning and returns its result.

        Args:

            letter: Single input that is executed on the SUL.

        Returns:

            Output received after executing the input.

        """
        pass


class CacheSUL(SUL):
    """
    System under learning that keeps a multiset of all queries in memory.
    This multiset/cache is encoded as a tree.
    """

    def __init__(self, sul: SUL, cache_type='tree'):
        super().__init__()
        self.sul = sul
        self.cache = CacheTree() if cache_type == 'tree' else CacheDict()

    def query(self, word):
        """
        Performs a membership query on the SUL if and only if `word` is not a prefix of any trace in the cache.
        Before the query, pre() method is called and after the query post()
        method is called. Each letter in the word (input in the input sequence) is executed using the step method.

        Args:

            word: membership query (word consisting of letters/inputs)

        Returns:

            list of outputs, where the i-th output corresponds to the output of the system after the i-th input

        """
        cached_query = self.cache.in_cache(word)
        if cached_query:
            self.num_cached_queries += 1
            return cached_query

        # get outputs using default query method
        out = self.sul.query(word)

        # add input/outputs to tree
        self.cache.reset()
        for i, o in zip(word, out):
            self.cache.step_in_cache(i, o)

        self.num_queries += 1
        self.num_steps += len(word)
        for o in out:
            if o == " 221" or o == " 500":
                self.num_inferred_outputs += 1
        if out and (out[-1] == " 221" or out[-1] == " 500"):
            self.num_inferred_outputs_end_of_query += 1
        return out

    def pre(self):
        """
        Reset the system under learning and current node in the cache tree.
        """
        self.cache.reset()
        self.sul.pre()

    def post(self):
        self.sul.post()

    def step(self, letter):
        """
        Executes an action on the system under learning, adds it to the cache and returns its result.

        Args:

           letter: Single input that is executed on the SUL.

        Returns:

           Output received after executing the input.

        """
        out = self.sul.step(letter)
        self.cache.step_in_cache(letter, out)
        return out
    