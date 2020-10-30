from flask import render_template, url_for, redirect, request
from zooba.models import Course, User, load_user
from zooba import app, db, bcrypt
from flask_login import login_user, current_user, logout_user, login_required
from flask import abort
from zooba.admin_routes import *
from zooba.route_functions import *

#the main routes of the site to the various pages for users
#try and catch to ensure an engaging user experience

#route for getting the user to a simple page with all their information
@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    try:
        return render_template("account.html", current_user=current_user, Course=Course)
    except:
        abort(404)

#route for displaying students with similar course interests
#then offers opportunity to add these displayed students and adding them to their friend list
@app.route("/add-friends",methods=['GET', 'POST'])
@login_required
def addFriends():
    try:
        matrix = getSimilarityMatrix(User.query.all())
        friends = getNFriends(matrix,current_user,5)
        atul, dinesh = load_user(2), load_user(1)
        creatorSim = [0, 0]
        creatorFriend = [True, True]
        current_friends = current_user.friends.values()    
        if current_user != atul and current_user != dinesh:
            creatorSim = [matrix[current_user][atul], matrix[current_user][dinesh]]
            creatorFriend[0] = not 2 in current_friends
            creatorFriend[1] = not 1 in current_friends

        if request.method == "POST":
            username = request.form.get("username")
            if username == "":
                return redirect(url_for("addFriends"))
            if username != None:
                username = username.lower()
                friend_list = [i for i in User.query.all() if i.site_user.lower().startswith(username) or i.name.lower().startswith(username)]
                if list(friend_list) == list(User.query.all()):
                    friend_list = []
                friends = {}
                for friend in friend_list:
                    if not current_user == friend and friend.id not in current_user.friends.values():
                        friends[friend] = matrix[current_user][friend]
            else:
                friend_user = request.form.get("add")[4:]
                friend = User.query.filter_by(site_user=friend_user).first()
                friend_requests = dict(friend.incoming_friend_requests)
                if current_user.id not in friend_requests.values() and not current_user.id == friend.id:
                    friend_requests[len(friend_requests)] = current_user.id
                    friend.incoming_friend_requests = friend_requests
                    db.session.commit()

                return redirect(url_for("addFriends"))
            return render_template("add-friends.html", friends=friends, creatorSim = creatorSim, creatorFriend=creatorFriend, dinesh=dinesh, atul=atul, search=True, current_user=current_user)
        return render_template("add-friends.html", friends=friends, creatorSim=creatorSim, creatorFriend=creatorFriend, dinesh=dinesh, atul=atul, search=False, current_user=current_user)
    except:
        abort(404)

#displays the various assignments that a student has 
#in addition to a relative timer so the student knows if they have time to turn the assignment on time
@app.route("/assignments")
@login_required
def assignments():
    try:
        course_assignments = current_user.course_assignments
        getTime(course_assignments)
        return render_template("assignments.html", title="Assignment", course_assignments=course_assignments, current_user=current_user)
    except:
        abort(404)

#creates a course page based off of a passed in course for a user to seee various information about the course
#can see a description of the course in additon to other students taking the course
@app.route("/course/<course>", methods=['GET', 'POST'])
@login_required
def course(course):
    try:
        course = Course.query.filter_by(name=course).first()
        matrix = getSimilarityMatrix(User.query.all())
        friends = {}
        for student_id in course.students_taking.values():
            student = load_user(student_id)
            if student != current_user:
                friends[student] = matrix[current_user][student]
        
        if request.method == "POST":
            friend_user = request.form.get("add")[4:]
            friend = User.query.filter_by(site_user=friend_user).first()
            friend_requests = dict(friend.incoming_friend_requests)
            if current_user.id not in friend_requests.values() and not current_user.id == friend.id:
                friend_requests[len(friend_requests)] = current_user.id
                friend.incoming_friend_requests = friend_requests
                db.session.commit()
        return render_template('course.html', current_user=current_user, course=course, friends=friends)
    except:
        abort(404)

#page for the main course recommendation algorithm
#pass in a class and the algorithm calculates classes that will be a very good fit in relation
@app.route("/course-recommendation", methods=['GET', 'POST'])
@login_required
def courseRecommendation():
    try:
        graph = getGraph()
        start = list(graph.keys())[0]
        if request.method == 'POST':
            start = request.form.get('start')
            return redirect(url_for("courseRecommendationPage", favorite=start))
        recommendations = dijkstra(graph, start)
        return redirect(url_for("courseRecommendationPage", favorite=start)) 
    except:
        abort(404)

#allows user to pass in a various class to calculate similar classes for users
@app.route("/course-recommendation/<favorite>", methods=['GET', 'POST'])
@login_required
def courseRecommendationPage(favorite):
    try:
        graph = getGraph()
        if request.method == 'POST':
            favorite = request.form.get('start')
            return redirect(url_for("courseRecommendationPage", favorite=favorite))
        recommendations = dijkstra(graph, favorite)
        calculateSimilarity(recommendations)
        return render_template("course-recommendation.html", current_user=current_user, start=favorite, courses=Course.query.all(), recommendations=recommendations, Course=Course)
    except:
        abort(404)

