import sqlite3 ,os
from flask import Flask, flash, redirect, render_template, request, session, abort , g , url_for , jsonify
from passlib.hash import sha256_crypt as sha
from hashlib import md5
from functools import wraps
from datetime import datetime
from flask import send_from_directory
from flask_mail import Mail , Message
import uuid
import pygeoip
<<<<<<< HEAD
from weather import Weather, Unit

=======
from weather import Weather ,Unit 
>>>>>>> d6ea375c5000f2e104e5e1ca936600d91fb338a8
app = Flask(__name__, static_url_path="", static_folder="static")
mail=Mail(app)

UPLOADS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOADS_PATH
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 #Limits filesize to 16MB


app.secret_key = os.urandom(12)

Database = 'agro.db'

if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response
    
import pygeoip
from weather import Weather, Unit

gi = pygeoip.GeoIP('GeoIPCity.dat', pygeoip.MEMORY_CACHE)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(Database)
    return db

def query_db(query, args=(), one=False): #used to retrive values from the table
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query , args=()): #executes a sql command like alter table and insert
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query , args)
    conn.commit()
    cur.close()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
@login_required
def home():
    redirect(url_for("home",username=session['username']))


@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        error = None
        username=request.form["username"]
        password=request.form["password"]
        phash = query_db("select password from users where username = ?", (username, ))
        if phash==[]:
            flash("User does not exist","danger")
            return render_template("login.html")

        if sha.verify(password, phash[0][0]):
            session["username"] = username
            return redirect(url_for('profile'))
        else:
            flash("Incorrect Password","danger")
            return render_template("login.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        submission = {}
        submission["username"] = request.form["username"]
        submission["name"] = request.form["name"]
        submission["email"] = request.form["email"]
        submission["phone"] = request.form["ph"]
        submission["pass"] = request.form["password"]
        submission["conf_pass"] = request.form["conf_pass"]
        digest = md5(submission['username'].encode('utf-8')).hexdigest()
        submission["image"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 256) #here 256 is size in sq pixels


        if submission["pass"]!=submission["conf_pass"]:
            flash("Passwords don't match","danger")
            return render_template("signup.html")

        if query_db("select username from users where username = ?", (submission["username"],))!=[]:
            flash("User already taken","danger")
            return render_template("signup.html")

        password = sha.encrypt(submission["pass"])
        execute_db("insert into users values(?,?,?,?,?,0,?)", (
            submission["username"],
            submission["name"],
            submission["email"],
            password,
            submission["phone"],
            submission["image"],
        ))
        flash("User Created","success")
        return redirect(url_for("login"))

@app.route('/members')
@login_required
def profile():
    location = request.remote_addr

    location = gi.record_by_addr(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
    #city = location['city']
    city = 'Patiala'
    location = jsonify(location)

    weather = Weather(unit=Unit.CELSIUS)
    location1 = weather.lookup_by_location(str(city))
    condition = location1.condition
    weather = str(condition.text)



    return render_template('home.html',location = city, weather = weather, un=session["username"])
    

@app.route("/logout")
def logout():
    session.clear()
    flash("Logout success","success")
    return redirect(url_for("login"))



if __name__ == "__main__":
    
    app.run(debug = True)
