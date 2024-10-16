from app import app
import re
from flask import render_template, request, flash, redirect, url_for, session
from models import db, Influencer, Sponsor, Admin, Campaign, AdRequest, Flag
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from sqlalchemy import desc, func

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

from flask import send_file

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

    flag = Flag.query.filter_by(entity_type=session['user_type'], entity_id=session['id']).first()
    if flag:
        session['is_flagged'] = True
        flash("Error : Your account has been flagged. Please contact our support team at support@adconnect.in ")
        return redirect(url_for('login'))
    else:
        session['is_flagged'] = False
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
    if not name or not name.replace(" ", "").isalpha():
        flash("Error : Name should contain only alphabetic characters")
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
            if session['is_flagged'] == True:
                flash("Error : Your account has been flagged. Please contact our support team at support@adconnect.in ")
                return redirect(url_for('login'))
            else:
                return inner_func(*args, **kwargs)
        else:
            flash("Error : Please log in to continue")
            return redirect(url_for('login'))
    return decorated_func

def sponsor_required(inner_func):
    @wraps(inner_func)
    def decorated_func(*args, **kwargs):
        if session.get("id"):
            if session.get("user_type") == "sponsor":
                if session['is_flagged'] == True:
                    flash("Error : Your account has been flagged. Please contact our support team at support@adconnect.in ")
                    return redirect(url_for('login'))
                else:
                    return inner_func(*args, **kwargs)
            else:
                flash("Error : You are not authorized to access this page")
                return redirect(url_for('index'))
        else:
            flash("Error : Please log in to continue")
            return redirect(url_for('login'))
    return decorated_func

def influencer_required(inner_func):
    @wraps(inner_func)
    def decorated_func(*args, **kwargs):
        if session.get("id"):
            if session.get("user_type") == "influencer":
                if session['is_flagged'] == True:
                    flash("Error : Your account has been flagged. Please contact our support team at support@adconnect.in ")
                    return redirect(url_for('login'))
                else:
                    return inner_func(*args, **kwargs)
            else:
                flash("Error : You are not authorized to access this page")
                return redirect(url_for('index'))
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
    elif user_type=="admin":
        admin = Admin.query.filter_by(id=id).first()
        return render_template('profile.html',admin=admin, user_type=user_type)
    
@app.route('/logout')
@auth_required
def logout():
    session.pop('user_type')
    session.pop('id')
    flash("User logged out successfully")
    return redirect(url_for('index'))

@app.route("/profile/sponsor/update", methods = ["POST"])
@sponsor_required
def update_profile_sponsor():
    username = request.form.get('username')
    password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    name = request.form.get('name')
    budget = request.form.get('budget')
    industry = request.form.get('industry')

    updated_fields = []

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
                if not re.match(r"^[A-Za-z\s]+$", name):
                    flash("Error : Name should contain only alphabetic characters")
                    return redirect(url_for('profile'))
                sponsor.name = name
                updated_fields.append("Name")
            if budget and str(sponsor.budget) != budget:
                try:
                    budget = float(budget)
                    if budget <= 0:
                        flash("Error : Budget should be greater than 0")
                        return redirect(url_for('profile')) 
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

@app.route("/sponsor/home")
@sponsor_required
def sponsor_home():
    sponsor = Sponsor.query.filter_by(id=session['id']).first()
    return render_template('/sponsor/sponsor_home.html',sponsor = sponsor)


@app.route("/sponsor/<int:sponsor_id>/create_campaign")
@sponsor_required
def create_campaign(sponsor_id):
    today = datetime.now().strftime('%Y-%m-%d')
    sponsor = Sponsor.query.filter_by(id=sponsor_id).first()
    return render_template("/sponsor/create_campaign.html", today = today, sponsor=sponsor)

@app.route("/sponsor/<int:sponsor_id>/create_campaign", methods=['POST'])
@sponsor_required
def create_campaign_post(sponsor_id):
    name = request.form.get('campaign_name')
    description = request.form.get("description")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    budget = request.form.get("budget")
    visibility = request.form.get("visibility")
    goals = request.form.get("goals")
    requirements = request.form.get('requirements')
    payment = request.form.get('payment')
    
    if not all([name,description,start_date,end_date,budget,visibility,goals, requirements,payment]):
        flash("Error : Please enter all required fields")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        flash("Error: Invalid date format", "danger")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id))
    if start_date < datetime.now().date():
        flash("Error : Start date cannot be before today")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id))
    if start_date > end_date:
        flash("Error : Start date cannot be after end date")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id))

    try:
        budget = float(budget)
        if budget < 0:
            raise ValueError
    except ValueError:
        flash("Error : Budget must be a positive number")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id))

    if not (visibility=="public" or visibility=="private"):
        flash("Error : Visibility should be either public or private")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id)) 

    try:
        payment = float(payment)
        if payment < 0:
            raise ValueError
    except ValueError:
        flash("Error : Payment amount must be a positive number")
        return redirect(url_for('create_campaign', sponsor_id=sponsor_id))
    

    campaign = Campaign(name = name, 
                        description = description, 
                        start_date = start_date, 
                        end_date=end_date,
                        budget=budget, 
                        visibility=visibility,
                        goals = goals,
                        requirements = requirements,
                        payment_amount = payment,
                        sponsor_id = sponsor_id)
    
    db.session.add(campaign)
    db.session.commit()
    flash("Campaign added successfully")
    return redirect(url_for('sponsor_home'))

