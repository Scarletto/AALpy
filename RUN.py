def coffee_Lsharp(extension_rule, separation_rule, use_optimizations):
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

    if use_optimizations:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True, crash_output="F", retry_output="W", goto_outputs=["*"])
    else:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True)

    assert bisimilar(learned_mealy, mealy_machine)

    return info
    
def rsa_Lsharp(extension_rule, separation_rule, use_optimizations):
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

    if use_optimizations:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True, crash_output="Alert Fatal (Unexpected message)", goto_outputs=["ChangeCipherSpec & Finished"])
    else:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True)

    assert bisimilar(learned_mealy, mealy_machine)

    return info

def haraka_Lsharp(extension_rule, separation_rule, use_optimizations):
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

    if use_optimizations:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True, crash_output=" 221", retry_output=" 500")
    else:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True)

    assert bisimilar(learned_mealy, mealy_machine)

    return info

def openssh_Lsharp(extension_rule, separation_rule, use_optimizations):
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

    if use_optimizations:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True, crash_output=" DISCONNECT", retry_output=" CH_NONE")
    else:
        learned_mealy, info = run_Lsharp(input_alphabet, sul_mealy, eq_oracle, automaton_type='mealy', extension_rule=extension_rule, separation_rule=separation_rule, max_learning_rounds=200, print_level=1, return_data=True)

    assert bisimilar(learned_mealy, mealy_machine)

    return info

def get_and_write_results_for_all_parameters(testing_function):
    extension_rules = [None, "SepSeq", "ADS"]
    separation_rules = ["SepSeq", "ADS"]
    optimization_options = [False, True]

    results = []

    for extension_rule in extension_rules:
        for separation_rule in separation_rules:
            for use_optimizations in optimization_options:
                print(f'Testing with extension_rule={extension_rule}, separation_rule={separation_rule}, use_optimizations={use_optimizations}')
                process_info = testing_function(extension_rule, separation_rule, use_optimizations)
                results.append((extension_rule, separation_rule, use_optimizations, process_info))

    # Write results to a file
    with open(f'CRG_results/results_{testing_function.__name__}.txt', 'w') as f:
        for extension_rule, separation_rule, use_optimizations, info in results:
            f.write(f'Extension Rule: {extension_rule}, Separation Rule: {separation_rule}, Use Optimizations: {use_optimizations}\n')
            f.write(f'Learning Rounds: {info["learning_rounds"]}\nLearning Queries: {info["queries_learning"]}\nLearning Steps: {info["steps_learning"]}\nEQ Queries: {info["queries_eq_oracle"]}\nEQ Steps: {info["steps_eq_oracle"]}\nTotal Time: {info["total_time"]:.2f} seconds\nEQ Query Time: {info["eq_oracle_time"]:.2f} seconds\nLearning Time: {info["learning_time"]:.2f} seconds\n\n')

get_and_write_results_for_all_parameters(coffee_Lsharp)
get_and_write_results_for_all_parameters(rsa_Lsharp)
get_and_write_results_for_all_parameters(haraka_Lsharp)
get_and_write_results_for_all_parameters(openssh_Lsharp)