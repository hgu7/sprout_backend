from flask import Flask, request
from careerjet_api_client import CareerjetAPIClient
from flask_pymongo import PyMongo
import json
from flask_cors import CORS, cross_origin
import os

# twilio
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

mongo_password = os.environ.get("MONGO_PASSWORD")
app = Flask(__name__)
app.config["MONGO_URI"] = f"mongodb+srv://sprout-user:{mongo_password}@cluster0.db8lg5b.mongodb.net/db"
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

account_sid = os.environ.get("ACCOUNT_SID")
auth_token = os.environ.get("AUTH_TOKEN")
twilio_number = "+16695872010"


client = Client(account_sid, auth_token)


mongo = PyMongo(app)

cj  =  CareerjetAPIClient("en_US");

@app.route("/")
def index():
    return "hello world"


@app.route("/lookup", methods = ['POST'])
def lookup():

    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        data = request.json


        location = 'college park, maryland'
        keywords = ''
        contract_period = ''


        if 'location' in data.keys():
            location = data['location']
        
        if 'keywords' in data.keys():
            keywords = data['keywords']
        
        result_json = cj.search({
                        'location'    : location,
                        'keywords'    : keywords,
                        'contractperiod': contract_period,
                        'affid'       : '213e213hd12344552',
                        'user_ip'     : '11.22.33.44',
                        'url'         : 'http://www.example.com/jobsearch?q=python&l=london',
                        'user_agent'  : 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0'
                      });

    return result_json



@app.route("/add_user", methods = ['POST'])
@cross_origin()
def add_user():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        match_profile = None
        data = request.json
        mentor = False        
        if data["role"] == "mentor":
            mentor = True
            mentor = {
                "name": data["name"],
                "careerArea": data["careerArea"],
                "job": data["job"],
                "location": data["location"],
                "matched": False,
                "email": data["email"],
                "phoneNumber": data["phoneNumber"],
                "interests": data["interests"]
            }
            
            mongo.db.mentors.insert_one(mentor)
            match_profile= match(False, data["email"])

        elif data["role"] == "mentee":
            mentee = {
                "name": data["name"],
                "careerArea": data["careerArea"],
                "job": data["job"],
                "location": data["location"],
                "matched": False,
                "email": data["email"],
                "phoneNumber": data["phoneNumber"],
                "interests": data["interests"]
            }

            mongo.db.mentees.insert_one(mentee)

            match_profile= match(True, data["email"])


        if match_profile:
            return match_profile
    
    return {"status": "error"}




def match(mentee, email):
    match_profile = None

    if mentee:
        profile = mongo.db.mentees.find_one({"email": email})
        match_profile = mongo.db.mentors.find_one({
                "careerArea": profile['careerArea'], 
                "matched": False
            })

    else:
        profile = mongo.db.mentors.find_one({"email": email})
        match_profile = mongo.db.mentees.find_one({
                "careerArea": profile['careerArea'],
                "matched": False
            })

    
    if match_profile:
        mentee_name = ""
        mentor_name = ""
        mentee_phone = ""
        mentor_phone = ""
        if mentee:
            new_profile = profile
            new_profile['matched'] = True
            new_profile['mentor_name'] = match_profile['name']
            new_profile['mentor_phone'] = match_profile['phoneNumber']

            mongo.db.mentees.update_one(
                {
                    'email': profile['email']
                },
                { "$set": new_profile}
            )

            mentor_profile = match_profile
            mentor_profile['matched'] = True
            mentor_profile['mentee_name'] = profile['name']
            mentor_profile['mentee_phone'] = profile['phoneNumber']

            mongo.db.mentors.update_one(
                {
                    'email': match_profile['email']
                },
                { "$set": mentor_profile}
            )

            mentee_phone = profile['phoneNumber']
            mentee_name = profile['name']
            mentor_phone = match_profile['phoneNumber']
            mentor_name = match_profile['name']

        else:
            new_profile = profile
            new_profile['matched'] = True
            new_profile['mentee_name'] = match_profile['name']
            new_profile['mentee_phone'] = match_profile['phoneNumber']

            mongo.db.mentors.update_one(
                {
                    'email': profile['email']
                },
                { "$set": new_profile}
            )

            mentee_profile = match_profile
            mentee_profile['matched'] = True
            mentee_profile['mentor_name'] = profile['name']
            mentee_profile['mentor_phone'] = profile['phoneNumber']

            mongo.db.mentees.update_one(
                {
                    'email': match_profile['email']
                },
                { "$set": mentee_profile}
            )

            mentee_phone = profile['phoneNumber']
            mentee_name = profile['name']
            mentor_phone = match_profile['phoneNumber']
            mentor_name = match_profile['name']


        try:
          # This could potentially throw an exception!
            message1 = client.messages.create(
                to=str(mentor_phone), 
                from_=twilio_number,
                body=f"You have been matched with a mentee!\nHere is their information:\nName: {mentee_name}\nPhone Number: {mentee_phone}")

            message2 = client.messages.create(
                to=str(mentee_phone), 
                from_=twilio_number,
                body=f"You have been matched with a mentor!\nHere is their information:\nName: {mentor_name}\nPhone Number: {mentor_phone}")

        except TwilioRestException as err:
          # Implement your fallback code here
          print(err)

        return { 
            "status": "ok",
            "match": {
                "name": match_profile['name'],
                "phone": match_profile['phoneNumber'],
                "interests": match_profile['interests'],
                "job": match_profile['job']
            }
        
        }
    
    return { "status": "match not found", "match": "none"}