@app.route("/sponsor/<int:sponsor_id>/show_campaigns")
@sponsor_required
def show_campaigns(sponsor_id):
    campaigns = Campaign.query.filter_by(sponsor_id = sponsor_id).order_by(desc(Campaign.id)).all()
    sponsor = Sponsor.query.filter_by(id=sponsor_id).first()
    flagged_campaigns = Flag.query.filter_by(entity_type='campaign').all()
    flagged_campaign_ids = {flag.entity_id for flag in flagged_campaigns}

    return render_template("sponsor/show_campaigns.html", campaigns = campaigns,sponsor = sponsor,flagged_campaign_ids=flagged_campaign_ids)

@app.route("/campaign/<int:campaign_id>/update")
@sponsor_required
def update_campaign(campaign_id):
    flagged = Flag.query.filter_by(entity_type='campaign',entity_id=campaign_id).first()
    if flagged:
        flash("Error : This campaign has been flagged. Please contact our support team at support@adconnect.in ")
        return redirect(url_for('show_campaigns',sponsor_id=session['id']))
    campaign = Campaign.query.filter_by(id=campaign_id).first()
    return render_template('/sponsor/update_campaign.html', campaign = campaign)

@app.route("/campaign/<int:campaign_id>/update" , methods=['POST'])
@sponsor_required
def update_campaign_post(campaign_id):
    flagged = Flag.query.filter_by(entity_type='campaign',entity_id=campaign_id).first()
    if flagged:
        flash("Error : This campaign has been flagged. Please contact our support team at support@adconnect.in ")
        return redirect(url_for('show_campaigns',sponsor_id=session['id']))
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        flash("Error : Campaign does not exist")
        return redirect(url_for("sponsor_home"))
    
    name = request.form.get('campaign_name')
    description = request.form.get("description")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    budget = request.form.get("budget")
    visibility = request.form.get("visibility")
    goals = request.form.get("goals")
    requirements = request.form.get('requirements')
    payment = request.form.get('payment')

    campaign = Campaign.query.get(campaign_id)

    if not all([name,description,start_date,end_date,budget,visibility,goals,requirements,payment]):
        flash("Error : Please enter all required fields")
        return redirect(url_for('update_campaign', campaign_id = campaign_id))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        flash("Error: Invalid date format", "danger")
        return redirect(url_for('update_campaign', campaign_id = campaign_id))
    if start_date != campaign.start_date:
        flash("Error : Start date cannot be edited")
        return redirect(url_for('update_campaign', campaign_id = campaign_id))
    if start_date > end_date:
        flash("Error : Start date cannot be after end date")
        return redirect(url_for('update_campaign', campaign_id = campaign_id))

    try:
        budget = float(budget)
        if budget < 0:
            raise ValueError
    except ValueError:
        flash("Error : Budget must be a positive number")
        return redirect(url_for('update_campaign', campaign_id = campaign_id))

    if not (visibility=="public" or visibility=="private"):
        flash("Error : Visibility should be either public or private")
        return redirect(url_for('update_campaign', campaign_id = campaign_id)) 

    try:
        payment = float(payment)
        if payment < 0:
            raise ValueError
    except ValueError:
        flash("Error : Payment amount must be a positive number")
        return redirect(url_for('update_campaign', campaign_id = campaign_id))
    

    campaign.name = name
    campaign.description = description
    campaign.end_date = end_date
    campaign.budget = budget
    campaign.visibility = visibility
    campaign.goals = goals
    campaign.requirements = requirements
    campaign.payment_amount = payment

    db.session.commit()
    flash("Campaign updated successfully")
    return redirect(url_for('show_campaigns', sponsor_id = campaign.sponsor_id))

@app.route("/campaign/<int:campaign_id>/delete")
@sponsor_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    return render_template("/sponsor/delete_campaign.html", campaign=campaign)

