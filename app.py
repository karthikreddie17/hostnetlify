from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_cors import CORS 
from resources import *
from db1 import *
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


app= Flask(__name__)
bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///database.sqlite3"
app.config['SECRET_KEY'] = 'thisisasecretkey'
CORS(app)  #configuration of api
api.init_app(app)
db.init_app(app)
app.app_context().push()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))



@app.route('/reverse', methods=['POST'])
def reverse_string():
    data = request.get_json()
    input = data['input']
    return {'output': input[::-1]}



@app.route('/')
def home():
    admin = Users.query.filter_by(user_type='admin').first()
    if not admin:
        user = Users(username="admin", password=bcrypt.generate_password_hash("admin123"),user_type="admin")
        db.session.add(user)
        db.session.commit()
    return render_template('home.html')

@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = Users(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/adminlogin', methods =["GET", "POST"])
def adminlogin():
    form = AdminLoginForm()

    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.adminname.data).first()
        if user and Users.isAdmin(user):
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid User!!','error')
                return redirect(url_for('adminlogin'))
    return render_template('adminlogin.html',form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = UserLoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('userdashboard'))
            else:
                return redirect(url_for('login'))   
    return render_template('login.html', form=form)




@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    return render_template('dashboard.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/userdashboard', methods =["GET", "POST"])
@login_required
def userdashboard():
    venues = Venues.query.all()
    return render_template('user_dashboard.html',venues=venues)


@app.route('/book_tickets', methods=['GET', 'POST'])
@login_required
def book_tickets():
    if request.method == 'POST':
        search_term = request.form['search_term']
        search_results = Venues.query.filter(Venues.venue_name.ilike(f"%{search_term}%")).all()
        return render_template('book_tickets.html', venues=search_results, search_term=search_term)
    else:
        venues = Venues.query.all()
        return render_template('book_tickets.html', venues=venues,search_term=None)


@app.route('/book_tickets/<int:venue_id>', methods=['GET', 'POST'])
@login_required
def select_showfromvenue(venue_id):
    venue = Venues.query.get(venue_id)
    shows = Shows.query.join(Association).filter(Association.venue_id==venue_id).all()
    show_available_seats = {}
    for show in shows:
        bookings = Bookings.query.filter_by(bvenue_id=venue_id, bshow_id=show.show_id).all()
        num_tickets_booked = sum(booking.num_tickets for booking in bookings) 
        show_available_seats[show.show_id] = venue.venue_capacity // len(shows) - num_tickets_booked
    search_term = request.form.get('search_term')

    # Filter shows based on search term
    if search_term:
        shows = [show for show in shows if search_term.lower() in show.show_name.lower()]

    return render_template('select_showfromvenue.html', shows=shows, venue_id=venue_id, show_available_seats=show_available_seats, search_term=search_term)


@app.route('/book_tickets/<int:venue_id>/<int:show_id>', methods=['GET', 'POST'])
@login_required
def book_final(venue_id, show_id):
    venue = Venues.query.get(venue_id) # use query.get() to get a single object by ID
    show = Shows.query.get(show_id) # use query.get() to get a single object by ID
    bookings = Bookings.query.filter_by(bvenue_id=venue_id, bshow_id=show_id).all()
    num_tickets_booked = sum(booking.num_tickets for booking in bookings)   
    available_seats = venue.venue_capacity // len(venue.x) - num_tickets_booked
    if request.method == "POST":
        n_tickets = int(request.form['n_tickets'])
        price = int(request.form['price'])
        t_price = int(price) * int(n_tickets)
        if available_seats >= n_tickets:
            available_seats -= n_tickets                                

            book = Bookings(
                buser_id=current_user.user_id, # use current_user.id instead of bu_id
                bvenue_id=venue_id, # use venue_id directly
                bshow_id=show_id, # use show_id directly
                num_tickets=n_tickets,
                total_price=t_price
            )

            db.session.add(book)
            db.session.commit()
            flash('Tickets booked successfully!', 'success')
            return redirect(url_for('book_tickets', venue_id=venue_id, show_id=show_id,available_seats=available_seats ))
        else:
            flash('Not enough tickets available!', 'error')
            
    return render_template('book_final.html', venue=venue, show=show, venue_id=venue_id, show_id=show_id,available_seats=available_seats)




@app.route('/userbookings', methods =["GET", "POST"])
@login_required
def userbookings():
    bookings = Bookings.query.filter(Bookings.buser_id==current_user.user_id)
    data = []
    for book in bookings:
        ven = Venues.query.filter(book.bvenue_id==Venues.venue_id).first()
        sho = Shows.query.filter(book.bshow_id==Shows.show_id).first()
        if ven is not None:
            data.append({"venue":ven.venue_name, "show":sho.show_name, "tag":sho.show_tags, "time":sho.show_time,"date":sho.show_date})
    print(data)
    return render_template('user_bookings.html', title='User Bookings', data=data)



@app.route("/get_user_profile", methods=['GET', 'POST'])
@login_required
def get_user_profile():
    # user = User.query(current_user.user_id)
    userdata = {
        "userid": current_user.user_id, 
        "username": current_user.username
    }
    return jsonify  (userdata)


