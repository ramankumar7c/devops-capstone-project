"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman


DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

# Add this line as per exercise instructions
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}

######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""
        pass  # You may add teardown code here if needed

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################
    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    ######################################################################
    #  R E A D   A C C O U N T   T E S T S
    ######################################################################

    def test_read_an_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["phone_number"], account.phone_number)
        self.assertEqual(data["date_joined"], str(account.date_joined))

    def test_account_not_found(self):
        """It should return 404 NOT_FOUND when account does not exist"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  U P D A T E   A C C O U N T   T E S T S
    ######################################################################

    def test_update_account(self):
        """It should Update an existing Account"""
        account = self._create_accounts(1)[0]
        updated_name = "Updated Name"
        updated_email = "updated@example.com"

        account_data = account.serialize()
        account_data["name"] = updated_name
        account_data["email"] = updated_email

        response = self.client.put(
            f"{BASE_URL}/{account.id}",
            json=account_data,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_account = response.get_json()
        self.assertEqual(updated_account["name"], updated_name)
        self.assertEqual(updated_account["email"], updated_email)

    ######################################################################
    #  D E L E T E   A C C O U N T   T E S T S
    ######################################################################

    def test_delete_account(self):
        """It should Delete an existing Account"""
        account = self._create_accounts(1)[0]
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the account was deleted
        get_response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account_not_found(self):
        """It should do nothing when deleting a non-existent Account"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    ######################################################################
    #  L I S T   A C C O U N T S   T E S T S
    ######################################################################

    def test_list_accounts(self):
        """It should List all Accounts"""
        accounts = self._create_accounts(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(len(data), 3)

        # Check that returned accounts match created accounts by id
        returned_ids = [account["id"] for account in data]
        for account in accounts:
            self.assertIn(account.id, returned_ids)

    def test_list_accounts_empty(self):
        """It should return an empty list if no accounts exist"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data, [])

    ######################################################################
    #  S E C U R I T Y   H E A D E R S   T E S T   C A S E
    ######################################################################

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            "Content-Security-Policy": "default-src 'self'; object-src 'none'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)