@app.route('/housing', methods=['POST'])
@cross_origin()
def housingEval():


    
    content_type = request.headers.get('Content-Type')

    toReturn = []

    # If a form is submitted
    if request.method == "POST":
        data = request.json
        CreditScore = data["creditScore"]
        LTV = float(data["loanAmount"]) / float(data["appraisedValue"])
        totDebt = float(data["cardPayment"]) + float(data["carPayment"]) + float(data["mortgagePayment"])
        DTI = totDebt / float(data["monthlyIncome"])
        FEDTI = float(data["mortgagePayment"]) / float(data["monthlyIncome"])
    
        details = ""

        # check credit score
        if(int(CreditScore) < 640):
            details += "1"   # no
            toReturn.append("We encourage you to consider techniques in raising your credit score. Pay down your revolving credit balances. If you have the funds to pay more than your minimum payment each month, you should do so. New habits to consider include to increase your credit limit and to check your credit report for errors. Also, ask to have negative entries that are paid off removed from your credit report.")
        else:
            details += "2"   # yes
            toReturn.append("Your credit score is acceptable, if not stellar. Continue to  increase your credit limit and to check your credit report for errors. Also, ask to have negative entries that are paid off removed from your credit report.")

        # check LTV
        if float(LTV) > 0.95:
            details += "3"   # no
            toReturn.append("Your LTV score is too high. In essence, increasing the amount of your down payment lowers the total amount of money that you're asking to borrow, which automatically lowers your LTV. Make a larger down payment. Saving for a big down payment may test your patience if you're really eager to get into a house or car, but it can be worth it in the long run.")
        elif float(LTV) < 0.80:
            details += "5"   # yes
            toReturn.append("Your LTV score is excellent. Continue to set your sights on affordable targets that are within the scope of your budget, income, and debt.")
        else:
            details += "4"   # maybe
            toReturn.append("Your LTV score is acceptable, but could be improved to lower interest rates. Set your sights on more affordable targets. Consider PMI (Private mortgage insurance), which is a type of mortgage insurance you might be required to pay for if you have a conventional loan. Like other kinds of mortgage insurance, PMI protects the lender—not you—if you stop making payments on your loan.")

        # check DTI
        if float(DTI) > 0.43:
            details += "6"   # no - can lower DTI by transfer high interest loans to a low interest credit card although having too many credit cards can also negatively impact your ability to purchase a home
            toReturn.append("Your DTI is too high. Consider lowering your DTI by transfering high interest loans to a low interest credit card. Consider the fact that this may negatively impact home buying power. In all, avoid taking on more debt.")
        elif float(DTI) <= 0.36:
            toReturn.append("Your DTI score is superb. Continue to recalculate your debt-to-income ratio monthly to ensure your position.")
            details += "8"   # yes -
        else: 
            details += "7"   # maybe
            toReturn.append("Your DTI score is decent, but could use active improvement. Increase the amount you pay monthly toward your debt. Extra payments can help lower your overall debt more quickly.")

        # check FEDTI
        if float(FEDTI) > 0.28:
            details += "9"   # no
            toReturn.append("Your FEDTI score is too high. Some of the best ways to improve debt-to-income ratio include paying down revolving or installment debts, reducing housing costs, and increasing income. A lower DTI can increase the amount of home you may be able to afford when qualifying to mortgage a property.")
        else:
            details += "0"   # yes
            toReturn.append("Your FEDTI score is great. Continue to exercise responsible financial habits.")


        ## DETERMINE FINAL EVAL - YES/ POSSIBLY/ MAYBE / NO
        eval = 0

        #no
        if "1" in details and "3" in details and "6" in details and "9" in details:
            eval = 0
            toReturn.append("You would not be approved to secure a home loan at this time.")
        # definitely yes
        elif "2" in details and "5" in details and "8" in details and "0" in details:
            eval = 1
            toReturn.append("You would be approved to secure a home loan at this time. Congrats!")
        # maybe yes
        elif "2" in details and "4" in details and "4" in details and "0" in details:
            eval = 2
            toReturn.append("\You would be approved to secure a home loan at this time, but your interest rates may be high. Consider improving your finances with the above advice.")
        # maybe
        else:
            eval = 3
            toReturn.append("You may or may not be approved to secure a home loan at this time with a favorable interest rate. We encourage you to take time to reorganize your finances and better understand opportunities for improvement.")

        result_json = json.dumps(toReturn)



        # Put inputs to dataframe
        #X = pd.DataFrame([[height, weight]], columns = ["Height", "Weight"])
        
    return {"result": result_json}


if __name__ == "__main__":
  app.run()