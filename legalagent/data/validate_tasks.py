"""Validation for the 50-task pilot; run after building tasks."""
import collections, hashlib, json, unittest

from ..paths import DATA, TASKS

BASE=TASKS

def read(path):
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]

class DatasetValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=read(DATA/'labor_subset.jsonl')
        cls.task=read(BASE/'tasks_all_50_reviewed.jsonl')
        cls.idx={(x['law_id'],x['article_number']):x for x in cls.corpus}
    def test_record_count_types_unique(self):
        self.assertEqual(len(self.task),50)
        self.assertEqual(len({t['task_id'] for t in self.task}),50)
        self.assertEqual(len({t['prompt'] for t in self.task}),50)
        self.assertEqual(dict(collections.Counter(t['task_type'] for t in self.task)),{'direct_retrieval':15,'fact_application':20,'multi_article':10,'insufficient_information':5})
    def test_all_sources_present_hash_correct(self):
        for t in self.task:
            with self.subTest(tid=t['task_id']):
                self.assertEqual(t['applicable_date'],'2024-06-01')
                ids=[]
                for e in t['source_evidence']:
                    law,num=e['article_id'].rsplit(':',1)
                    row=self.idx[(law,int(num))]
                    self.assertEqual(row['text_sha256'],hashlib.sha256(row['text'].encode('utf-8')).hexdigest())
                    self.assertEqual(row['text_sha256'],e['text_sha256'])
                    self.assertEqual(row['version_id'],e['version_id'])
                    self.assertIn(e['supporting_quote'],row['text'])
                    self.assertLessEqual(row['effective_from'],t['applicable_date'])
                    self.assertTrue(row['effective_to'] is None or t['applicable_date'] < row['effective_to'])
                    ids.append(e['article_id'])
                self.assertEqual(set(ids),set(t['gold_article_ids']))
                self.assertEqual(len(t['gold_article_ids']),len(set(t['gold_article_ids'])))
                self.assertTrue(t['expected_answer_points'])
                self.assertTrue(t['gold_issues'])
                self.assertEqual(t['review']['independent_human_legal_expert_review'],'pending')
    def test_fixed_splits(self):
        ids=set()
        for group,expected in [('train',35),('dev',10),('test',5)]:
            labeled=read(BASE/f'tasks_{group}_labeled.jsonl')
            prompts=read(BASE/f'tasks_{group}_prompts_only.jsonl')
            self.assertEqual(len(labeled),expected)
            self.assertEqual(len(prompts),expected)
            self.assertEqual({x['task_id'] for x in labeled},{x['task_id'] for x in prompts})
            self.assertFalse(ids.intersection({x['task_id'] for x in labeled}))
            ids.update(x['task_id'] for x in labeled)
            for x in prompts:
                self.assertEqual(set(x),{'task_id','prompt','jurisdiction','applicable_date'})
                self.assertNotIn('gold_',json.dumps(x))
        self.assertEqual(ids,{t['task_id'] for t in self.task})
    def test_unsafe_corpus_article_not_labelled(self):
        # These older provisions require cross-law/higher-ranked-law qualification; avoid as hard gold.
        used=set(e['article_id'] for t in self.task for e in t['source_evidence'])
        self.assertFalse({'labor_law:82','labor_law:36','labor_law:62'} & used)
    def test_insufficient_facts_explicit(self):
        cases=[t for t in self.task if t['task_type']=='insufficient_information']
        self.assertEqual(len(cases),5)
        self.assertTrue(all(t['missing_facts'] for t in cases))

if __name__=='__main__':
    unittest.main(verbosity=2)