@app.route("/campaign/<int:campaign_id>/delete", methods = ['POST'])
@sponsor_required
def delete_campaign_post(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        flash("Error : Campaign does not exist")
        return redirect(url_for("sponsor_home"))
    db.session.delete(campaign)
    db.session.commit()
    flash("Campaign deleted successfully")
    return redirect(url_for('sponsor_home'))

@app.route("/campaign/<int:campaign_id>/track")
def track_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    ad_requests = AdRequest.query.filter_by(campaign_id = campaign_id).all()
    spendings = sum(ad_request.payment_amount for ad_request in ad_requests if ad_request.payment_status == 1)
    unique_platforms = set(ad_request.influencer.niche for ad_request in ad_requests if ad_request.influencer)
    return render_template('/sponsor/track_campaigns.html',campaign=campaign,spendings=spendings,ad_requests=ad_requests,unique_platforms=unique_platforms)

@app.route("/sponsor/search")
@sponsor_required
def search_influencer():
    categories = set([influencer.category for influencer in Influencer.query.distinct(Influencer.category).all()])
    niches = set([influencer.niche for influencer in Influencer.query.distinct(Influencer.niche).all()])

    influencers = Influencer.query.all()
    return render_template("/sponsor/search_influencers.html", influencers = influencers, categories=categories, niches=niches)

@app.route("/sponsor/search", methods=["POST"])
@sponsor_required
def search_influencer_post():
    category = request.form.get('category')
    niche = request.form.get('niche')
    reach = request.form.get("reach")
    
    query = Influencer.query
    if category:
        query = query.filter(Influencer.category == category)
    if niche:
        query = query.filter(Influencer.niche == niche)
    if reach:
        query = query.filter(Influencer.reach >= int(reach))

    influencers = query.all()
    categories = set([influencer.category for influencer in Influencer.query.distinct(Influencer.category).all()])
    niches = set([influencer.niche for influencer in Influencer.query.distinct(Influencer.niche).all()])

    return render_template("/sponsor/search_influencers.html", influencers = influencers, categories=categories, niches=niches)

@app.route("/sponsor/search/<int:id>/view_influencer")
@sponsor_required
def view_influencer(id):
    influencer = Influencer.query.get(id)
    return render_template('/sponsor/view_influencer.html',influencer = influencer)

@app.route("/sponsor/create_ad_request", defaults = {'influencer_id' : None})
@app.route("/sponsor/create_ad_request/<int:influencer_id>")
@sponsor_required
def create_ad_request(influencer_id):
    sponsor_id = session['id']
    campaigns = Campaign.query.filter_by(sponsor_id = sponsor_id)
    influencers = Influencer.query.all()
    return render_template('/sponsor/create_ad_request.html',campaigns=campaigns, influencers=influencers,influencer_id=influencer_id)

@app.route("/sponsor/create_ad_request", defaults = {'influencer_id' : None},methods=['POST'])
@app.route("/sponsor/create_ad_request/<int:influencer_id>", methods=['POST'])
@sponsor_required
def create_ad_request_post(influencer_id):
    sponsor_id = session['id']
    campaign_id = request.form.get('campaign_id')
    inflcr_id = request.form.get('influencer_id')
    messages = request.form.get("messages")
    requirements = request.form.get("requirements")
    payment_amount = request.form.get("payment_amount")   

    if not all([sponsor_id,campaign_id,inflcr_id,requirements,payment_amount]):
        flash("Error : Please fill all required fields")
        return redirect(url_for('create_ad_request',influencer_id=influencer_id))
    
    campaign = Campaign.query.filter_by(id = campaign_id, sponsor_id=sponsor_id).first()
    is_flagged = Flag.query.filter_by(entity_type='campaign', entity_id=campaign_id).first()
    if not campaign:
        flash("Error : Invalid campaign. Please select a valid campaign.")
        return redirect(url_for('create_ad_request', influencer_id=influencer_id))
    if is_flagged:
        flash("Error : This campaign has been flagged. You cannot create ad requests for this campaign. Kindly contact support at support@adconnect.in for more details.")
        return redirect(url_for('create_ad_request', influencer_id=influencer_id))
    influencer = Influencer.query.filter_by(id=inflcr_id).first()
    if not influencer:
        flash("Error : Invalid influencer. Please select a valid influencer.")
        return redirect(url_for('create_ad_request', influencer_id=influencer_id))

    try:
        payment_amount = float(payment_amount)
        if payment_amount <= 0:
            flash("Error : Payment amount be greater than 0")
            return redirect(url_for('create_ad_request', influencer_id=influencer_id))
    except ValueError:
        flash("Error: Invalid payment amount")
        return redirect(url_for('create_ad_request', influencer_id=influencer_id))
    
    ad_request = AdRequest(
        campaign_id = campaign_id,
        influencer_id = inflcr_id,
        sponsor_id = sponsor_id,
        messages = messages,
        requirements = requirements,
        payment_amount = payment_amount
    )
    db.session.add(ad_request)
    db.session.commit()
    flash("Ad Request sent successfully")
    return redirect(url_for('sponsor_home'))

@app.route('/sponsor/<int:sponsor_id>/show_ad_requests_sponsor')
@sponsor_required
def show_ad_requests_sponsor(sponsor_id):
    sponsor = Sponsor.query.filter_by(id = sponsor_id).first()
    ad_requests = AdRequest.query.filter_by(sponsor_id = sponsor.id).order_by(desc(AdRequest.sponsor_accepted)).all()
    return render_template('/sponsor/show_ad_requests.html', sponsor=sponsor, ad_requests = ad_requests)

@app.route('/sponsor/<int:sponsor_id>/sponsor_accept_request/<int:request_id>',methods=["POST"])
@sponsor_required
def sponsor_accept_request(sponsor_id,request_id):
    sponsor = Sponsor.query.get(sponsor_id)
    ad_request = AdRequest.query.get(request_id)
    if not sponsor:
        flash("Error : Sponsor does not exist")
        return redirect(url_for('login'))
    if not (session['user_type']=='sponsor' and session['id']==sponsor_id):
        flash("Error : You are not authorized to access this page")
        return redirect(url_for('sponsor_home'))
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('sponsor_home'))
    
    if ad_request.sponsor_id != sponsor_id:
        flash("Error : Ad Request does not exist")
        return redirect(url_for("sponsor_home"))
    
    campaign = Campaign.query.filter_by(id=ad_request.campaign_id).first()
    if not campaign : 
        flash("Error : Campaign does not exist or has ended")
        return redirect(url_for('sponsor_home'))
    
    influencer = Influencer.query.filter_by(id=ad_request.influencer_id).first()
    if not influencer:
        flash("Error : Influencer does not exist")
        return redirect(url_for('sponsor_home'))
    
    ad_request.sponsor_accepted = True
    if ad_request.sponsor_accepted == True and ad_request.influencer_accepted == True:
        ad_request.status = 'Accepted'
    if ad_request.sponsor_accepted == False or ad_request.influencer_accepted == False:
        ad_request.status = 'Rejected'

    db.session.commit()
    flash("Ad Request accepted successfully")
    return redirect(url_for('sponsor_home'))