@app.route('/venue/create',methods=['GET','POST'])
@login_required
def create_venue():
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    if request.method=="POST":
        v_name=request.form['v_name']
        v_location=request.form['v_location']
        v_capacity=request.form['v_capacity']
        ven=Venues(
            venue_name=v_name,
            venue_location=v_location,
            venue_capacity=v_capacity
        )
        db.session.add(ven)
        db.session.commit()
        return redirect('/venues')
    #venues=Venues.query.all()
    return render_template('create_venue.html')

@app.route('/venues')
@login_required
def view_venues():
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    venues=Venues.query.all()
    return render_template("view_venues.html",venues=venues)

@app.route('/show/create',methods=['GET','POST'])
@login_required
def create_show():
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    if request.method=="POST":
        s_name=request.form['s_name']
        s_date = datetime.strptime(request.form['s_date'], '%Y-%m-%d').date()
        s_time = datetime.strptime(request.form['s_time'], '%H:%M').time()
        s_tag=request.form['s_tag']
        s_rating=request.form['s_rating']
        s_price=request.form['s_price']
        v_id=request.form['v_id']

        sho=Shows(
            show_name=s_name,
            show_date=s_date,
            show_time=s_time,
            show_tags=s_tag,
            show_rating=s_rating,
            show_price=s_price,
            svenue_id=v_id
        )
        ven=Venues.query.get(v_id)
        sho.y.append(ven)
        db.session.add(sho)
        
        db.session.commit()
        #get request
        return redirect('/dashboard')
    venues=Venues.query.all()

    return render_template('create_show.html',venues=venues)

@app.route('/shows')
def view_shows():
    
    shows=Shows.query.all()
    return render_template("view_shows.html",shows=shows)

@app.route('/every_show/<int:id>',methods=['GET','POST'])
def every_show(id):
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    #take <int:id> or typecast int(id)
    v1=Venues.query.get(id)
    shows=v1.x
    return render_template('onevenue_shows.html',v1=v1,shows=shows)  

@app.route('/assign/<int:id>',methods=['GET','POST'])
def assign(id):
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    s1=Shows.query.get(id)
    if request.method=='GET':
        venues=Venues.query.all()
        return render_template('assign_ven.html',venues=venues,s1=s1)
    
    if request.method=='POST':
        v_id=request.form.get('v_id')
        #by default from string we willl get string so typecast it
        venue=Venues.query.get(int(v_id))
        #y=relationship in many to many backref nothing but list and append is the list method
        s1.y.append(venue)
        db.session.commit()
        return redirect('/venues')


@app.route('/venue/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_venue(id):
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    venue = Venues.query.get(id)
    if request.method == 'POST':
        v_name = request.form['v_name']
        v_location = request.form['v_location']
        v_capacity = request.form['v_capacity']
        venue.venue_name = v_name
        venue.venue_location = v_location
        venue.venue_capacity = v_capacity
        db.session.commit()
        return redirect('/venues')
    return render_template('update_venue.html', venue=venue)

@app.route('/venue/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_venue(id):
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    venue = Venues.query.get(id)
    if request.method == 'POST':
        db.session.delete(venue)
        db.session.commit()
        return redirect('/venues')
    # Set cascade property to delete all associated shows
    # venue.x.cascade = "all, delete"
    return render_template('delete_venue.html', venue=venue)

@app.route('/show/update/<int:show_id>', methods=['GET', 'POST'])
@login_required
def update_show(show_id):
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    show = Shows.query.get(show_id)
    if request.method == 'POST':
        show.show_name = request.form['s_name']
        show.show_tags = request.form['s_tag']
        show.show_rating = request.form['s_rating']
        show.show_price = request.form['s_price']
        db.session.commit()
        return redirect('/shows')
    else:
        return render_template('update_show.html', show=show)

@app.route('/show/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_show(id):
    user = Users.query.filter_by(user_id = current_user.user_id).first()
    if not user.isAdmin():
        return redirect(url_for('adminlogin'))
    show = Shows.query.get(id)
    if request.method == 'POST' or request.method == 'GET':
        db.session.delete(show)
        db.session.commit()
        return redirect('/shows')
    return render_template('delete_venue.html', show=show)

import io
import numpy as np

@app.route('/rating')
@login_required
def rating():
    shows = Shows.query.with_entities(Shows.show_name, Shows.show_rating).all()
    labels = [s[0] for s in shows]
    ratings = [s[1] for s in shows]
    plt.bar(labels, ratings, color=['#FFC107', '#FF9800', '#FF5722', '#F44336'])
    plt.title('Show Ratings')
    plt.xlabel('Shows')
    plt.ylabel('Rating')
    plt.ylim((0, 10))
    plt.grid(True)
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

@app.route('/rating1')
@login_required
def rating1():
    shows = Shows.query.with_entities(Shows.show_name, Shows.price).all()
    labels = [s[0] for s in shows]
    price = [s[1] for s in shows]
    plt.bar(labels, price, color=['#FFC107', '#FF9800', '#FF5722', '#F44336'])
    plt.title('Show Prices')
    plt.xlabel('Shows')
    plt.ylabel('Price')
    plt.ylim((0, 500))
    plt.grid(True)
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')



if __name__=="__main__" :
    app.run(debug=True)