#opportunity for user to edit profile and input various information 
#updated in database accordingly
@app.route("/edit-profile", methods=['GET', 'POST'])
@login_required
def editProfile():
    try:
        pastCourses = Course.query.all()
        for courseName in current_user.current_courses.values():
            course = Course.query.filter_by(name=courseName).first()
            if course:
                pastCourses.remove(course)
        
        if request.method == 'POST':
            student_past_courses = []
            for course in pastCourses:
                check = request.form.get(course.name + "--check")
                if check == "on":
                    student_past_courses.append(course.name)
            current_user.past_courses = arrayToDict(student_past_courses)
            all_course_list = list(current_user.current_courses.values()) + list(current_user.past_courses.values())
            current_user.all_courses = arrayToDict(all_course_list)
            profile = request.files["profile_pic"]
            back = request.files["profile_bac"]

            insta = None if request.form.get("instagram") == "" else request.form.get("instagram")
            snap = None if request.form.get("snapchat") == "" else request.form.get("snapchat")
            email = None if request.form.get("email") == "" else request.form.get("email")
            about = None if request.form.get("about_me") == "" else request.form.get("about_me")
            hac_email = request.form.get("hac_email")
            hac_pass = request.form.get("hac_pass")

            current_user.instagram = insta
            current_user.snapchat = snap
            current_user.email = email
            current_user.about_me = about
            current_user.hac_email = hac_email
            current_user.hac_pass = hac_pass
            
            if profile.filename != '':
                current_user.profile_photo = save_picture(profile, 198, 198)
            if back.filename != '':
                current_user.profile_background = save_picture(back, 934*4, 350*4)

            db.session.commit()
            return redirect(url_for("account"))
        return render_template("edit-profile.html", current_user=current_user, pastCourses=pastCourses)
    except:
        abort(404)

#shows the users current GPA for the six weeks grading period
#based on their current grades in Home Access Center
@app.route("/gpa")
@login_required
def GPA():
    try:
        print(current_user.course_grades)
        return render_template("gpa.html", current_user=current_user, Course=Course)
    except:
        print(current_user.course_grades)
        abort(404)

#the default home directory with links to each facet of the site
@app.route("/",methods=['GET', 'POST'])
def home():
    try:
        return render_template("index.html")
    except:
        abort(404)

#allows user to see any incoming friend requests and add them accordingly if they want
@app.route('/incoming', methods=['GET', 'POST'])
@login_required
def incoming():
    try:
        matrix = getSimilarityMatrix(User.query.all())
        incoming = {}
        for friend_id in current_user.incoming_friend_requests.values():
            friend = load_user(friend_id)
            if current_user != friend:
                incoming[friend] = matrix[current_user][friend]

        if request.method == 'POST':
            friend_user = request.form.get("add")[4:]
            friend = User.query.filter_by(site_user=friend_user).first()
            user_requests = dict(current_user.incoming_friend_requests)
            user_requests.pop(str(get_key(user_requests, friend.id)))
            current_user.incoming_friend_requests = user_requests
            friend_requests = dict(friend.incoming_friend_requests)
            key = get_key(friend_requests, current_user.id)
            if key != "DNE":
                friend_requests.pop(str(key))
            friend.incoming_friend_requests = friend_requests
            current_user.updateFriends(friend.id)
            db.session.commit()
            
            return redirect(url_for("incoming"))
        return render_template('incoming-friends.html', incoming=incoming, current_user=current_user)
    except:
        abort(404)

#login route that takes into account the users encrypted password
#redirects them to the account when they are logged in
@app.route("/login", methods=['GET', 'POST'])
def login():
    try:
        if not current_user.is_anonymous:
            return redirect(url_for("account"))
        user_name = request.form.get("username")
        if user_name:
            user_name = user_name.lower()
            user = User.query.filter_by(site_user=user_name).first()
            if user and bcrypt.check_password_hash(user.site_pass, request.form.get("password")):
                login_user(user)
                update_assignments()
                return redirect(url_for("account"))
        return render_template("login.html")
    except:
        abort(404)

#allows user to easily logout upon clicking the logout button
@app.route("/logout")
def logout():
    try:
        logout_user()
        return redirect(url_for('home'))
    except:
        abort(404)

#error handling for showing 404 errors in a more user friendly manner
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404page.html', title = '404'), 404

#error handling for showing 401 unauthorized errors to redirect user to allowed page
@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for("login"))

#allows the user to signup for the site and easily use the different facets of the site upon logging in
@app.route("/signup",methods=['GET', 'POST'])
def signup():
    try:
        if not current_user.is_anonymous:
            return redirect(url_for("account"))
        if request.method == 'POST':
            name = request.form.get("name")
            user_name = request.form.get("user_name")
            password =  bcrypt.generate_password_hash(request.form.get("pass_word")).decode('utf-8')
            hac_email = request.form.get("hac_email")
            hac_pass = request.form.get("hac_password")
            if User.query.filter_by(site_user=user_name).first():
                return redirect(url_for("signup"))
            user = User(name, user_name.lower(), password, hac_email, hac_pass) 
            db.session.add(user)
            db.session.commit()
            login_user(user)
            update_assignments()
            return redirect(url_for("editProfile"))
        return render_template("signup.html",site_users = getUsernameList())
    except:
        abort(404)

#creates a user page for a given user such as a friend or someone who is taking a similar class
@app.route("/user/<username>")
@login_required
def user(username):
    try:
        username = username.lower()
        friend = User.query.filter_by(site_user=username).first()
        matrix = getSimilarityMatrix(User.query.all())
        similarityScore=100
        if friend and current_user != friend:
            similarityScore = matrix[current_user][friend]
        return render_template("friend-page.html", Course= Course, current_user=current_user, friend=friend, similarityScore=similarityScore)
    except:
        abort(404)

#allows the user to see all their friends and click their profile and visit what they are up to
@app.route("/view-friends")
@login_required
def viewFriends():
    try:
        matrix = getSimilarityMatrix(User.query.all())
        friends = {}
        for friend_id in current_user.friends.values():
            friend = load_user(friend_id)
            friends[friend] = matrix[current_user][friend]
        return render_template("view-friends.html",current_user=current_user, friends=friends)
    except:
        abort(404)