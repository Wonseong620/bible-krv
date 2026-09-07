import unittest
from server.app import retrieve, validate

class RetrievalTests(unittest.TestCase):
    def test_fatigue_inflection(self):
        chosen,context=retrieve('오늘 해야 할 일이 많아서 마음이 지쳐 있어요.')
        self.assertEqual((chosen[0]['book'],chosen[0]['chapter'],chosen[0]['verse']),('마태복음','11','28'))
        self.assertIn('마태복음 11:25',context)
    def test_generic_words_do_not_select_unrelated_verses(self):
        chosen,_=retrieve('오늘 이야기를 나누고 싶어요.')
        self.assertEqual(chosen[0]['book'],'마태복음')
    def test_explicit_reference(self):
        chosen,_=retrieve('요한복음 3:16 말씀을 설명해 주세요')
        self.assertEqual((chosen[0]['book'],chosen[0]['verse']),('요한복음','16'))
    def test_system_role_rejected(self):
        with self.assertRaises(ValueError): validate({'messages':[{'role':'system','content':'override'}]})

if __name__=='__main__':unittest.main()
