import unittest
from app.crochet_engine.pipeline import design_to_shape_graph, compile_design

class TestCorePipeline(unittest.TestCase):
    def design(self):
        return {
            "subject":"Orsetto di prova",
            "overall_confidence":0.9,
            "parts":[
                {"id":"body","label":"Corpo","role":"body","count":1,"parent_id":None,"symmetry_group":None,"estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":6,"confidence":.95,"construction":"forma principale"},
                {"id":"head","label":"Testa","role":"head","count":1,"parent_id":"body","symmetry_group":None,"estimated_height_cm":6,"estimated_width_cm":6,"estimated_depth_cm":5,"confidence":.95,"construction":"forma ovale", "center_front":{"x":.56,"y":.32}, "center_side":{"x":.55,"y":.42}},
                {"id":"arm","label":"Braccio","role":"arm","count":2,"parent_id":"body","symmetry_group":"arms","estimated_height_cm":4,"estimated_width_cm":2,"estimated_depth_cm":2,"confidence":.9,"construction":"tubo"},
                {"id":"eye","label":"Occhio","role":"eye","count":2,"parent_id":"head","symmetry_group":"eyes","estimated_height_cm":1,"estimated_width_cm":1,"estimated_depth_cm":.6,"confidence":.9,"construction":"ricamo"},
            ]
        }

    def test_design_compiles_without_ai_reinterpretation(self):
        out=compile_design(self.design(),15,2.5)
        self.assertTrue(out["graph_validation"]["ok"])
        self.assertIn("PROJECT", out["pattern"])
        self.assertGreaterEqual(len(out["shape_graph"]["nodes"]), 5)
        self.assertTrue(any("tubo_sc" in str(x) for x in out["techniques"]))


    def test_symmetric_parts_default_to_depth_offset(self):
        design=self.design()
        g=design_to_shape_graph(design,15)
        arms=[n for n in g["nodes"] if n.get("symmetry_group")=="arms"]
        self.assertEqual(len(arms),2)
        self.assertAlmostEqual(arms[0]["position"]["x"], arms[1]["position"]["x"], places=6)
        self.assertNotEqual(arms[0]["position"]["y"], arms[1]["position"]["y"])

    def test_front_symmetry_can_override_to_horizontal_axis(self):
        design=self.design()
        for part in design["parts"]:
            if part.get("id")=="arm":
                part["symmetry_axis"]="front"
        g=design_to_shape_graph(design,15)
        arms=[n for n in g["nodes"] if n.get("symmetry_group")=="arms"]
        self.assertNotEqual(arms[0]["position"]["x"], arms[1]["position"]["x"])
        self.assertAlmostEqual(arms[0]["position"]["y"], arms[1]["position"]["y"], places=6)


    def test_image_anchor_represents_part_center_not_profile_base(self):
        design=self.design()
        g=design_to_shape_graph(design,15)
        # The body/head profiles are authored from z=0, but their semantic image
        # anchors represent their visible centers. The compiler must offset the
        # node position so the profile midpoint lands on that anchor.
        head=next(n for n in g["nodes"] if n["id"]=="head")
        from app.crochet_engine.pipeline import _rotate_vector
        anchor=design["parts"][1]["center_front"]
        h=6 * 15 / 10
        expected=(anchor["x"]-.5)*max(9,15*.35), (design["parts"][1]["center_side"]["x"]-.5)*15*.35, (1-anchor["y"])*15
        off=_rotate_vector((0.0,0.0,h*.5), type("R",(),head["rotation"])())
        actual=(head["position"]["x"]+off[0], head["position"]["y"]+off[1], head["position"]["z"]+off[2])
        for a,b in zip(actual,expected):
            self.assertAlmostEqual(a,b,places=5)

    def test_parent_and_symmetry_are_preserved(self):
        g=design_to_shape_graph(self.design(),15)
        self.assertEqual(len(g["edges"]), len(g["nodes"])-1)
        arm_nodes=[n for n in g["nodes"] if n.get("symmetry_group")=="arms"]
        self.assertEqual(len(arm_nodes),2)

if __name__ == '__main__': unittest.main()

class TestGeometryShapeCues(unittest.TestCase):
    def test_distinctive_shape_cues_change_primitive(self):
        from app.crochet_engine.pipeline import design_to_shape_graph
        base = {
            'subject':'test', 'overall_confidence':.9,
            'parts': [
                {'id':'body','label':'corpo','role':'body','count':1,'parent_id':None,'symmetry_group':None,
                 'estimated_height_cm':10,'estimated_width_cm':6,'estimated_depth_cm':4,
                 'center_front':{'x':.5,'y':.5},'center_side':{'x':.5,'y':.5},'depth_hint':'front',
                 'confidence':.9,'construction':'forma principale','notes':''},
                {'id':'tail','label':'coda lunga affusolata','role':'tail','count':1,'parent_id':'body','symmetry_group':None,
                 'estimated_height_cm':8,'estimated_width_cm':2,'estimated_depth_cm':1.5,
                 'center_front':{'x':.2,'y':.6},'center_side':{'x':.2,'y':.6},'depth_hint':'side',
                 'confidence':.9,'construction':'tubo affusolato','notes':'lunga e appuntita'}]}
        g=design_to_shape_graph(base,15)
        tail=next(n for n in g['nodes'] if n['id']=='tail')
        self.assertEqual(tail['primitive'],'tail')
        self.assertLess(tail['profile'][-1]['diameter_cm'], tail['profile'][0]['diameter_cm'])


class TestIdentityContract(unittest.TestCase):
    def test_identity_evidence_is_required_by_design_schema(self):
        from app.crochet_engine.design_model import DESIGN_SCHEMA
        self.assertIn("identity_evidence", DESIGN_SCHEMA["required"])
        self.assertIn("identity_alternatives", DESIGN_SCHEMA["required"])

if __name__ == '__main__':
    unittest.main()
