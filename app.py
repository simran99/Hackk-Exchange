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
from weather import Weather, Unit


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
 
@app.route('/sell')
@login_required
def sell():
    sell=query_db('select * from buy_sell')
    
    return render_template('sell.html', un=session["username"], sell=sell)    

@app.route('/buy')
@login_required
def buy():
    buy=query_db('select * from buy_sell')
    
    return render_template('buy.html', un=session["username"], buy=buy)

 
@app.route('/addsell', methods=['GET', 'POST'])
@login_required
def addsell():
    sell=query_db('select * from buy_sell')
    if request.method == "GET":
        return render_template("addsell.html",un=session["username"],sell=sell)
    else:
        submission = {}
        submission["item"] = request.form["item"]
        submission["quantity"] = request.form["quantity"]
        submission["price"] = request.form["price"]
        submission["name"] = request.form["name"]
        submission["contact"] = request.form["contact"]
        submission["type"]=1


        file = request.files.get('image')
        if not(file):
            digest = md5(submission['item'].encode('utf-8')).hexdigest()
            submission["image"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 256) #here 256 is size in sq pixels
        else:
            extension = os.path.splitext(file.filename)[1]
            token = uuid.uuid4().hex+extension
            f = os.path.join(app.config['UPLOAD_FOLDER'],token)
            file.save(f)
            submission["image"] = url_for('uploaded_file',filename=token)
            
        
        execute_db("insert into buy_sell (id,item,quantity,name,contact,type,image,price) values(0,?,?,?,?,?,?,?)", (
            submission["item"],
            submission["quantity"],
            submission["name"],
            submission["contact"],
            submission["type"],
            submission["image"],
            submission["price"],
        ))
        return redirect(url_for("sell"))   

@app.route('/addbuy', methods=['GET', 'POST'])
@login_required
def addbuy():
    buy=query_db('select * from buy_sell')
    if request.method == "GET":
        return render_template("addbuy.html",un=session["username"],buy=buy)
    else:
        submission = {}
        submission["item"] = request.form["item"]
        submission["quantity"] = request.form["quantity"]
        submission["price"] = request.form["price"]
        submission["name"] = request.form["name"]
        submission["contact"] = request.form["contact"]
        submission["type"]=2


        file = request.files.get('image')
        if not(file):
            digest = md5(submission['item'].encode('utf-8')).hexdigest()
            submission["image"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 256) #here 256 is size in sq pixels
        else:
            extension = os.path.splitext(file.filename)[1]
            token = uuid.uuid4().hex+extension
            f = os.path.join(app.config['UPLOAD_FOLDER'],token)
            file.save(f)
            submission["image"] = url_for('uploaded_file',filename=token)
            
        
        execute_db("insert into buy_sell (item,quantity,name,contact,type,image,price) values(?,?,?,?,?,?,?)", (
            submission["item"],
            submission["quantity"],
            submission["name"],
            submission["contact"],
            submission["type"],
            submission["image"],
            submission["price"],
        ))
        return redirect(url_for("buy"))   


@app.route("/logout")
def logout():
    session.clear()
    flash("Logout success","success")
    return redirect(url_for("login"))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)    



if __name__ == "__main__":
    
    app.run(debug = True)
