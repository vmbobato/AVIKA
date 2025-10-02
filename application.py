
from flask import Flask, render_template, request

application = Flask(__name__)

@application.route("/")
def home():
    return render_template("index.html", title="Home - Avika")

@application.route("/about")
def about():
    return render_template("about.html", title="About Us")

@application.route("/pay")
def pay():
    return render_template("pay.html", title="Pay My Bill")

@application.route("/contact")
def contact():
    return render_template("contact.html", title="Contact Us")

@application.route("/pay-client")
def pay_customer():
    return render_template("pay-client.html", title="Client Payment")

@application.route("/pay-patient")
def pay_patient():
    return render_template("pay-patient.html", title="Patient Payment")

@application.route("/find-my-info")
def invoice_help():
    return render_template("find_info.html", title="Find My Info")

@application.errorhandler(404)
def not_found(e):
    return render_template("404.html", title="Not Found"), 404

if __name__ == "__main__":
    application.run(debug=True)