@app.route('/sponsor/<int:sponsor_id>/sponsor_reject_request/<int:request_id>',methods=["POST"])
@sponsor_required
def sponsor_reject_request(sponsor_id,request_id):
    sponsor = Sponsor.query.get(sponsor_id)
    ad_request = AdRequest.query.get(request_id)
    if not sponsor:
        flash("Error : Sponsor does not exist")
        return redirect(url_for('login'))
    if not (session['user_type']=='sponsor' and session['id']==sponsor_id):
        flash("Error : You are not authorized to access this page")
        return redirect(url_for('sponsor_home'))
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('sponsor_home'))
    if ad_request.sponsor_id != sponsor_id:
        flash("Error : Ad Request does not exist")
        return redirect(url_for("sponsor_home"))
    
    campaign = Campaign.query.filter_by(id=ad_request.campaign_id).first()
    if not campaign : 
        flash("Error : Campaign does not exist or has ended")
        return redirect(url_for('sponsor_home'))
    
    influencer = Influencer.query.filter_by(id=ad_request.influencer_id).first()
    if not influencer:
        flash("Error : Influencer does not exist")
        return redirect(url_for('sponsor_home'))
    
    ad_request.sponsor_accepted = False

    if ad_request.sponsor_accepted == True and ad_request.influencer_accepted == True:
        ad_request.status = 'Accepted'
    if ad_request.sponsor_accepted == False or ad_request.influencer_accepted == False:
        ad_request.status = 'Rejected'

    db.session.commit()
    flash("Ad Request rejected")
    return redirect(url_for('sponsor_home'))

@app.route("/sponsor/<int:sponsor_id>/negotiate_ad_request_sponsor/<int:ad_request_id>")
@sponsor_required
def negotiate_ad_request_sponsor(sponsor_id,ad_request_id):
    sponsor = Sponsor.query.get(sponsor_id)
    if not sponsor:
        flash("Error : Sponsor does not exist")
        return redirect(url_for('sponsor_home'))
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('sponsor_home'))
    
    return render_template("/sponsor/negotiate_ad_request.html", sponsor=sponsor,ad_request=ad_request)

@app.route("/sponsor/<int:sponsor_id>/negotiate_ad_request_sponsor/<int:ad_request_id>", methods=['POST'])
@sponsor_required
def negotiate_ad_request_sponsor_post(sponsor_id,ad_request_id):
    sponsor = Sponsor.query.get(sponsor_id)
    if not sponsor:
        flash("Error : Sponsor does not exist")
        return redirect(url_for('sponsor_home'))
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('sponsor_home'))
    
    if not ad_request.campaign:
        flash("Error : Campaign does not exist or has ended")
        return redirect(url_for('sponsor_home'))
    
    messages = request.form.get('messages')
    if not messages:
        flash("Error : Message cannot be empty")
        return redirect(url_for('sponsor_home'))
    
    ad_request.messages = messages

    if ad_request.sponsor_accepted == True and ad_request.influencer_accepted == True:
        ad_request.status = 'Accepted'
    if ad_request.sponsor_accepted == False or ad_request.influencer_accepted == False:
        ad_request.status = 'Rejected'

    db.session.commit()
    flash("Message sent successfully")
    return redirect(url_for('show_ad_requests_sponsor', sponsor_id = sponsor.id))

@app.route("/sponsor/<int:sponsor_id>/delete_ad_request/<int:ad_request_id>")
@sponsor_required
def delete_ad_request(sponsor_id,ad_request_id):
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('sponsor_home'))
    sponsor = Sponsor.query.get(sponsor_id)
    if not sponsor:
        flash("Error : You are not authorized to access this page")
        return redirect(url_for('index'))
    return render_template("/sponsor/delete_ad_request.html",sponsor=sponsor, ad_request = ad_request)

@app.route("/sponsor/<int:sponsor_id>/delete_ad_request/<int:ad_request_id>", methods=['POST'])
@sponsor_required
def delete_ad_request_post(sponsor_id,ad_request_id):
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('sponsor_home'))
    sponsor = Sponsor.query.get(sponsor_id)
    if not sponsor:
        flash("Error : You are not authorized to access this page")
        return redirect(url_for('index'))
    db.session.delete(ad_request)
    db.session.commit()
    flash("Ad request deleted successfully")
    return redirect(url_for('show_ad_requests_sponsor',sponsor_id = ad_request.sponsor_id))

