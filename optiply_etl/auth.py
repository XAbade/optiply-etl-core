import os
import requests
import datetime
import backoff
import json
import pandas as pd
import random
import logging
import uuid
logging.getLogger('backoff').setLevel(logging.CRITICAL)

optiply_base_url = os.environ.get('optiply_base_url', 'https://api.optiply.com/v1')
optiply_dashboard_url = os.environ.get('optiply_dashboard_url', 'https://dashboard.optiply.nl/api')
print("optiply_base_url: ", optiply_base_url)
print("optiply_dashboard_url: ", optiply_dashboard_url)


class OptiplyAuthenticator:
    def __init__(self, credentials, dir_path, output_dir) -> None:
        self.config = credentials
        self.config_path = dir_path
        self.last_refreshed = None
        self.output_dir = output_dir
        self.test = bool(
            credentials.get("hotglue_test", os.environ.get("IS_TEST", False))
        )
        self.requests_table = None
        if self.test:
            self.prepare_testing()

    def prepare_testing(self) -> None:
        # Create the test_output.csv
        self.requests_table = pd.DataFrame(columns=["uri", "method", "payload"])

    # Checks if there's an access_token in the tenant_config.json
    def is_token_valid(self):

        # If we're running a test etl return true, since we're not making any real requests.
        if self.test:
            return True

        # If there is not, return False -> Create new token
        if not self.config.get("access_token"):
            return False

        # If there is, check if it's valid
        # If it is -> use it!
        # If it is not -> Create new token!
        if self.check_access():
            return True
        return False

    def get_access(self):

        print(self.config)
        url = f"{optiply_dashboard_url}/auth/oauth/token?grant_type=password"

        data = {
            "username": self.config.get("username"),
            "password": self.config.get("password"),
        }
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")

        if client_id and client_secret:
            resp = self._request(
                "POST", dummy=True, url=url, data=data, auth=(client_id, client_secret)
            )
        else:
            raise Exception("MISSING CONFIG -- client_id or client_secret")

        self.validate_and_update(resp)

    def validate_and_update(self, resp):

        if 500 <= resp.status_code < 600:
            msg = resp.text
            raise Exception(msg)
        elif 400 <= resp.status_code < 500:
            msg = resp.text
            raise Exception(msg)

        resp = resp.json()

        self.last_refreshed = datetime.datetime.utcnow()

        self.config["access_token"] = resp["access_token"]
        self.config["refresh_token"] = resp["refresh_token"]

        # Updating the tenant-config
        self.update_tenant_config(self.config["access_token"])

    def access_token(self):
        # Check if access token is valid
        if self.is_token_valid():
            # If it is, return it
            return self.config["access_token"]

        # Otherwise, we need to generate access_token and refresh_token
        self.get_access()
        return self.config["access_token"]

    @backoff.on_exception(backoff.constant, Exception, max_tries=10,interval = 20)
    def _request(self, method, dummy=False, **kwargs):
        # Log the request
        print(f"{method} URL=[{kwargs.get('url')}] Payload=[{kwargs.get('data')}]")

        if self.test and method != "GET":
            # Create the mock response
            response = FakeResponse()
            response.status_code = 200

            # remove remoteDAtaSyncedToDate from payload
            payload = kwargs.get("data", None)
            if payload is not None:
                payload = json.loads(payload)
                payload["data"]["attributes"].pop("remoteDataSyncedToDate")

            # append the url, method and payload to the test_output.csv
            self.requests_table = pd.concat(
                [
                    self.requests_table,
                    pd.DataFrame.from_dict(
                        {
                            "uri": [kwargs.get("url")],
                            "method": [method],
                            "payload": [payload],
                        }
                    ),
                ]
            )

            # save the output
            test_dir = f"{self.output_dir}/test_output.csv"
            self.requests_table.to_csv(test_dir, index=False)

            # return the fake response
            return response

        # uptade the headers to use the latest access_token
        if not dummy and self.config.get("access_token", None):
            kwargs.update(
                {
                    "headers": {
                        "Content-Type": "application/vnd.api+json",
                        "Authorization": f'Bearer {self.config["access_token"]}',
                        "User-Agent": "hotglue_py_agent"
                    }
                }
            )

        response = requests.request(method, **kwargs, timeout=300)
        # Log the response status code
        print(f"STATUS CODE {response.status_code}")

        if response.status_code == 401:
            if (
                "UserDetailsService returned null, which is an interface contract violation"
                in response.text
            ):
                raise Exception(
                    "CREDENTIALS ARE WRONG -- update client_secret and client_id"
                )
            else:
                print("DEBUG -- Getting new access_token")
                self.get_access()
        if (
            response.status_code > 400 or response.status_code < 200
        ) and response.status_code not in [404, 409]:
            response.raise_for_status()

        # If the status of the response is not a success code, we raise an Exception
        # TODO: Will this cause an issue because of the backoff?
        if (
            response.status_code not in [200, 201, 204, 409]
            # this error is specific for Suppliers and we will retry the POST without the email
            and not (response.status_code == 400 and "is not a valid address" in response.text)
            # this error is specific for SuppliersProducts that might already been deleted form the customer in our FE OR if is a sellOrder
            and not (response.status_code == 404 and method == 'DELETE')
            and not (response.status_code == 404 and method == 'POST' and ('receiptLines' in kwargs.get("url")))
            and not (response.status_code == 404 and method == 'PATCH' and ('supplierProducts' in kwargs.get("url")))
        ):
            raise Exception(response.text)
        return response


    def update_tenant_config(self, access_token):
        # Read data from tenant_config.json
        json_f = open(self.config_path, "r")
        data = json.load(json_f)

        # Update/Create access_token
        data["apiCredentials"]["access_token"] = access_token

        # Write it on the tenant_config.json
        json_f = open(self.config_path, "w")
        json.dump(data, json_f)
        print("DEBUG -- new access_token written in tenant_config.json")

    def check_access(self):
        """Returns True if the token is valid, false if it's not"""
        # Dummy endpoit to check access
        url = f"{optiply_base_url}/products?page[limit]=1&page[offset]=0"
        response = self._request("GET", url=url)

        if response.status_code == 200:
            print("DEBUG -- access_token in tenant_config.json is valid!")
            return True
        print("DEBUG -- access_token in tenant_config.json is NOT VALID!")
        return False


    def get_data(self,url):
        # Preparing Parameters
        parameters = {
            "page[limit]" : 100,
            "page[offset]": 0,
            "sort": "id"
        }

        # Array to save the data
        data = []

        # Looping on pages
        paginate = 0
        while paginate is not None:

            # Getting the repsonse from the endpoint
            # print(parameters) # ancient loop debugging method
            response = self._request("GET", url=url,params=parameters)
            paginate += 1 

            if response.status_code == 200:
                
                # parsing the repsonse 
                resp = response.json()
                data += resp['data']

                # Stop paginating if the endpoint returns empty array
                if len(response.json()['data']) == 0:
                    paginate = None
                else:
                    parameters.update({"page[offset]": (paginate)*parameters['page[limit]']})
                
            else:
                raise Exception(response.text)

        return data


class FakeResponse(requests.Response):
    def json(self, **kwargs):
        return {"data": {"id": random.randint(0, 1e10),"attributes": {"uuid": str(uuid.uuid4())}}}