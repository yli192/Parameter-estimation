#! /usr/bin/python
import sys

def get_grid_info(network_file):
    """ Get the number of rows, columns, landmarks, and time_steps """
    rows = -1
    columns = -1
    landmarks = -1
    time_steps = -1

    network_file.seek(0) #move the pointer to line 0

    for line in network_file:
        if line.startswith("PositionRow_"):

            if rows == -1:
                lines = line.strip().split(",")
                rows = int(lines[-1])
            line = line.strip().split()
            pos,time_step = line[0].split("_");
            time_steps = max(time_steps, int(time_step)) ##constantly update time_steps
        elif line.startswith("PositionCol_"):
            if columns == -1:
                line = line.strip().split(",")
                columns = int(line[-1])
        elif line.startswith("ObserveLandmark"):
            observation,direction,time_step = line.split()[0].split("_")
            landmarks = max(landmarks, int(observation[-1]));

    return rows, columns, landmarks, time_steps

def calculateCPT(training_name, possible_actions, rows, columns, landmarks):
    training_file = open(training_name)

    #Hold the CPTs for the parameters shared CPTs
    row_cpt = {}
    col_cpt = {}
    landmark_cpt = {}
    wall_cpt = {}

    #Hold the counters used to normalize the CPTs
    move_counters = {} # how many times you have been seen action. This is the denominator for the positionrow and positioncol
    position_counters = {} #how many times that you ahve been into position (i,j), e.g. (1,1), this is the denominartor for wall and landmarks

    #Initialize row and column CPT
    for action in possible_actions:
        #print action
        row_cpt["PositionRow_t=i|PositionRow_t-1=i-1,Action_t-1=" + action] = 0
        row_cpt["PositionRow_t=i|PositionRow_t-1=i+1,Action_t-1=" + action] = 0
        row_cpt["PositionRow_t=i|PositionRow_t-1=i,Action_t-1=" + action] = 0
        col_cpt["PositionCol_t=j|PositionCol_t-1=j-1,Action_t-1=" + action] = 0
        col_cpt["PositionCol_t=j|PositionCol_t-1=j+1,Action_t-1=" + action] = 0
        col_cpt["PositionCol_t=j|PositionCol_t-1=j,Action_t-1=" + action] = 0

        move_counters[action] = 0

    possible_directions = ['N', 'S', 'E', 'W']

    #Initialize wall and landmark CPT
    for direction in possible_directions:
        for i in range(1, rows+1):
            for j in range(1, columns+1):
                position_counters[str(i) + "," + str(j)] = 0
                wall_cpt["ObserveWall_" + direction + "_t|PositionRow_t=" + str(i) + ",PositionCol_t=" + str(j)] = 0
                for landmark in range(1, landmarks+1):
                    landmark_cpt["ObserveLandmark" + str(landmark) + "_" + direction + "_t|PositionRow_t=" + str(i) + ",PositionCol_t=" + str(j)] = 0

    trajectory = -1
    previousRow = -1
    previousCol = -1
    previousAction = ""

    for line in training_file:
        #Line format
        #trajectory time PositionRow PositionCol Action Observations...
        line = line.strip().split()
        for var in line:
            if var.startswith("PositionCol_"):
                var = var.split('=')
                col = int(var[1]) #col is the actual column coordinate

            elif var.startswith("PositionRow_"):
                var = var.split('=')
                row = int(var[1])

            elif var.startswith("Action_"):
                var = var.split('=')
                action = var[1]

            elif var.startswith("ObserveLandmark"):  #make _0 to _t so that the code can actually count it; need to do the same for wall
                landmark = var.split("_")
                landmark_form = landmark[0] + "_" + landmark[1] + "_t|PositionRow_t=" + str(row) + ",PositionCol_t=" + str(col)
                landmark_cpt[landmark_form] = int(landmark_cpt[landmark_form]) + 1 #update the # of occurance of each particular combination of landmark_form in the dict

            elif var.startswith("ObserveWall"):
                wall = var.split("_")
                wall_form = wall[0] + "_" + wall[1] + "_t|PositionRow_t=" + str(row) + ",PositionCol_t=" + str(col)
                wall_cpt[wall_form] = int(wall_cpt[wall_form]) + 1

        # use the local variable row and col to update position_counters as well
        position_counters_form = str(row) + "," + str(col)
        position_counters[position_counters_form] = int(position_counters[position_counters_form]) + 1
        #We have moved on to the next trajectory.  Reset previousRow,
        #previousCol, previousAction; skip time step 0 becasue it doesn't have parents so there is no cpds for that time step

        if trajectory != line[0]: #this is just to store the values in the first time_step of each trajectory as their corresponding previous values so that occurances of i,i+1 or i-1 can accumulate
            trajectory = line[0]
            previousCol = col
            previousRow = row
            previousAction = action
            continue
        rowChange = ""
        #Determine which row case we are in, look at page 6 for equations, row=the current row
        if row == previousRow:
            rowChange = 'i'
        elif (row - 1 == previousRow) or (row == 1 and previousRow == rows):
            rowChange = 'i-1'
        elif (row + 1 == previousRow) or (row == rows and previousRow == 1):
            rowChange = 'i+1'

        colChange = ""
        if col == previousCol:
            colChange = 'j'
        elif (col - 1 == previousCol) or (col == 1 and previousCol == columns):
            colChange = 'j-1'
        elif (col + 1 == previousCol) or (col == columns and previousCol == 1):
            colChange = 'j+1'

        move_counters[previousAction] = int(move_counters[previousAction]) + 1
        #Update row counts
        row_cpt_form = "PositionRow_t=i|PositionRow_t-1=" + rowChange + ",Action_t-1=" + previousAction
        row_cpt[row_cpt_form] = int(row_cpt[row_cpt_form]) + 1

        col_cpt_form = "PositionCol_t=j|PositionCol_t-1=" + colChange + ",Action_t-1=" + previousAction
        col_cpt[col_cpt_form] = int(col_cpt[col_cpt_form]) + 1

        previousCol = col
        previousRow = row
        previousAction = action

    #!!Remember to cast on variable to float!! (done)
    for key in row_cpt:
        previousAction = key.strip().split("|")[1].split("=")[2]
        move_counter_form =  previousAction
        row_cpt[key] = (row_cpt[key] +1)/float(move_counters[move_counter_form]+1) #!!! ADD LAPLACE SMOOTING !!!

    #Not sure what you were trying to do here.  By normalize the probability I just ment divide by denominator found above.
    ## I see. Somehow I thought that the cpds in row_cpt should sum to 1 but I just realized that this is so wrong. In fact they should sum to 4.
    #For each moving direction the cpds should sum to 1. That is print sum(row_cpt.values()) =4. We are good now.

    for key in col_cpt:
        previousAction = key.strip().split("|")[1].split("=")[2]
        move_counter_form =  previousAction
        col_cpt[key] = (col_cpt[key]+1)/float(move_counters[move_counter_form]+1) #!!! ADD LAPLACE SMOOTING !!! Need to check

    for key in landmark_cpt:
        row = key.strip().split("|")[1].split(",")[0].split("=")[1]
        col =  key.strip().split("|")[1].split(",")[1].split("=")[1]
        position_counter_form = str(row) + "," + str(col)

        #if (landmark_cpt[key]+1)/float(position_counters[position_counter_form]+1) > 1:
        #    print key
        #    print landmark_cpt[key]
        #    print position_counters[position_counter_form]
        #    print position_counter_form
        landmark_cpt[key] = (landmark_cpt[key]+1)/float(position_counters[position_counter_form]+1)

    #print position_counters, position_counters
    for key in wall_cpt:
        row = key.strip().split("|")[1].split(",")[0].split("=")[1]
        col =  key.strip().split("|")[1].split(",")[1].split("=")[1]
        position_counter_form = str(row) + "," + str(col)

        #if (wall_cpt[key]+1)/float(position_counters[position_counter_form]+1) > 1:
        #    print key
        #    print wall_cpt[key]
        #    print position_counter_form
        wall_cpt[key] = (wall_cpt[key]+1)/float(position_counters[position_counter_form]+1)


    training_file.close()

    return row_cpt, col_cpt, wall_cpt, landmark_cpt

