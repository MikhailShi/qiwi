#!/usr/bin/python3

# This module is a short implementation of qiwi.con p2p payment API
# for information purposes. No liability accepted upon any
# intended or unintended loss due to the below scripts.
# Those running this module takes full responsibility on any
# possible outcome.
# Part of this code was sourced from https://t.me/ssleg

import os
import time
import uuid
import logging
import requests
from datetime import datetime, timedelta, timezone


class Qiwi:
    # https://developer.qiwi.com/en/p2p-payments/#http
    # https://github.com/QIWI-API/p2p-payments-docs/blob/master/p2p-payments_en.html.md
    headers = {
        "Authorization": "Bearer ",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    base_url = "https://api.qiwi.com/partner/bill/v1/bills/"

    invoice_json = {
        "amount": {
            "currency": "RUB",
            "value": "",
        },
        "expirationDateTime": "",
        "comment": "",
        "customer": {},
        "customFields": {},
    }

    def __init__(self, bill_id):
        self.full_url = self.base_url + bill_id

        if os.getenv("QIWI_SECRET_KEY", False):
            secret_key = os.getenv["QIWI_SECRET_KEY"]
        else:
            # For security reasons it's not advised to store a key in a module
            secret_key = ""  # TODO insert your Secret Key here
            # Use this url to create Secret/Public Keys pair: https://p2p.qiwi.com

        self.headers['Authorization'] += secret_key

    def issue_invoice(self, amount, comment=None, email=None):
        """Method to initiate invoice.
        https://developer.qiwi.com/en/p2p-payments/#API
        """

        if comment is not None:
            self.invoice_json["comment"] = comment
        if email is not None:
            self.invoice_json["customer"] = {"email": email}

        self.invoice_json["amount"]["value"] = "{:.2f}".format(amount)

        # This invoice is valid for 10 minutes, adjust accordingly
        self.invoice_json["expirationDateTime"] = (
                datetime.utcnow().replace(tzinfo=timezone.utc) +
                timedelta(minutes=10)
        ).isoformat(sep="T", timespec="seconds")

        try:
            invoice_response = requests.put(
                self.full_url,
                json=self.invoice_json,
                headers=self.headers,
                timeout=15
            )
            cod = invoice_response.status_code
            invoice_data = invoice_response.json()
            if cod == 200:
                return invoice_data["payUrl"]
            else:
                levent = 'qiwi server error (create bill). code - ' + str(cod) + ', response - ' + str(res)
                logging.error(levent)
                return 'error'

        except Exception as e:
            levent = 'protocol error (create bill): ' + str(e)
            logging.error(levent)
            return 'error'

    def payment_confirmation(self):
        """Receive payment confirmation.
        https://developer.qiwi.com/en/p2p-payments/#cancel
        Statuses:
        =====================================================
        Status   Description                            Final
        WAITING  Invoice issued awaiting for payment    -
        PAID     Invoice paid                           +
        REJECTED Invoice rejected by customer           +
        EXPIRED  Invoice expired. Invoice not paid      +
        """
        try:
            response = requests.get(
                self.full_url,
                headers=self.headers,
                timeout=5
            )
            cod = response.status_code
            res = response.json()
            if cod == 200:
                status = res.get("status")
                return status.get("value")
            else:
                levent = ("qiwi server error (bill status). code - " +
                          str(cod) + ", response - " + str(res))
                logging.error(levent)
                return 'error'

        except Exception as e:
            levent = "protocol error (bill status): " + str(e)
            logging.error(levent)
            return "error"


if __name__ == "__main__":
    key = str(uuid.uuid4())

    # try with 1 rubble bill
    qiwi = Qiwi(key)
    url = qiwi.issue_invoice(amount=1, comment="test")
    print(url)

    for i in range(10):
        print(qiwi.payment_confirmation())
        time.sleep(10)
