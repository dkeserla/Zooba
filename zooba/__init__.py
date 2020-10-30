from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

#starts the flask project
app = Flask(__name__)
#contains the necessary key for the page to correctly run and function
app.config['SECRET_KEY'] = '' #hidden for security
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

#initializes the database, encryption algorithm, and login manager all from flask versions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

#calls the different routes required for the site
from zooba import routes