@app.route("/sponsor/ad_request/<int:ad_request_id>/make_payment")
@sponsor_required
def make_payment(ad_request_id):
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Invalid Ad Request")
        return redirect(url_for('sponsor_home'))
    
    return render_template('/sponsor/make_payment.html', ad_request = ad_request)

@app.route("/sponsor/ad_request/<int:ad_request_id>/make_payment", methods=["POST"])
@sponsor_required
def make_payment_post(ad_request_id):
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Invalid Ad Request")
        return redirect(url_for('sponsor_home'))
    
    if ad_request.payment_status == True:
        flash("Payment is already processed")
        return redirect(url_for('sponsor_home'))

    payment_amount = request.form.get('payment_amount')
    try:
        payment_amount = float(payment_amount)
        if payment_amount <= 0:
            raise ValueError
    except ValueError:
        flash("Error : Invalid payment amount")
        return redirect(url_for('make_payment',ad_request_id = ad_request.id))

    ad_request.payment_amount = payment_amount
    ad_request.payment_status = True
    db.session.commit()
    flash("Payment successful")
    return redirect(url_for('make_payment',ad_request_id = ad_request.id))

@app.route("/sponsor/ad_request/<int:ad_request_id>/download_invoice")
@sponsor_required
def download_invoice(ad_request_id):
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error: Invalid Ad Request")
        return redirect(url_for('sponsor_home'))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.fontName = 'Times-Roman'
    title_style.fontSize = 20
    title_style.leading = 30
    title_style.alignment = 1

    subtitle_style = styles['Heading2']
    subtitle_style.fontName = 'Times-Roman'
    subtitle_style.fontSize = 14
    subtitle_style.leading = 20
    subtitle_style.alignment = 1

    footer_style = styles['Normal']
    footer_style.fontName = 'Times-Roman'
    footer_style.fontSize = 12
    footer_style.leading = 18
    footer_style.alignment = 1

    header_style = styles['Heading1']
    header_style.fontName = 'Times-Roman'
    header_style.fontSize = 14
    header_style.leading = 18
    header_style.alignment = 1

    # Title and Subtitle
    title = Paragraph("AdConnect", title_style)
    subtitle = Paragraph(f"Invoice for Ad Request", subtitle_style)

    elements.append(title)
    elements.append(Spacer(1, 12))
    elements.append(subtitle)
    elements.append(Spacer(1, 24))

    # Data for the table
    data = [
        ["Description", "Details"],
        ["Campaign Name", ad_request.campaign.name],
        ["Sponsor Name", ad_request.sponsor.username],
        ["Influencer Name", ad_request.influencer.username],
        ["Payment Amount", f"{ad_request.payment_amount:.2f}"],
        ["Status", "Paid"]
    ]

    # Create the table
    table = Table(data, colWidths=[2.5 * inch, 3.5 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.turquoise),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Roman'),
        ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 24))  # Space between table and footer

    # Footer
    footer = Paragraph("Thank you for your payment!", footer_style)
    elements.append(footer)

    # Build the PDF
    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"invoice_{ad_request.id}.pdf", mimetype='application/pdf')


# #################################### influencer functions

@app.route("/profile/influencer/update",methods=["POST"])
@influencer_required
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
                if not re.match(r"^[A-Za-z\s]+$", name):
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

@app.route("/influencer/home")
@influencer_required
def influencer_home():
    influencer = Influencer.query.filter_by(id=session['id']).first()
    return render_template('/influencer/influencer_home.html', influencer = influencer)

# @app.route('/influencer/<int:influencer_id>/create_ad_request_influencer')
# @influencer_required
# def create_ad_request_influencer(influencer_id):
#     return f"Create ad request for {influencer_id}"

@app.route('/influencer/<int:influencer_id>/show_ad_requests')
@influencer_required
def show_ad_requests(influencer_id):
    influencer = Influencer.query.filter_by(id=influencer_id).first()
    ad_requests = AdRequest.query.filter_by(influencer_id=influencer_id).order_by(desc(AdRequest.influencer_accepted)).all()
    return render_template("/influencer/show_ad_requests.html", influencer = influencer, ad_requests = ad_requests)

@app.route('/influencer/<int:influencer_id>/search_campaigns')
@influencer_required
def search_campaigns(influencer_id):
    influencer = Influencer.query.filter_by(id=influencer_id).first()
    industries = set([sponsor.industry for sponsor in Sponsor.query.distinct(Sponsor.industry).all()])
    campaigns = Campaign.query.filter_by(visibility = "public" ).all()
    return render_template("/influencer/search_campaigns.html", campaigns = campaigns, influencer = influencer, industries=industries)

