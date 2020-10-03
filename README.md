# QIWI
Brief implementation of https://p2p.qiwi.com API.

p2p Secret Key is needed to run this module.


## Choice 1. Local file qiwi.py for invoice issue and for checking the invoice status


MAC OS, python 3.8.5:
```
> virtualenv venv
> . venv/bin/activate
> pip install -r requirements_local.txt
> export QIWI_SECRET_KEY=your_secret_key_from_https://p2p.qiwi.com
> python qiwi.py
```


## Choice 2. Flask web-app with API to receive Invoice Payment Notifications

For this web-app you will need ssl certificates to receive Invoice Payment Notifications (see. [documentation](https://developer.qiwi.com/en/p2p-payments/?php#notification))

You might want to run this repository with [IBM Cloud CF](https://cloud.ibm.com/docs/cloud-foundry?topic=cloud-foundry-getting-started-python) for free.
Secret Key should be passed through manifest.yml or via CF SSH. Also you need to set application name, which should have proper route address assigned.

For trying flask app.py locally (MAC OS, python 3.8.5):
```
> virtualenv venv
> . venv/bin/activate
> pip install -r requirements.txt
> export QIWI_SECRET_KEY=your_secret_key_from_https://p2p.qiwi.com
> flask run
```

P.S. Payment cancellation doesn't work for the reason yet unknown.

