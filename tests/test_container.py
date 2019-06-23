from unittest import TestCase
from utils import Container, load_csv

containers = load_csv("containers")
names = load_csv("nouns")


class TestContainer(TestCase):
    def test_name(self):
        for con_id in containers.keys():
            con = Container(con_id, explicit=True)
            self.assertTrue(con.name in names[con_id])
