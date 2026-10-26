# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from werkzeug.exceptions import NotFound

from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.website.tools import MockRequest

from ..controllers.website_sale import WebsiteSale


@tagged("post_install", "-at_install")
class TestAssortmentController(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="assortment_intersection",
            groups="base.group_portal",
            context={"no_reset_password": True},
        )
        cls.website = cls.env["website"].search([], limit=1)
        cls.products = cls.env["product.product"].create(
            [{"name": f"Assortment product {i}"} for i in range(3)]
        )
        cls.controller = WebsiteSale()

    def _create_assortment(self, name, products):
        return self.env["ir.filters"].create(
            {
                "name": name,
                "model_id": "product.product",
                "is_assortment": True,
                "website_availability": "no_show",
                "domain": repr([("id", "in", products.ids)]),
                "partner_domain": repr([("id", "=", self.user.partner_id.id)]),
            }
        )

    def test_multiple_assortments(self):
        self._create_assortment("A", self.products[:2])
        self._create_assortment("B", self.products[1:])
        with MockRequest(self.env(user=self.user), website=self.website):
            self.assertEqual(
                self.controller._get_products_allowed(),
                ({self.products[1].id}, True),
            )
            self.assertEqual(
                self.controller._get_search_options()["allowed_product_domain"],
                [("product_variant_ids", "in", [self.products[1].id])],
            )
            with self.assertRaises(NotFound):
                self.controller.product(self.products[0].product_tmpl_id)

    def test_empty_intersection(self):
        first = self._create_assortment("A", self.products[:1])
        self._create_assortment("B", self.products[1:2])
        self._create_assortment("C", self.products)
        with MockRequest(self.env(user=self.user), website=self.website):
            self.assertEqual(self.controller._get_products_allowed(), (set(), True))
            first.domain = repr([("id", "in", [])])
            self.assertEqual(self.controller._get_products_allowed(), (set(), True))

    def test_no_applicable_assortment(self):
        assortment = self._create_assortment("A", self.products[:1])
        assortment.partner_domain = repr([("id", "=", 0)])
        with MockRequest(self.env(user=self.user), website=self.website):
            self.assertEqual(self.controller._get_products_allowed(), (set(), False))
            self.assertNotIn(
                "allowed_product_domain", self.controller._get_search_options()
            )
