from flask import Flask, render_template, request, session, logging, url_for, redirect, flash
from flask_login import current_user
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
from passlib.hash import sha256_crypt



engine = create_engine("mysql+pymysql://root:root@localhost/user")
db = scoped_session(sessionmaker(bind=engine))
app = Flask(__name__)

@app.route("/")
def home():

    return render_template("home.html")

#register form
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        existingUserCheck = 'no'
        fuelHistory = 'no'

        if password == confirm:
            db.execute("INSERT INTO users(username, password, existingUser) VALUES(:username, :password, :existingUser)",
                                          {"username":username, "password":password, "existingUser":existingUserCheck})
            db.execute("INSERT INTO FuelHistory(username) VALUES(:username)",{"username":username})
            db.execute("UPDATE FuelHistory SET History='no' WHERE username=:username", {"username":username})

            db.commit()
            flash("You are now registered and ready to login!", "success")
            return redirect(url_for('login'))
        else:
            flash("Passwords do not match", "danger")
            return render_template("register.html")

    return render_template("register.html")

#login
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        session['username'] = request.form.get("username")
        session['password'] = request.form.get("password")

        usernameData = db.execute("SELECT username FROM users WHERE username=:username", {"username":session['username']}).fetchone()
        passwordData = db.execute("SELECT password FROM users WHERE username=:username",{"username":session['username']}).fetchone()
        checkNewUser = db.execute("SELECT existingUser FROM users WHERE username=:username", {"username":session['username']}).fetchone()


        if usernameData is None:
            flash("No account found! Please try again or create an account","danger")
            return render_template("login.html")
        else:
            for password_data in passwordData:
                if session['password'] == password_data:
                    if checkNewUser[0] == "no":
                        session["log"] = True
                        flash("You are now logged in! Please complete your profile", "success")
                        return redirect(url_for('userProfile'))
                    else:
                        session["log"] = True
                        flash("Welcome back!", "success")
                        return render_template("home.html")
                else:
                    flash("password incorrect!", "danger")
                    return render_template("login.html")

    return render_template("login.html")


#photo
@app.route("/photo")
def photo():
    return render_template("photo.html")

#user profile update
@app.route("/userProfile", methods=["GET","POST"])
def userProfile():
    username = session['username']
    newUserCheck = db.execute("SELECT existingUser FROM users WHERE username=:username", {"username":session['username']}).fetchone()

    if newUserCheck[0] == 'no':
        if request.method == "POST":

            fullName = request.form.get("fullName")
            address1 = request.form.get("address1")
            address2 = request.form.get("address2")
            city = request.form.get("city")
            state = request.form.get("state")
            zipCode = request.form.get("zip")

            if len(zipCode) > 3:
                db.execute("UPDATE users SET fullName=:fullName WHERE username=:username", {"fullName":fullName, "username":username})
                db.execute("UPDATE users SET address1=:address1 WHERE username=:username", {"address1": address1, "username":username})
                db.execute("UPDATE users SET city=:city WHERE username=:username", {"city": city, "username":username})
                db.execute("UPDATE users SET state=:state WHERE username=:username", {"state": state, "username":username})
                db.execute("UPDATE users SET zipcode=:zipCode WHERE username=:username", {"zipCode": zipCode, "username":username})
                db.execute("UPDATE users SET existingUser='yes' WHERE username=:username", {"username":username})
                db.commit()
                flash("Profile has been updated", "success")
                test = db.execute("SELECT fullName, address1, city, state, zipcode FROM users WHERE username=:username", {"username":username})
                data = test.fetchall()
                return render_template("completedUserProfile.html", data=data)
    else:
        test = db.execute("SELECT fullName, address1, city, state, zipcode FROM users WHERE username=:username", {"username":username})
        data = test.fetchall()
        return render_template("completedUserProfile.html", data=data)

    return render_template("userProfile.html")

#completed user profile form
@app.route("/completedUserProfile", methods=["GET","POST"])
def completedUserProfile():

    return render_template("completedUserProfile.html")