@app.route('/influencer/<int:influencer_id>/search_campaigns', methods=['POST'])
@influencer_required
def search_campaigns_post(influencer_id):
    industry = request.form.get('industry')
    budget = request.form.get('budget')
    query=Campaign.query
    query = query.filter(Campaign.visibility=='public')
    if industry:
        query=query.join(Campaign.sponsor).filter(Sponsor.industry == industry)
    if budget:
        if float(budget) > 0:
            query = query.filter(Campaign.budget >= budget)
    campaigns = query.all()
    influencer = Influencer.query.filter_by(id=influencer_id).first()
    industries = set([sponsor.industry for sponsor in Sponsor.query.distinct(Sponsor.industry).all()])
    return render_template("/influencer/search_campaigns.html", campaigns = campaigns, influencer = influencer, industries=industries)

@app.route('/influencer/<int:influencer_id>/<int:campaign_id>/<int:sponsor_id>/interested_campaign', methods=['POST'])
@influencer_required
def interested_campaign(campaign_id, sponsor_id,influencer_id):
    existing_ad_request = AdRequest.query.filter_by(campaign_id=campaign_id,sponsor_id=sponsor_id,influencer_id=influencer_id).first()
    if existing_ad_request:
        flash("Ad request already initiated")
        return redirect(url_for('influencer_home'))
    campaign=Campaign.query.get(campaign_id)
    adrequest = AdRequest(campaign_id = campaign_id, 
                          sponsor_id = sponsor_id, 
                          influencer_id = influencer_id, 
                          messages="I am interested", 
                          requirements = campaign.requirements,
                          payment_amount = campaign.payment_amount)
    db.session.add(adrequest)
    db.session.commit()
    flash("Ad Request sent successfully")
    return redirect(url_for('influencer_home'))

@app.route('/influencer/<int:influencer_id>/influencer_accept_request/<int:request_id>',methods=["POST"])
@influencer_required
def influencer_accept_request(influencer_id,request_id):
    influencer = Influencer.query.get(influencer_id)
    ad_request = AdRequest.query.get(request_id)
    if not influencer:
        flash("Error : Influencer does not exist")
        return redirect(url_for('login'))
    if not (session['user_type']=='influencer' and session['id']==influencer_id):
        flash("Error : You are not authorized to access this page")
        return redirect(url_for('influencer_home'))
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('influencer_home'))
    
    if ad_request.influencer_id != influencer_id:
        flash("Error : Ad Request does not exist")
        return redirect(url_for("influencer_home"))
    
    campaign = Campaign.query.filter_by(id=ad_request.campaign_id).first()
    if not campaign : 
        flash("Error : Campaign does not exist or has ended")
        return redirect(url_for('influencer_home'))
    
    sponsor = Sponsor.query.filter_by(id=ad_request.sponsor_id).first()
    if not sponsor:
        flash("Error : Sponsor does not exist")

    ad_request.influencer_accepted = True

    if ad_request.sponsor_accepted == True and ad_request.influencer_accepted == True:
        ad_request.status = 'Accepted'
    if ad_request.sponsor_accepted == False or ad_request.influencer_accepted == False:
        ad_request.status = 'Rejected'

    db.session.commit()
    flash("Ad Request accepted successfully")
    return redirect(url_for('influencer_home'))

@app.route('/influencer/<int:influencer_id>/influencer_reject_request/<int:request_id>',methods=["POST"])
@influencer_required
def influencer_reject_request(influencer_id,request_id):
    influencer = Influencer.query.get(influencer_id)
    ad_request = AdRequest.query.get(request_id)
    if not influencer:
        flash("Error : Influencer does not exist")
        return redirect(url_for('login'))
    if not (session['user_type']=='influencer' and session['id']==influencer_id):
        flash("Error : You are not authorized to access this page")
        return redirect(url_for('influencer_home'))
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('influencer_home'))
    
    if ad_request.influencer_id != influencer_id:
        flash("Error : Ad Request does not exist")
        return redirect(url_for("influencer_home"))
    campaign = Campaign.query.filter_by(id=ad_request.campaign_id).first()
    if not campaign : 
        flash("Error : Campaign does not exist or has ended")
        return redirect(url_for('influencer_home'))
    
    sponsor = Sponsor.query.filter_by(id=ad_request.sponsor_id).first()
    if not sponsor:
        flash("Error : Sponsor does not exist")
        return redirect(url_for('influencer_home'))
    ad_request.influencer_accepted = False

    if ad_request.sponsor_accepted == True and ad_request.influencer_accepted == True:
        ad_request.status = 'Accepted'
    if ad_request.sponsor_accepted == False or ad_request.influencer_accepted == False:
        ad_request.status = 'Rejected'

    db.session.commit()
    flash("Ad Request rejected")
    return redirect(url_for('influencer_home'))

@app.route("/influencer/<int:influencer_id>/negotiate_ad_request_influencer/<int:ad_request_id>")
def negotiate_ad_request_influencer(influencer_id,ad_request_id):
    influencer = Influencer.query.get(influencer_id)
    if not influencer:
        flash("Error : Influencer does not exist")
        return redirect(url_for('influencer_home'))
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('influencer_home'))
    
    return render_template("/influencer/negotiate_ad_request.html", influencer=influencer,ad_request=ad_request)

