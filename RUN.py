def coffee_Lsharp():
    from aalpy.utils import load_automaton_from_file, bisimilar
    from aalpy.SULs import MealySUL
    from aalpy.oracles import WpMethodEqOracle
    from aalpy.learning_algs import run_Lsharp

    mealy_machine = load_automaton_from_file(f'./DotModels/test_LSharpCRG/coffee_machine.dot', automaton_type='mealy')
    input_alphabet = mealy_machine.get_input_alphabet()

    sul_mealy = MealySUL(mealy_machine)
    eq_oracle = WpMethodEqOracle(input_alphabet, sul_mealy, len(mealy_machine.states))

    # Extension rule options: {None, "SepSeq", "ADS"}
    # Separation rule options: {"SepSeq", "ADS"}

    learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule="ADS", separation_rule="ADS", max_learning_rounds=200, print_level=3, crash_output="F", retry_output="W", goto_outputs=["*"])
    # learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule="ADS", separation_rule="ADS", max_learning_rounds=200, print_level=3)

    assert bisimilar(learned_mealy, mealy_machine)
    
def rsa_Lsharp():
    from aalpy.utils import load_automaton_from_file, bisimilar
    from aalpy.SULs import MealySUL
    from aalpy.oracles import WpMethodEqOracle
    from aalpy.learning_algs import run_Lsharp

    mealy_machine = load_automaton_from_file(f'./DotModels/test_LSharpCRG/RSA_BSAFE_C_4.0.4_server_regular.dot', automaton_type='mealy')
    input_alphabet = mealy_machine.get_input_alphabet()

    sul_mealy = MealySUL(mealy_machine)
    eq_oracle = WpMethodEqOracle(input_alphabet, sul_mealy, len(mealy_machine.states))

    # Extension rule options: {None, "SepSeq", "ADS"}
    # Separation rule options: {"SepSeq", "ADS"}

    learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule="ADS", separation_rule="ADS", max_learning_rounds=200, print_level=1, crash_output="Alert Fatal (Unexpected message)", goto_outputs=["ChangeCipherSpec & Finished"])
    # learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule="ADS", separation_rule="ADS", max_learning_rounds=200, print_level=1)

    assert bisimilar(learned_mealy, mealy_machine)

def haraka_Lsharp():
    from aalpy.utils import load_automaton_from_file, bisimilar
    from aalpy.SULs import MealySUL
    from aalpy.oracles import WpMethodEqOracle
    from aalpy.learning_algs import run_Lsharp

    mealy_machine = load_automaton_from_file(f'./DotModels/test_LSharpCRG/haraka.dot', automaton_type='mealy')
    input_alphabet = mealy_machine.get_input_alphabet()

    sul_mealy = MealySUL(mealy_machine)
    eq_oracle = WpMethodEqOracle(input_alphabet, sul_mealy, len(mealy_machine.states))

    # Extension rule options: {None, "SepSeq", "ADS"}
    # Separation rule options: {"SepSeq", "ADS"}

    #learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=None, separation_rule="ADS", max_learning_rounds=200, print_level=1, crash_output=" 221", retry_output=" 500")
    learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=None, separation_rule="ADS", max_learning_rounds=200, print_level=1)

    assert bisimilar(learned_mealy, mealy_machine)

def openssh_Lsharp():
    from aalpy.utils import load_automaton_from_file, bisimilar
    from aalpy.SULs import MealySUL
    from aalpy.oracles import WpMethodEqOracle
    from aalpy.learning_algs import run_Lsharp

    mealy_machine = load_automaton_from_file(f'./DotModels/test_LSharpCRG/OpenSSH-8.8p1.dot', automaton_type='mealy')
    input_alphabet = mealy_machine.get_input_alphabet()

    sul_mealy = MealySUL(mealy_machine)
    eq_oracle = WpMethodEqOracle(input_alphabet, sul_mealy, len(mealy_machine.states))

    # Extension rule options: {None, "SepSeq", "ADS"}
    # Separation rule options: {"SepSeq", "ADS"}

    # learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=None, separation_rule="ADS", max_learning_rounds=200, print_level=1, crash_output=" 221", retry_output=" 500")
    learned_mealy = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule="SepSeq", separation_rule="ADS", max_learning_rounds=200, print_level=1)

    assert bisimilar(learned_mealy, mealy_machine)


haraka_Lsharp()