def outputCPT(output_name, rows_CPT, columns_CPT, wall_CPT, landmark_CPT, rows, columns, landmarks, time_steps, Action):
    output_file = open(output_name, "w+");

    for key in rows_CPT:
        for t in xrange(1,time_steps+1):
            for action in Action:
                for row in xrange(1,rows+1):
                    row_t = key.strip().split("|")[0].split("=")[1]
                    row_t_previous =  key.strip().split("|")[1].split(",")[0].split("=")[1]
                    action_value = key.strip().split("|")[1].split(",")[1].split("=")[1]

                    if row_t == "i" and row_t_previous == "i-1" and action_value == action: #Match probabilities in rows_CPT
                        if row == 1:
                            line_forward = "PositionRow_" + str(t) + "=" + str(row) + " " + "PositionRow_" + str(t-1) + "=" + str(rows) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(rows_CPT[key])
                        else:
                            line_forward = "PositionRow_" + str(t) + "=" + str(row) + " " + "PositionRow_" + str(t-1) + "=" + str(row-1) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(rows_CPT[key])

                        output_file.write(line_forward)
                        output_file.write('\n')

                    if row_t == "i" and row_t_previous == "i+1" and action_value == action:
                        if row == rows:
                            line_backward = "PositionRow_" + str(t) + "=" + str(row) + " " + "PositionRow_" + str(t-1) + "=" + str(1) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(rows_CPT[key])
                        else:
                            line_backward = "PositionRow_" + str(t) + "=" + str(row) + " " + "PositionRow_" + str(t-1) + "=" + str(row+1) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(rows_CPT[key])
                        output_file.write(line_backward)
                        output_file.write('\n')

                    if row_t == "i" and row_t_previous == "i" and action_value == action:
                        line_stayin = "PositionRow_" + str(t) + "=" + str(row) + " " + "PositionRow_" + str(t-1) + "=" + str(row) + "," \
                        + "Action_" + str(t-1) + "=" + action + " " + str(rows_CPT[key])
                        output_file.write(line_stayin)
                        output_file.write('\n')

    #Output column CPTs

    for key in columns_CPT:
        for t in xrange(1,time_steps+1):
            for action in Action:
                for col in xrange(1,columns+1):
                    col_t = key.strip().split("|")[0].split("=")[1]
                    col_t_previous =  key.strip().split("|")[1].split(",")[0].split("=")[1]
                    action_value = key.strip().split("|")[1].split(",")[1].split("=")[1]
                    #print action_value
                    if col_t == "j" and col_t_previous == "j-1" and action_value == action:
                        if col == 1:
                            line_forward = "PositionCol_" + str(t) + "=" + str(col) + " " + "PositionCol_" + str(t-1) + "=" + str(columns) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(columns_CPT[key])
                        else:
                            line_forward = "PositionCol_" + str(t) + "=" + str(col) + " " + "PositionCol_" + str(t-1) + "=" + str(col-1) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(columns_CPT[key])
                        output_file.write(line_forward + '\n')

                    if col_t == "j" and col_t_previous == "j+1" and action_value == action:
                        if col == columns:
                            line_backward = "PositionCol_" + str(t) + "=" + str(col) + " " + "PositionCol_" + str(t-1) + "=" + str(1) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(columns_CPT[key])
                        else:
                            line_backward = "PositionCol_" + str(t) + "=" + str(col) + " " + "PositionCol_" + str(t-1) + "=" + str(col+1) + "," \
                            + "Action_" + str(t-1) + "=" + action + " " + str(columns_CPT[key])
                        output_file.write(line_backward + '\n')

                    if col_t == "j" and col_t_previous == "j" and action_value == action:
                        line_stayin = "PositionCol_" + str(t) + "=" + str(col) + " " + "PositionCol_" + str(t-1) + "=" + str(col) + "," \
                        + "Action_" + str(t-1) + "=" + action + " " + str(columns_CPT[key])
                        output_file.write(line_stayin +'\n')

    possible_directions = ['N', 'S', 'E', 'W']

    #Output wall and landmark CPTs

    for t in range(0, time_steps+1):
        for direction in possible_directions:
            for i in range(1, rows+1):
                for j in range(1, columns+1):
                    outputString = "ObserveWall_" + direction + "_"+str(t)+"=Yes PositionRow_"+str(t)+"=" + str(i) + ",PositionCol_" + str(t) + "=" + str(j)
                    prob = wall_CPT["ObserveWall_" + direction + "_t|PositionRow_t=" + str(i) + ",PositionCol_t=" + str(j)]
                    outputString = outputString + " " + str(prob)
                    output_file.write(outputString + '\n')
                    outputString = "ObserveWall_" + direction + "_"+str(t)+"=No PositionRow_"+str(t)+"=" + str(i) + ",PositionCol_" + str(t) + "=" + str(j)
                    prob = 1- prob
                    outputString = outputString + " " + str(prob)
                    output_file.write(outputString + '\n')
                    for landmark in range(1, landmarks+1):
                        outputString = "ObserveLandmark" + str(landmark) + "_" + direction + "_"+ str(t) +"=Yes PositionRow_" + str(t) + "=" + str(i) + ",PositionCol_" + str(t) +"=" + str(j)
                        prob = landmark_CPT["ObserveLandmark" + str(landmark) + "_" + direction + "_t|PositionRow_t=" + str(i) + ",PositionCol_t=" + str(j)]
                        outputString = outputString + " " + str(prob)
                        output_file.write(outputString + '\n')
                        outputString = "ObserveLandmark" + str(landmark) + "_" + direction + "_"+ str(t) +"=No PositionRow_" + str(t) + "=" + str(i) + ",PositionCol_" + str(t) +"=" + str(j)
                        prob = 1- prob
                        outputString = outputString + " " + str(prob)
                        output_file.write(outputString + '\n')


    output_file.close()

def main(args):

    # Check if all command line arguments are given
    if (len(args) != 3):
        print "Arguments: Network file, Training file, CPD file"
        exit();

    #--Read in network information
    network_file = open(args[0])

    #Get the number of nodes/variables in the graph
    num_vars = int(network_file.readline().strip())

    #Get variables and their possible values; variables is a dict
    variables = {} ## a dict
    for i in xrange(num_vars):
        (name, values) = network_file.readline().strip().split() ## a good line of code, LHS is a list
        values = values.split(',')
        variables[name] = values ##add rv's possible values(values) to dict_keys(names)

    #Get the number of rows, columns, landmarks, and time_steps
    (rows, columns, landmarks, time_steps) = get_grid_info(network_file)

    network_file.close()
    #--End read in network information

    (rows_CPT, columns_CPT, wall_CPT, landmark_CPT) = calculateCPT(args[1], variables["Action_0"], rows, columns, landmarks)

    # here need the number of rows, columns, landmarks becasue you need to loop over them
    outputCPT(args[2], rows_CPT, columns_CPT, wall_CPT, landmark_CPT, rows, columns, landmarks, time_steps, variables["Action_0"])

main(sys.argv[1:])