@app.route("/influencer/<int:influencer_id>/negotiate_ad_request_influencer/<int:ad_request_id>", methods=['POST'])
def negotiate_ad_request_influencer_post(influencer_id,ad_request_id):
    influencer = Influencer.query.get(influencer_id)
    if not influencer:
        flash("Error : Influencer does not exist")
        return redirect(url_for('influencer_home'))
    ad_request = AdRequest.query.get(ad_request_id)
    if not ad_request:
        flash("Error : Ad Request does not exist")
        return redirect(url_for('influencer_home'))
    
    if not ad_request.campaign:
        flash("Error : Campaign does not exist or has ended")
        return redirect(url_for('influencer_home'))
    
    messages = request.form.get('messages')
    if not messages:
        flash("Error : Message cannot be empty")
        return redirect(url_for('influencer_home'))
    
    ad_request.messages = messages

    if ad_request.sponsor_accepted == True and ad_request.influencer_accepted == True:
        ad_request.status = 'Accepted'
    if ad_request.sponsor_accepted == False or ad_request.influencer_accepted == False:
        ad_request.status = 'Rejected'

    db.session.commit()
    flash("Message sent successfully")
    return redirect(url_for('show_ad_requests', influencer_id = influencer.id))
   

############################################################# 
################### ADMIN FUNCTIONALITY #####################
#############################################################

def admin_required(inner_func):
    @wraps(inner_func)
    def decorated_func(*args, **kwargs):
        if session.get("id"):
            if session.get("user_type") == "admin":
                return inner_func(*args, **kwargs)
            else:
                flash("Error : You are not authorized to access this page")
                return redirect(url_for('index'))
        else:
            flash("Error : Please log in to continue")
            return redirect(url_for('login'))
    return decorated_func

@app.route("/profile/admin/update", methods = ["POST"])
@admin_required
def update_profile_admin():
    username = request.form.get('username')
    password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    name = request.form.get('name')

    admin = Admin.query.filter_by(id = session['id']).first()
    if password:
        if check_password_hash(admin.passhash , password):                    
            if new_password or confirm_new_password: 
                if password != new_password and new_password == confirm_new_password:
                    password_error = is_valid_password(new_password)
                    if password_error:
                        flash(f"Error : {password_error}")
                        return redirect(url_for('profile'))
                    else:
                        admin.passhash = generate_password_hash(new_password)
                        flash("Password updated successfully")
                        return redirect(url_for('admin_home'))
                else:
                    flash("Error : New password must be different from the current password and confirm password should match")
                    return redirect(url_for('profile'))
            else:
                flash("No new changes made")
            return redirect(url_for('profile'))
        else:
            flash("Error : Password is incorrect")
            return redirect(url_for('profile'))
    else:
        flash("Error : Verify password to make changes to profile")
        return redirect(url_for('profile'))

@app.route('/admin/home')
@admin_required
def admin_home():
    admin = Admin.query.filter_by(id=session['id']).first()
    influencers = Influencer.query.all()
    sponsors =Sponsor.query.all()
    private_campaigns = Campaign.query.filter_by(visibility ='private').all()
    public_campaigns = Campaign.query.filter_by(visibility='public').all()
    flagged_influencers = Flag.query.filter_by(entity_type='influencer').all()
    flagged_sponsors = Flag.query.filter_by(entity_type='sponsor').all()
    accepted_requests = AdRequest.query.filter_by(status="Accepted").all()
    rejected_requests = AdRequest.query.filter_by(status="Rejected").all()
    pending_requests = AdRequest.query.filter_by(status="Pending").all()

    industry_distribution = db.session.query(
        Sponsor.industry,
        func.count(Sponsor.id).label('count')
    ).group_by(Sponsor.industry).all()

    niche_distribution = db.session.query(
        Influencer.niche,
        func.count(Influencer.id).label('count')
    ).group_by(Influencer.niche).all()

    niches = [item.niche for item in niche_distribution]
    niche_counts = [item.count for item in niche_distribution]

    # Process industry distribution into dictionaries
    industries = [item.industry for item in industry_distribution]
    counts = [item.count for item in industry_distribution]
    return render_template('/admin/admin_home.html',
                           admin = admin, 
                           influencers=len(influencers), 
                           sponsors=len(sponsors),
                           private_campaigns=len(private_campaigns),
                           public_campaigns=len(public_campaigns),
                           flagged_influencers = len(flagged_influencers),
                           flagged_sponsors = len(flagged_sponsors),
                           no_of_acc_req = len(accepted_requests),
                           no_of_rej_req = len(rejected_requests),
                           no_of_pen_req = len(pending_requests),
                           industries=industries,
                           counts=counts,
                           niches=niches,
                           niche_counts=niche_counts
                           )

@app.route("/admin/manage_influencers")
@admin_required
def manage_influencers():
    admin=Admin.query.get(session['id'])
    influencers = Influencer.query.all()
    flagged_influencers = Flag.query.filter_by(entity_type='influencer').all()
    flagged_influencer_ids = {flag.entity_id for flag in flagged_influencers}

    return render_template('/admin/manage_influencers.html', influencers = influencers, admin=admin,flagged_influencer_ids = flagged_influencer_ids)

