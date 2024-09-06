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

    if not user_type or not username or not password : 
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

def is_valid_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not re.search("[a-z]", password) or not re.search("[A-Z]", password):
        return "Password must contain both uppercase and lowercase letters"
    if not re.search("[0-9]", password):
        return "Password must contain at least one number"
    if not re.search("[@#$%^&+=]", password):
        return "Password must contain at least one special character (@#$%^&+=)"
    return None

@app.route("/register", methods=["POST"])
def register_post():
    user_type = request.form.get("user_type")
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    name = request.form.get("name")

    if not user_type or not username or not password or not confirm_password or not name:
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
    password_error = is_valid_password(password)
    if password_error:
        flash(f"Error : {password_error}")
        return redirect(url_for('register'))
    if not name or not name.isalpha():
        flash("Error : Name should contain only alphabetic characters")
        return redirect(url_for('profile'))
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

@app.route("/profile/sponsor/update", methods = ["POST"])
@auth_required
def update_profile_sponsor():
    username = request.form.get('username')
    password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    name = request.form.get('name')
    budget = request.form.get('budget')
    industry = request.form.get('industry')

    updated_fields = []

    if not session['user_type'] == 'sponsor':
        flash("You are not authorized to update sponsor details")
        return redirect(url_for('profile'))

    sponsor = Sponsor.query.filter_by(id = session['id']).first()
    if password:
        if check_password_hash(sponsor.passhash , password):
            if username and sponsor.username != username:
                if Sponsor.query.filter_by(username = username).first():
                    flash("Error : Username already exists.")
                    return redirect(url_for('profile'))
                elif len(username) < 3 or len(username) > 20:
                    flash("Error: Username must be between 3 and 20 characters")
                    return redirect(url_for('profile'))
                if not username.isalnum():
                    flash("Error: Username must contain only letters and numbers")
                    return redirect(url_for('profile'))
                else:
                    sponsor.username = username
                    updated_fields.append("Username")
                    
            if new_password or confirm_new_password: 
                if password != new_password and new_password == confirm_new_password:
                    password_error = is_valid_password(new_password)
                    if password_error:
                        flash(f"Error : {password_error}")
                        return redirect(url_for('profile'))
                    else:
                        sponsor.passhash = generate_password_hash(new_password)
                        updated_fields.append("Password")
                else:
                    flash("Error : New password must be different from the current password and confirm password should match")
                    return redirect(url_for('profile'))
            
            if name and sponsor.name != name:
                if not re.match("^[A-Za-z\s]+$", name):
                    flash("Error : Name should contain only alphabetic characters")
                    return redirect(url_for('profile'))
                sponsor.name = name
                updated_fields.append("Name")
            if budget and str(sponsor.budget) != budget:
                try:
                    float(budget)
                except ValueError:
                    flash("Error : Budget should be a number")
                    return redirect(url_for('profile'))
                sponsor.budget = budget
                updated_fields.append("Budget")
            if industry and sponsor.industry != industry:
                if not industry.isalpha():
                    flash("Error : Industry should have all alphabetic characters")
                    return redirect(url_for('profile'))
                sponsor.industry = industry
                updated_fields.append("Industry")
            if updated_fields:
                db.session.commit()
                flash(f"{', '.join(updated_fields)} updated successfully!")
            else:
                flash("No new changes made")
            return redirect(url_for('profile'))
        else:
            flash("Error : Password is incorrect")
            return redirect(url_for('profile'))
    else:
        flash("Error : Verify password to make changes to profile")
        return redirect(url_for('profile'))


@app.route("/profile/influencer/update",methods=["POST"])
@auth_required
def update_profile_influencer():
    username = request.form.get('username')
    password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    name = request.form.get('name')
    category = request.form.get('category')
    niche = request.form.get('niche')
    reach = request.form.get('reach')

    updated_fields = []
    if not session['user_type'] == 'influencer':
        flash("Error : You are not authorized to update influencer details")
        return redirect(url_for('profile'))

    influencer = Influencer.query.filter_by(id = session['id']).first()
    if password:
        if check_password_hash(influencer.passhash , password):
            if username and influencer.username != username:
                if Influencer.query.filter_by(username = username).first():
                    flash("Error : Username already exists.")
                    return redirect(url_for('profile'))
                elif len(username) < 3 or len(username) > 20:
                    flash("Error: Username must be between 3 and 20 characters")
                    return redirect(url_for('profile'))
                if not username.isalnum():
                    flash("Error: Username must contain only letters and numbers")
                    return redirect(url_for('profile'))
                else:
                    influencer.username = username
                    updated_fields.append("Username")
                    
            if new_password or confirm_new_password: 
                if password != new_password and new_password == confirm_new_password:
                    password_error = is_valid_password(new_password)
                    if password_error:
                        flash(f"Error : {password_error}")
                        return redirect(url_for('profile'))
                    else:
                        influencer.passhash = generate_password_hash(new_password)
                        updated_fields.append("Password")
                else:
                    flash("Error : New password must be different from the current password and confirm password should match")
                    return redirect(url_for('profile'))
            
            if name and influencer.name != name:
                if not re.match("^[A-Za-z\s]+$", name):
                    flash("Error : Name should contain only alphabetic characters")
                    return redirect(url_for('profile'))
                influencer.name = name
                updated_fields.append("Name")

            if category and influencer.category != category:
                if not category.isalpha():
                    flash("Error : Category must have only alphabetic characters")
                    return redirect(url_for('profile'))
                influencer.category = category
                updated_fields.append("Category")
            if niche and influencer.niche != niche:
                if not niche.isalpha():
                    flash("Error : Niche should have all alphabetic characters")
                    return redirect(url_for('profile'))
                influencer.niche = niche
                updated_fields.append("Niche")
            if reach and str(influencer.reach) != reach:
                try:
                    float(reach)
                except ValueError:
                    flash("Error : Reach should be a number")
                    return redirect(url_for('profile'))
                influencer.reach = reach
                updated_fields.append("Reach")
            if updated_fields:
                db.session.commit()
                flash(f"{', '.join(updated_fields)} updated successfully!")
            else:
                flash("No new changes made")
            return redirect(url_for('profile'))
        else:
            flash("Error : Password is incorrect")
            return redirect(url_for('profile'))
    else:
        flash("Error : Verify password to make changes to profile")
        return redirect(url_for('profile'))


