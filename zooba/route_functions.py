from flask_login import current_user
from zooba.models import Course, User
from zooba.connection import *
from zooba.assignments import *
from zooba import app, db
import operator, datetime, heapq, os, secrets, math
from PIL import Image

#important functions for the site to perform each task

#converts an array to a dictionary of integers to values for json
def arrayToDict(items):
    count = 0
    itemsDict = {}
    for v in items:
        itemsDict[count] = v
        count += 1
    return itemsDict

#calculates the similarity from a users given classes using graph theory to determine similarity
def calculateSimilarity(recommendations):
    maxSim = max(recommendations.values()) 
    dupeRecomendations = dict(recommendations)
    for course in dupeRecomendations:
        recommendations[course] = round((maxSim - recommendations[course]) /  (maxSim) * 100, 2)
        if recommendations[course] == 0:
            recommendations.pop(course)

#implementation of dijkstras algorithm to find the classes that another class is most similarity 
#main component of course recommendation algorithm
def dijkstra(graph, start):
    distances = {i: 1000000 for i in graph}
    distances[start] = 0
    visited = {start}
    heap = [(0, start)]
    while len(heap) > 0:
        node = heapq.heappop(heap)[1]
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                if distances[neighbor] > distances[node] + graph[node][neighbor]:
                    distances[neighbor] = distances[node] + graph[node][neighbor]
                    heapq.heappush(heap, (distances[neighbor], neighbor))
    
    del distances[start]
    return {k: v for k, v in sorted(distances.items(), key=lambda item: item[1])}

#finds a given course by name from the database
def findCourseByName(course):
    courses = Course.query.all()
    for c in courses:
        if(str(c) == str(course)):
            return c
    return None

#converts the course objects and their related course to a graph for the course recommendation algorithm
def getGraph():
    graph = {}
    courses = Course.query.all()
    for c in courses:
        graph[c.name] = c.relatedCourses
    
    return graph

#gets the closest amount of friends based of an adjacency matrix to find new friends
def getNFriends(matrix, person, n):
    if n > len(matrix):
        n = len(matrix)

    count = 0
    friends = {}
    for friend in matrix[person]:
        if count > n:
            break
        if friend.id in person.friends.values() or friend.id <= 2:
            continue
        friends[friend] = matrix[person][friend] 
        count += 1
    return friends

#gets the similarity from two users to find if they would be good friends based of a similarity percentage
def getSimilarity(a, b):
    aCourses = list(a.all_courses.values())
    bCourses = list(b.all_courses.values())

    a = []
    b = []

    for i in range(len(aCourses)):
        if Course.query.filter_by(name=aCourses[i]).first() != None:
            a.append(Course.query.filter_by(name=aCourses[i]).first())

    for i in range(len(bCourses)):
        if Course.query.filter_by(name=bCourses[i]).first() != None:
            b.append(Course.query.filter_by(name=bCourses[i]).first())
        

    if len(a) > len(b):
        bigger = a
        smaller = b
    else:
        bigger = b
        smaller = a


    bigger = bigger[:len(smaller)]
    same = 0
    try:
        for i in bigger:
            for j in smaller:
                if i.name == j.name:
                    same += 1
                else:
                    if j.name in i.relatedCourses:
                        same += 1 - i.relatedCourses[j.name]/10
        x = same/(len(smaller)**2)
        score = math.log10(x + .1) + 1
        return round(score*100, 3) if score < 1 else 9001
    except:
        return 0

#creates a matrix based off the similarity score of each student to one another in order to find the user friends
def getSimilarityMatrix(people):
    friendsMatrix = {}
    for currPerson in people:
        connections = {}
        for comparePerson in people:
            if currPerson != comparePerson:
                connections[comparePerson] = getSimilarity(currPerson, comparePerson)
        connections = dict(sorted(connections.items(), key=operator.itemgetter(1)))
        friendsMatrix[currPerson] = connections
    return friendsMatrix

#gets the current relative time for a student's assignment 
#to see if they are late or have time to complete an assignment
def getTime(course_assignments):
    now = datetime.datetime.now()
    month = now.month
    day = now.day
    for course in course_assignments:
        for assignment in course_assignments[course]:
            due_date = assignment["due_date"] #"8/17/2020"
            due_month = int(due_date[:2])
            due_day = int(due_date[3:5])
            signal = 'chill'

            if month == due_month:
                if day >= due_day:
                    signal = 'late'
                elif due_day - day >= 1 and due_day - day <= 5:
                    signal = 'urgent'
                else:
                    signal = 'chill'
            elif due_month > month:
                signal = 'chill'
            elif month > due_month:
                signal = 'late'

            assignment['time'] = signal

#gets the username of each user in the site
def getUsernameList():
    username_list = []
    for user in User.query.all():
        username_list.append(user.site_user)
    return username_list

#calculates a student's grade point average
#based on the 6.0 grading system and takes into account various classes
def get_GPA(course_grades):
    weighted_classes = ['Digital Forensics', 'Computer Science III']
    not_graded_classes = ['PSAT Team', 'Off-Period', 'Student Aide']
    not_graded_num = 0

    for course in dict(course_grades):
        try:
            course_grades[course] = round(float(course_grades[course]))
        except:
            course_grades[course] = 0

    weighted_total = 0
    total_minus = 0

    for course in course_grades:
        if course in not_graded_classes:
            not_graded_num += 1
            continue
        if course in weighted_classes or 'AP' in course:
            weighted_total += 1
            total_minus += get_minus(6, course_grades[course])
        else:
            total_minus += get_minus(5, course_grades[course])
    try:
        onLevel = 5 * (len(course_grades)-weighted_total-not_graded_num)
        gradeBoosted = 6 * weighted_total
        gpaSum = onLevel + gradeBoosted - total_minus
        gpa = gpaSum/(len(course_grades)-not_graded_num)
        gpa = round(gpa, 3)
        return gpa
    except:
        return 0

#finds the key in a given dictionary (first key with that value)
def get_key(dictionary,val): 
    for key, value in dictionary.items(): 
         if val == value: 
             return key 
    return "DNE"

#gets the difference in a students grade from a hundred
#for GPA calculation
def get_minus(max_grade, grade):
    lost_points = (100-grade)*.1
    if max_grade-lost_points < 0:
        return max_grade
    else:
        return lost_points

#saves a picture that a student uploads
def save_picture(form_picture, w, h):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    size = [w,h]
    i = Image.open(form_picture)
    i.thumbnail(size)
    i.save(picture_path)

    return picture_fn

#checks if there is any updates within the student's Home Access Center
#updates these changes into the student object on the site
def update_assignments():
    assignments_page = connect(current_user.hac_email, current_user.hac_pass)
    assignments = bs.BeautifulSoup(assignments_page.content, 'html5lib')
    course_assignments, course_grades = get_assignments(assignments)
    current_user.course_assignments = course_assignments
    current_user.course_grades = course_grades
    current_user.current_gpa = str(get_GPA(course_grades))
    current_user.current_courses = arrayToDict(course_grades)
    all_course_list = list(current_user.current_courses.values()) + list(current_user.past_courses.values())
    current_user.all_courses = arrayToDict(all_course_list)
    
    for courseName in current_user.current_courses.values():
        course = Course.query.filter_by(name=courseName).first()
        if course:
            studentsTaking = list(course.students_taking.values())
            if current_user.id not in studentsTaking:
                studentsTaking.append(current_user.id)
            course.students_taking = arrayToDict(studentsTaking)

    db.session.commit()

