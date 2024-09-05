from app import app
import re
from flask import render_template
from flask import request, flash, redirect, url_for, session
from models import db, Influencer, Sponsor, Admin
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/register")
def register():
    return render_template('register.html')

@app.route("/login", methods=["POST"])
def login_post():
    user_type = request.form.get("user_type")
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password : 
        flash("Error : Please fill all required fields")
        return redirect(url_for('login'))
    
    user_models = {
        "influencer": Influencer,
        "sponsor": Sponsor,
        "admin" : Admin
    }

    user_model = user_models.get(user_type)

    if (user_type not in user_models.keys()) or (not user_model):
        flash("Error: Invalid user type")
        return redirect(url_for('login'))
    
    user = user_model.query.filter_by(username=username).first()

    if not user:
        flash(f"Error : {user_type.capitalize()} not registered")
        return redirect(url_for('register'))
    
    if not check_password_hash(user.passhash, password):
        flash("Error: Incorrect password")
        return redirect(url_for('login'))
    
    session['user_type'] = user_type
    session['id'] = user.id
    flash(f"{user_type.capitalize()} login successful")
    return redirect(url_for('index'))

@app.route("/register", methods=["POST"])
def register_post():
    user_type = request.form.get("user_type")
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    name = request.form.get("name")

    if not username or not password or not confirm_password:
        flash("Error : Please fill all required fields")
        return redirect(url_for('register'))
    
    if len(username) < 3 or len(username) > 20:
        flash("Error: Username must be between 3 and 20 characters")
        return redirect(url_for('register'))
    if not username.isalnum():
        flash("Error: Username must contain only letters and numbers")
        return redirect(url_for('register'))

    if password != confirm_password:
        flash("Error : Passwords do not match")
        return redirect(url_for('register'))
    if len(password) < 8:
        flash("Error: Password must be at least 8 characters long")
        return redirect(url_for('register'))
    if not re.search("[a-z]", password) or not re.search("[A-Z]", password):
        flash("Error: Password must contain both uppercase and lowercase letters")
        return redirect(url_for('register'))
    if not re.search("[0-9]", password):
        flash("Error: Password must contain at least one number")
        return redirect(url_for('register'))
    if not re.search("[@#$%^&+=]", password):
        flash("Error: Password must contain at least one special character (@#$%^&+=)")
        return redirect(url_for('register'))

    if user_type == "influencer":
        additional_fields = {"category": request.form.get("category"), "niche": request.form.get("niche"), "reach" : request.form.get("reach")}
        user_class = Influencer
    elif user_type == "sponsor":
        additional_fields = {"budget": request.form.get("budget"), "industry": request.form.get("industry")}
        try:
            budget = float(request.form.get("budget"))
            if budget <= 0:
                flash("Error: Budget must be a positive number")
                return redirect(url_for('register'))
        except ValueError:
            flash("Error: Invalid budget amount")
            return redirect(url_for('register'))
        user_class = Sponsor
    else:
        flash("Error: Invalid user type")
        return redirect(url_for('register'))

    if not all(additional_fields.values()):
        flash("Error: Please fill all required fields")
        return redirect(url_for('register'))
    
    if user_class.query.filter_by(username=username).first():
        flash("Error: Username already taken")
        return redirect(url_for('register'))
    
    new_user = user_class(username=username, passhash=generate_password_hash(password), name=name, **additional_fields)
    db.session.add(new_user)
    db.session.commit()

    flash(f"{user_type.capitalize()} successfully registered")
    return redirect(url_for('login'))

def auth_required(inner_func):
    @wraps(inner_func)
    def decorated_func(*args, **kwargs):
        if session.get("id"):
            return inner_func(*args, **kwargs)
        else:
            flash("Error : Please log in to continue")
            return redirect(url_for('login'))
    return decorated_func

@app.route("/profile")
@auth_required
def profile():
    user_type = session['user_type']
    id = session['id']
    if user_type == "influencer":
        influencer = Influencer.query.filter_by(id=id).first()
        return render_template('profile.html', influencer = influencer, user_type = user_type)
    elif user_type == "sponsor":
        sponsor = Sponsor.query.filter_by(id=id).first()
        return render_template('profile.html', sponsor = sponsor, user_type = user_type)
    
@app.route('/logout')
@auth_required
def logout():
    session.pop('user_type')
    session.pop('id')
    flash("User logged out successfully")
    return redirect(url_for('index'))

@app.route("/profile/sponsor/update",methods=["POST"])
@auth_required
def update_profile_sponsor():
    return "Update Profile Sponsor"

@app.route("/profile/influencer/update",methods=["POST"])
@auth_required
def update_profile_influencer():
    return "Update Profile Influencer"