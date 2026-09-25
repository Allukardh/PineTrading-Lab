import unittest

from tools.thesis_management_anchor_reference import (
    AnchorCapability,
    invalidation_is_usable,
    resolve_anchors,
    target_is_usable,
)


class ThesisManagementAnchorTests(unittest.TestCase):
    def test_full_long(self):
        x=resolve_anchors(
            direction=1,confirm_close=100.0,target=120.0,invalidation=90.0
        )
        self.assertEqual(x.capability,AnchorCapability.FULL)
        self.assertEqual(x.target,120.0)
        self.assertEqual(x.invalidation,90.0)

    def test_full_short(self):
        x=resolve_anchors(
            direction=-1,confirm_close=100.0,target=80.0,invalidation=110.0
        )
        self.assertEqual(x.capability,AnchorCapability.FULL)

    def test_partial_capabilities(self):
        inv=resolve_anchors(
            direction=1,confirm_close=100.0,target=None,invalidation=90.0
        )
        self.assertEqual(inv.capability,AnchorCapability.INVALIDATION_ONLY)
        self.assertEqual(inv.target_issue,"TARGET_MISSING")

        tgt=resolve_anchors(
            direction=1,confirm_close=100.0,target=120.0,invalidation=None
        )
        self.assertEqual(tgt.capability,AnchorCapability.TARGET_ONLY)
        self.assertEqual(tgt.invalidation_issue,"INVALIDATION_MISSING")

        none=resolve_anchors(
            direction=1,confirm_close=100.0,target=None,invalidation=None
        )
        self.assertEqual(none.capability,AnchorCapability.NONE)

    def test_bad_geometry_is_not_synthesized(self):
        x=resolve_anchors(
            direction=1,confirm_close=100.0,target=95.0,invalidation=105.0
        )
        self.assertEqual(x.capability,AnchorCapability.NONE)
        self.assertIsNone(x.target)
        self.assertIsNone(x.invalidation)
        self.assertEqual(x.target_issue,"TARGET_INVALID_GEOMETRY")
        self.assertEqual(x.invalidation_issue,"INVALIDATION_INVALID_GEOMETRY")

    def test_geometry_helpers_are_directionally_symmetric(self):
        self.assertTrue(target_is_usable(1,100.0,101.0))
        self.assertTrue(target_is_usable(-1,100.0,99.0))
        self.assertFalse(target_is_usable(1,100.0,99.0))
        self.assertFalse(target_is_usable(-1,100.0,101.0))

        self.assertTrue(invalidation_is_usable(1,100.0,99.0))
        self.assertTrue(invalidation_is_usable(-1,100.0,101.0))
        self.assertFalse(invalidation_is_usable(1,100.0,101.0))
        self.assertFalse(invalidation_is_usable(-1,100.0,99.0))


if __name__=="__main__":
    unittest.main()
