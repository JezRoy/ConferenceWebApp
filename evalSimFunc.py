import multiprocessing
import gc

def calculate_delegate_score(delegate_preferences, schedule):
    total_preferred_talks = len(delegate_preferences)
    attended_talks = []

    # Check if each preferred talk can be attended without conflicts
    for time_slot, talks in schedule.items():
        for talk in talks:
            if talk[0] == delegate_preferences[1] and delegate_preferences[1] not in attended_talks:
                attended_talks.append(delegate_preferences[1])
    
    # Calculate the percentage of preferred talks attended
    attended_percentage = len(attended_talks) / total_preferred_talks

    return 1 if attended_percentage >= 0.8 else 0

def calculate_schedule_score_parallel(schedule, deleg_likes_talks):
    total_score = multiprocessing.Value('i', 0)

    def update_total_score(result):
        with total_score.get_lock():
            total_score.value += result

    # Limit the number of processes based on available CPU cores
    num_processes = multiprocessing.cpu_count() // 2  # Use half of available CPU cores
    pool = multiprocessing.Pool(processes=num_processes)

    batch_size = 100  # Adjust batch size based on available memory and CPU capacity
    num_batches = (len(deleg_likes_talks) + batch_size - 1) // batch_size

    for i in range(num_batches):
        batch_start = i * batch_size
        batch_end = min((i + 1) * batch_size, len(deleg_likes_talks))
        batch_delegates = deleg_likes_talks[batch_start:batch_end]

        for deleg in batch_delegates:
            pool.apply_async(calculate_delegate_score, args=(deleg, schedule), callback=update_total_score)

        # Explicitly invoke garbage collection to release memory occupied by processed batches
        gc.collect()

    pool.close()
    pool.join()

    return total_score.value

# Example usage
sample_schedule = {
    1: [(1, "Parameterized Matroid-Constrained Maximum Coverage"), (2, "Sorting Finite Automata via Partition Refinement")],
    2: [(3, "Lyndon Arrays in Sublinear Time"), (4, "Linear Time Construction of Cover Suffix Tree and Applications")]
    # Add more time slots with scheduled talks
}

sample_deleg_likes_talks = [
    [1, 2, 9], [1, 3, 5], [1, 4, 4], [1, 5, 9], [1, 1, 10], 
    [2, 2, 2], [2, 3, 6], [2, 5, 1], 
    [3, 2, 8], [3, 3, 8], [3, 5, 10], 
    [4, 2, 3], [4, 3, 9], [4, 5, 5], 
    [5, 2, 8], [5, 3, 4], [5, 5, 5], 
    [6, 2, 10], [6, 4, 4], [6, 3, 7], [6, 5, 5], 
    [7, 2, 3], [7, 2, 8], [7, 3, 3], [7, 5, 5]
]

score = calculate_schedule_score_parallel(sample_schedule, sample_deleg_likes_talks)
print("Schedule Score:", score)
