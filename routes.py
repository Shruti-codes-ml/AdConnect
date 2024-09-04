from app import app
from flask import render_template
from flask import request, flash, redirect, url_for, session
from models import db, Influencer, Sponsor, Admin
from werkzeug.security import generate_password_hash, check_password_hash

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

    if not user_model:
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

    if user_type == "influencer" : 
        category = request.form.get("category")
        niche = request.form.get("niche")
        if not username or not password or not confirm_password or not category or not niche : 
            flash("Error : Please fill all required fields")
            return redirect(url_for('register'))
        if password != confirm_password:
            flash("Error : Passwords do not match")
            return redirect(url_for('register'))
        
        influencer = Influencer.query.filter_by(username = username).first()
        if influencer : 
            flash("Error : Username already taken")
            return redirect(url_for('register'))
        new_influencer = Influencer(username = username, passhash = generate_password_hash(password),name=name, category = category, niche=niche)
        db.session.add(new_influencer)
        db.session.commit()
        flash("Influencer successfully registered")
        return redirect(url_for('index'))
    if user_type == "sponsor" :
        budget = request.form.get("budget")
        industry = request.form.get("industry")
        
        if not username or not password or not confirm_password or not budget or not industry : 
            flash("Error : Please fill all required fields")
            return redirect(url_for('register'))
        if password != confirm_password:
            flash("Error : Passwords do not match")
            return redirect(url_for('register'))
        
        sponsor = Sponsor.query.filter_by(username = username).first()
        if sponsor : 
            flash("Error : Username already taken")
            return redirect(url_for('register'))
        new_sponsor = Sponsor(username = username, passhash = generate_password_hash(password),name=name, budget = budget, industry = industry)
        db.session.add(new_sponsor)
        db.session.commit()
        flash("Sponsor successfully registered")
        return redirect(url_for('index'))
     


    
