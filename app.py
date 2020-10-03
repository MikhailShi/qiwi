import time
import datetime
import uuid
import os
import logging
from collections import defaultdict
from flask import Flask, request, flash, render_template, Response
from flask_restful import Api, Resource
from qiwi import Qiwi, check_bill, issue_invoice, payment_confirmation, payment_cancellation

app = Flask(__name__)
api = Api(app)

# global variable for illustration purposes only
# there should be Redis or similar service involved
bill_paid = defaultdict(str)
Qiwi().init_key()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        account = request.form.get('account')
        phone = request.form.get('phone')
        email = request.form.get('email')
        amount = request.form.get('amount')
        comment = request.form.get('comment')
        minutes = request.form.get('minutes')

        error = None
        logging.debug("Starting page POST")

        if amount is None or not any(v.isnumeric() for v in amount.split(".", 1)):
            error = "Numeric amount is required!"
        else:
            amount = float(amount)

        if minutes is not None and not minutes.isnumeric():
            error = "Integer value of minute(s) is(are) required!"
        elif minutes is not None:
            minutes = int(minutes)
        else:
            minutes = 5

        if error is None:

            bill_id = str(uuid.uuid4())
            payment_url = issue_invoice(bill_id,amount, comment, email, minutes)
            print(f"Invoice issued for {bill_id}, {payment_url}")
            return render_template('payment.html',
                                   bill_id=bill_id, payment_url=payment_url)

        flash(error)

    return render_template('create.html')


@app.route('/payment_confirmation/<bill_id>')
def confirm_payment(bill_id):
    print(f"Payment confirmation requested for {bill_id}")
    # bill_id = str(bill_id)
    pay_status = payment_confirmation(bill_id)
    print(pay_status)
    if pay_status == "PAID":
        print(f"Bill {bill_id} paid")
        bill_paid[bill_id] = "PAID"
    elif pay_status == "EXPIRED":
        print(f"Bill {bill_id} expired")
        bill_paid[bill_id] = "EXPIRED"
    print(bill_paid)
    return ("", 202)


@app.route('/payment_cancellation/<bill_id>')
def cancel_payment(bill_id):
    # bill_id = str(bill_id)
    print(f"Payment CANCELLATION requested for {bill_id}")

    pay_status = payment_cancellation(bill_id)
    print(pay_status)
    bill_paid[bill_id] = "REJECTED" if pay_status == "REJECTED" else ""
    print(f"Bill {bill_id} rejected")
    print(bill_paid)
    return ("", 204)


@app.route('/waiting_for_payment/<uuid:bill_id>')
def waiting_for_payment(bill_id):
    print(f"Waiting for payment confirmation for {bill_id}")
    return Response(looking_for_confirmation(bill_id), mimetype='text/event-stream')


def looking_for_confirmation(bill_id):
    print("waiting")
    bill_id = str(bill_id)
    t = time.time()
    yield "data:Waiting...\n\n"
    while not bill_paid[bill_id]:
        print(f"Check payment confirmation for {bill_id}")
        time.sleep(10)
        print("waiting", bill_paid[bill_id])
        # stop checks after 10 minutes
        if time.time() - t > 60 * 10:
            yield "data: Bill was not paid!\n\n"
            return

    print(f"Receiving data for {bill_id}: {bill_paid[bill_id]}")

    if bill_paid[bill_id] == "PAID":
        t = datetime.datetime.now().strftime("%d-%m-%YT%H:%M:%S")
        yield f"data: Bill was paid! {t}\n\n"
    elif bill_paid[bill_id] == "REJECTED":
        print("rejected")
        yield "data: Bill was rejected!\n\n"
    elif bill_paid[bill_id] == "EXPIRED":
        yield "data: Bill was expired!\n\n"
    return


class Confirmation(Resource):
    def post(self):
        print("Received POST confirmation")
        hash_received = request.headers.get("X-Api-Signature-SHA256")
        print(f"HASH received {hash_received}")
        json_data = request.get_json(force=True)

        global bill_paid
        if check_bill(hash_received, json_data):
            bill_id = json_data["bill"].get("billId")
            bill_paid[bill_id] = "PAID"  # json_data["bill"]["status"].get("value")
            print(f"Setting as paid {bill_id}")
            # need to return 200 to stop repeating notifications
            return {"error": "0"}, 200, {"Content-Type": "application/json"}
        return {}, 400


api.add_resource(Confirmation, '/confirmation')

port = os.getenv('PORT', '8000')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(port))