@app.route("/admin/manage_sponsors")
@admin_required
def manage_sponsors():
    admin=Admin.query.get(session['id'])
    sponsors = Sponsor.query.all()
    flagged_sponsors = Flag.query.filter_by(entity_type='sponsor').all()
    flagged_sponsor_ids = {flag.entity_id for flag in flagged_sponsors}

    return render_template('/admin/manage_sponsors.html', sponsors = sponsors, admin=admin, flagged_sponsor_ids=flagged_sponsor_ids)


@app.route("/admin/manage_campaigns")
@admin_required
def manage_campaigns():
    admin=Admin.query.get(session['id'])
    campaigns = Campaign.query.all()

    flagged_campaigns = Flag.query.filter_by(entity_type='campaign').all()
    flagged_campaign_ids = {flag.entity_id for flag in flagged_campaigns}

    return render_template('/admin/manage_campaigns.html', campaigns = campaigns, admin=admin, flagged_campaign_ids=flagged_campaign_ids)


@app.route("/admin/<int:admin_id>/flag/<entity_type>/<int:entity_id>", methods=["POST"])
@admin_required
def flag_entity(admin_id, entity_type, entity_id):
    if not admin_id or not entity_type or not entity_id:
        flash("Error : Provide all required fields")
        return redirect(url_for('admin_home'))
    if admin_id != session['id']:
        flash("Error : You are not authorized to access this page.")
        return redirect(url_for('index'))
    if entity_type not in ['influencer', 'sponsor', 'campaign']:
        flash("Error : Incorrect entity type")
        return redirect(url_for('admin_home'))
    if entity_type == 'influencer':
        influencer = Influencer.query.get(entity_id)
        flagged = Flag.query.filter_by(entity_id=entity_id, entity_type=entity_type).first()
        if flagged:
            flash(f"{entity_type.capitalize()} is already flagged")
            return redirect(url_for('admin_home'))
        if not influencer:
            flash("Error : Influencer does not exist")
            return redirect(url_for('admin_home'))
    if entity_type == 'sponsor':
        sponsor = Sponsor.query.get(entity_id)
        flagged = Flag.query.filter_by(entity_id=entity_id, entity_type=entity_type).first()
        if flagged:
            flash(f"{entity_type.capitalize()} is already flagged")
            return redirect(url_for('admin_home'))
        if not sponsor:
            flash("Error : Sponsor does not exist")
            return redirect(url_for('admin_home'))
    if entity_type == 'campaign':
        campaign = Campaign.query.get(entity_id)
        flagged = Flag.query.filter_by(entity_id=entity_id, entity_type='entity_type').first()
        if flagged:
            flash(f"{entity_type.capitalize()} is already flagged")
            return redirect(url_for('admin_home'))
        if not campaign:
            flash("Error : Campaign does not exist")
            return redirect(url_for('admin_home'))
    flag = Flag(reason="Flagged for supervision to ensure compliance with platform terms and conditions",
                entity_type = entity_type, entity_id=entity_id, admin_id = admin_id)
    db.session.add(flag)
    db.session.commit()
    flash(f"{entity_type.capitalize()} flagged successfully")
    return redirect(url_for('admin_home'))

@app.route("/admin/<int:admin_id>/unflag/<entity_type>/<int:entity_id>", methods=["POST"])
@admin_required
def unflag_entity(admin_id, entity_type, entity_id):
    if not admin_id or not entity_type or not entity_id:
        flash("Error : Provide all required fields")
        return redirect(url_for('admin_home'))
    if admin_id != session['id']:
        flash("Error : You are not authorized to access this page.")
        return redirect(url_for('index'))
    if entity_type not in ['influencer', 'sponsor', 'campaign']:
        flash("Error : Incorrect entity type")
        return redirect(url_for('admin_home'))
    if entity_type == 'influencer':
        influencer = Influencer.query.get(entity_id)
        flagged = Flag.query.filter_by(entity_id=entity_id, entity_type=entity_type).first()
        if not flagged:
            flash(f"{entity_type.capitalize()} is not flagged")
            return redirect(url_for('admin_home'))
        if not influencer:
            flash("Error : Influencer does not exist")
            return redirect(url_for('admin_home'))
    if entity_type == 'sponsor':
        sponsor = Sponsor.query.get(entity_id)
        flagged = Flag.query.filter_by(entity_id=entity_id, entity_type=entity_type).first()
        if not flagged:
            flash(f"{entity_type.capitalize()} is not flagged")
            return redirect(url_for('admin_home'))
        if not sponsor:
            flash("Error : Sponsor does not exist")
            return redirect(url_for('admin_home'))
    if entity_type == 'campaign':
        campaign = Campaign.query.get(entity_id)
        flagged = Flag.query.filter_by(entity_id=entity_id, entity_type=entity_type).first()
        if not flagged:
            flash(f"{entity_type.capitalize()} is not flagged")
            return redirect(url_for('admin_home'))
        if not campaign:
            flash("Error : Campaign does not exist")
            return redirect(url_for('admin_home'))
    flag = Flag.query.filter_by(entity_id=entity_id, entity_type=entity_type,admin_id=admin_id).first()
    db.session.delete(flag)
    db.session.commit()
    flash(f"{entity_type.capitalize()} unflagged successfully")
    return redirect(url_for('admin_home'))