#fuel Quote Request
@app.route("/fuelQuote", methods=["GET", "POST"])
def fuelQuote():
    # defaulted to no for history and if submitted request then change it to yes in DB
    # if history is yes in DB then apply discounted price
    data = db.execute("SELECT state FROM users WHERE username=:username", {"username":session['username']}).fetchone()

    if request.method == 'POST':
    
        if request.form['action'] == 'Calculate':
            #locally used varibles
            state = db.execute("SELECT state FROM users WHERE username=:username", {"username":session['username']}).fetchone()
            fuelHistory =  db.execute("SELECT History FROM FuelHistory WHERE username=:username", {"username":session['username']}).fetchone()

            
            CurrentPrice = 1.50

            date = request.form.get("delivery-date")
            gallons = request.form.get("gallonsRequested")


            db.execute("UPDATE FuelHistory SET Date=:date WHERE username=:username", {"date": date, "username":session['username']})
            db.execute("UPDATE FuelHistory SET Gallons=:gallons WHERE username=:username", {"gallons": gallons, "username":session['username']})
            db.commit()



            SuggestedPrice = 0


            TotalDue = 0

            Discount = 0


            #location factor
            if (state[0] == "TX"):
                Discount = 0.02
                
            else:
                Discount = 0.04

            
            #checking fuel quote history
            if (fuelHistory[0] == "yes"):

                Discount = Discount - 0.01
                

            #checking if gallons requested is more than 1000
            if (gallons > "1000"):
                Discount = (Discount + 0.02)
                
            else:
                Discount = Discount + 0.03


            # Company Profit Factor
            Discount = Discount + .1
            
            #checking season (rate fluctuation)
            datee = datetime.datetime.strptime(date, "%Y-%m-%d")

            if(datee.month == 6 or datee.month == 7 or datee.month == 8):
                Discount = Discount + 0.04

            else:
                Discount = Discount + 0.03
                


            suggestedPrice = CurrentPrice * (Discount) + CurrentPrice
            TotalDue = int(gallons) * suggestedPrice


            db.execute("UPDATE FuelHistory SET SuggestedPrice=:suggestedPrice WHERE username=:username", {"suggestedPrice":suggestedPrice, "username":session['username']})
            db.execute("UPDATE FuelHistory SET Total=:TotalDue WHERE username=:username", {"TotalDue":TotalDue, "username":session['username']})
            db.commit()

            test = db.execute("SELECT state, NULL as test, NULL as test2, NULL as test3 FROM users WHERE username=:username UNION SELECT Date, Gallons, SuggestedPrice, Total FROM FuelHistory WHERE username=:username", {"username":session['username']})
            
            data2 = test.fetchall()

            return render_template("Calculated.html", data2 = data2)
        elif request.form['action'] == 'Buy':
            
            db.execute("UPDATE FuelHistory SET History='yes' WHERE username=:username", {"username":session['username']})
            db.commit()

            test = db.execute("SELECT state, NULL as test, NULL as test2, NULL as test3, NULL as test4 FROM users WHERE username=:username UNION SELECT Date, Gallons, SuggestedPrice, Total, History FROM FuelHistory WHERE username=:username", {"username":session['username']})
            
            data2 = test.fetchall()

            return render_template("FuelReceipt.html", data2 = data2)


    return render_template("fuelQuote.html", data = data)


@app.route("/fuelQuoteHistory", methods=["GET","POST"])
def fuelQuoteHistory():
    
    fuelHistCheck = db.execute("SELECT History FROM FuelHistory WHERE username=:username", {"username":session['username']}).fetchone()
    
    test = db.execute("SELECT state, NULL as test, NULL as test2, NULL as test3, NULL as test4 FROM users WHERE username=:username UNION SELECT Date, Gallons, SuggestedPrice, Total, History FROM FuelHistory WHERE username=:username", {"username":session['username']})
            
    data2 = test.fetchall()

    if fuelHistCheck[0] == 'yes':
        return render_template("FuelReceipt.html", data2 = data2)
    
    return render_template("fuelQuoteHistory.html")



@app.route("/adminHistory", methods=["GET","POST"])
def adminHistory():

    fuelHistCheck = 'yes'

    if(session['username']=='Admin'):
            test = db.execute("SELECT * FROM FuelHistory WHERE History=:fuelHistCheck", {"fuelHistCheck":fuelHistCheck}).fetchall()
            data=test
    else:
        flash("You are not an admin to view this page", "danger")
        return redirect(url_for('home'))

    

    return render_template("adminHistory.html", data=data)



#logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for('login'))

if __name__=="__main__":
    app.secret_key = "1234567"
    app.run(debug=True)