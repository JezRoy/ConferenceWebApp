
                

# Constraint - each talk is scheduled once
                for tk in range(numOfTalks):
                    print(tk, range(ConferenceData[8]))
                    SchedulePt1model += pulp.lpSum(ScheduleVars[s, tk] for s in range(ConferenceData[8])) <= 1, f"EachTalkOnce_{tk}"


                # Constraint - one talk per time slot
                for s in range(ConferenceData[8]):
                    for t in range(ConferenceData[6]):
                        SchedulePt1model += pulp.lpSum(ScheduleVars[ss, t] for ss in range(ConferenceData[8])) <= 1, f"OneTalkPerSlot_{s}_{t}"
                
                # Solve this assignment model
                SchedulePt1model.solve()

                # Print the schedule
                for s in range(ConferenceData[8]):
                    print(f"Session {s+1}:")
                    for t in range(ConferenceData[6]):
                        if pulp.value(ScheduleVars[s, t]) == 1:
                            print(f"  Talk {t+1}")