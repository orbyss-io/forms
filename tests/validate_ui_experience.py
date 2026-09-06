from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "extensions/program-kit-governance/scripts"))
import ui_content
import ui_contracts
import ui_profile
import ui_svg
import ui_tokens
import ui_evaluation
import bootstrap_context


class Html(HTMLParser):
    def __init__(self, value):
        super().__init__()
        self.tags, self.text, self.scripts, self.in_script = [], [], [], False
        self.feed(value)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self.in_script = tag == "script" or self.in_script

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        (self.scripts if self.in_script else self.text).append(data)


class UiExperienceTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ui_profile.TEMPLATES / "profile.json").read_text())
        self.content = json.loads((ui_profile.TEMPLATES / "content.json").read_text())

    def test_all_archetype_adapter_density_scheme_combinations(self):
        for archetype in ("journey", "product-shell", "workspace", "content-hub", "showcase"):
            for css in ("native", "tailwind", "existing-system"):
                for density in ("compact", "comfortable"):
                    for scheme in ("light", "dark", "system"):
                        self.profile.update(archetype=archetype, css=css, density=density, scheme=scheme)
                        output = ui_profile.outputs(self.profile, self.content)
                        self.assertTrue(any(name.endswith("tokens.json") for name in output))
                        self.assertEqual(css == "tailwind", any(name.endswith("tailwind.css") for name in output))
                        html = output[f"{ui_profile.OUTPUT}/public/index.html"].decode()
                        self.assertIn(f'data-archetype="{archetype}"', html)

    def test_brand_seeds_and_overrides_have_contrast(self):
        for seed in ("#FFFFFF", "#000000", "#FAEEDA", "#FFFF00", "#1122AA", "#FF00FF"):
            self.profile["brand"]["primary"] = seed
            for mode in ui_tokens.palettes(self.profile).values():
                self.assertGreaterEqual(ui_tokens.contrast(mode["primary"], mode["on-primary"]), 4.5)
                self.assertGreaterEqual(ui_tokens.contrast(mode["primary"], mode["surface"]), 3)
        self.profile["brand"]["overrides"] = {"light": {"on-surface": "#EEEEEE"}}
        with self.assertRaisesRegex(ValueError, "contrast"):
            ui_profile.outputs(self.profile, self.content)

    def test_dtcg_aliases_resolve_to_srgb_colors(self):
        tokens = json.loads(ui_tokens.compile_tokens(self.profile)["tokens.json"])
        for mode in ("light", "dark"):
            for token in tokens["semantic"][mode].values():
                path = token["$value"][1:-1].split(".")
                target = tokens
                for segment in path:
                    target = target[segment]
                self.assertEqual(target["$value"]["colorSpace"], "srgb")
                self.assertEqual(len(target["$value"]["components"]), 3)

    def test_initial_html_is_semantic_and_has_one_metadata_owner(self):
        page = self.content["pages"][1]
        parsed = Html(ui_content.document(page, self.content, self.profile))
        for tag in ("title", "h1", "main", "table", "caption"):
            self.assertEqual(sum(t == tag for t, _ in parsed.tags), 1)
        self.assertEqual(sum(t == "link" and a.get("rel") == "canonical" for t, a in parsed.tags), 1)
        self.assertIn("100", parsed.text)
        self.assertIn("per month", parsed.text)
        structured = json.loads(parsed.scripts[0])
        self.assertEqual(structured["author"]["name"], page["article"]["author"])
        self.assertIn(page["article"]["author"], " ".join(parsed.text))

    def test_product_facts_are_visible_and_machine_readable(self):
        page = self.content["pages"][0]
        page["product"] = {"type": "SoftwareApplication", "price": "19.90", "currency": "EUR", "unit": "user/month", "region": "NL", "terms": "VAT excluded; annual commitment."}
        output = ui_content.document(page, self.content, self.profile)
        for fact in ("19.90", "EUR", "user/month", "NL", "annual commitment"):
            self.assertIn(fact, " ".join(Html(output).text))
            self.assertIn(fact, ui_content.markdown(page, self.content["origin"]))

    def test_hostile_content_never_becomes_executable_markup(self):
        attack = '</script><script>alert("x")</script><img src=x onerror=alert(1)>'
        page = self.content["pages"][0]
        page["title"] = page["description"] = attack
        page["blocks"] = [{"type": "paragraph", "text": attack}]
        parsed = Html(ui_content.document(page, self.content, self.profile))
        self.assertEqual(sum(t == "script" for t, _ in parsed.tags), 1)
        self.assertFalse(any(t == "img" for t, _ in parsed.tags))
        self.assertEqual(json.loads(parsed.scripts[0])["name"], attack)
        self.assertNotIn("<script>", ui_content.markdown(page, self.content["origin"]))

    def test_private_and_nonindexed_export_boundaries(self):
        self.profile["discovery"].update(markdown=True, llms=True)
        self.content["pages"][-1]["title"] = "PRIVATE_CANARY"
        self.content["pages"][-1]["blocks"] = [{"type": "paragraph", "text": "SECRET_BODY_CANARY"}]
        self.content["pages"][1]["index"] = False
        output = ui_profile.outputs(self.profile, self.content)
        for path, data in output.items():
            self.assertNotIn(b"PRIVATE_CANARY", data, path)
            self.assertNotIn(b"SECRET_BODY_CANARY", data, path)
        manifest = json.loads(output[f"{ui_profile.OUTPUT}/publication.json"])
        routes = {r["route"] for r in manifest["resources"]}
        self.assertNotIn("/account", routes)
        self.assertNotIn("/discovery/guide.md", routes)
        self.assertIn("/guide", routes)
        sitemap = ET.fromstring(output[f"{ui_profile.OUTPUT}/public/sitemap.xml"])
        self.assertEqual(len(sitemap), 1)
        self.assertIn(b"noindex,follow", output[f"{ui_profile.OUTPUT}/public/guide/index.html"])

    def test_sitemap_dates_are_editorial_and_generation_reproducible(self):
        first = ui_profile.outputs(self.profile, self.content)
        self.assertEqual(first, ui_profile.outputs(copy.deepcopy(self.profile), copy.deepcopy(self.content)))
        self.assertIn(b"2026-09-05", first[f"{ui_profile.OUTPUT}/public/sitemap.xml"])
        self.content["pages"][0]["lastModified"] = "2025-01-01"
        self.assertIn(b"2025-01-01", ui_profile.outputs(self.profile, self.content)[f"{ui_profile.OUTPUT}/public/sitemap.xml"])

    def test_reciprocal_translations(self):
        page = copy.deepcopy(self.content["pages"][0])
        page.update(id="welkom", path="/nl", language="nl", alternates=["welcome"])
        self.content["pages"].append(page)
        self.content["pages"][0]["alternates"] = ["welkom"]
        ui_contracts.validate(self.profile, self.content)
        self.assertIn('hreflang="nl"', ui_content.head(self.content["pages"][0], self.content, self.profile))
        page["alternates"] = []
        with self.assertRaisesRegex(ValueError, "reciprocal"):
            ui_contracts.validate(self.profile, self.content)

    def test_crawler_categories_are_independent(self):
        for search in (False, True):
            for training in (False, True):
                for user_fetch in (False, True):
                    self.profile["discovery"].update(search=search, training=training, userFetch=user_fetch)
                    robots = ui_content.discovery(self.content, self.profile)["robots.txt"]
                    for name, allowed in (("OAI-SearchBot", search), ("GPTBot", training), ("ChatGPT-User", user_fetch), ("Google-Extended", training), ("Claude-User", user_fetch)):
                        self.assertIn(f"User-agent: {name}\nDisallow:" + ("\n" if allowed else " /\n"), robots)

    def test_invalid_inputs_fail_closed(self):
        for path in ("/../escape", "//host", "/%2e%2e/x", "/assets/logo", "/a?x", "/a#b", "/A", "/a\\b"):
            content = copy.deepcopy(self.content)
            content["pages"][0]["path"] = path
            with self.assertRaises(ValueError, msg=path):
                ui_profile.outputs(self.profile, content)
        for url in ("javascript:alert(1)", "data:text/html,x", "//host/path", "https://user:pass@host", "https://host/\nx"):
            with self.assertRaises(ValueError, msg=url):
                ui_contracts.safe_url(url)
        for key, value in (("density", "unknown"), ("scheme", None), ("profile", 1), ("extra", True)):
            profile = copy.deepcopy(self.profile)
            profile[key] = value
            with self.assertRaises(ValueError):
                ui_profile.outputs(profile, self.content)

    def test_navigation_and_rtl_are_independent_choices(self):
        self.content["pages"][0]["direction"] = "rtl"
        for navigation in ("sidebar", "top", "contextual", "none"):
            self.profile["navigation"] = navigation
            rendered = ui_content.document(self.content["pages"][0], self.content, self.profile)
            self.assertIn('dir="rtl"', rendered)
            self.assertEqual('<nav ' in rendered, navigation != "none")
            if navigation == "contextual":
                self.assertIn('href="#start"', rendered)

    def test_budget_failure(self):
        self.profile["budgets"]["cssBytes"] = 1024
        with self.assertRaisesRegex(ValueError, "budget"):
            ui_profile.outputs(self.profile, self.content)

    def test_svg_logo_and_custom_icon_provenance(self):
        svg = '<svg viewBox="0 0 24 24"><defs><linearGradient id="brand"><stop offset="0" stop-color="#123456"/></linearGradient></defs><path fill="url(#brand)" d="M0 0h24v24z"/></svg>'
        self.profile["brand"]["logo"] = {"svg": svg, "alt": "Acme"}
        self.profile["brand"]["icons"] = {"bundle": "custom", "assets": {"check": svg}, "source": "Consumer artwork", "license": "Consumer-owned"}
        output = ui_profile.outputs(self.profile, self.content)
        self.assertIn(b"pk-logo-brand", output[f"{ui_profile.OUTPUT}/public/assets/brand-logo.svg"])
        self.assertIn(b"Acme", output[f"{ui_profile.OUTPUT}/public/index.html"])
        del self.profile["brand"]["icons"]["license"]
        with self.assertRaisesRegex(ValueError, "license"):
            ui_profile.outputs(self.profile, self.content)

    def test_svg_rejects_active_content_and_dangling_references(self):
        attacks = ['<script/>', '<foreignObject/>', '<image href="https://evil/track"/>', '<path onclick="alert(1)"/>',
                   '<path style="fill:red"/>', '<path fill="url(https://evil)"/>', '<path fill="url(#missing)"/>',
                   '<use href="#x"/>', '<animate/>']
        for attack in attacks:
            with self.assertRaises(ValueError, msg=attack):
                ui_svg.sanitize_svg('<svg viewBox="0 0 24 24">' + attack + '</svg>')
        with self.assertRaises(ValueError):
            ui_svg.sanitize_svg('<!DOCTYPE svg [<!ENTITY x "bad">]><svg viewBox="0 0 1 1"/>')

    def test_icon_accessibility_and_license(self):
        self.assertIn('aria-hidden="true"', ui_svg.icon_markup(self.profile, "check"))
        self.assertIn('aria-label="Search"', ui_svg.icon_markup(self.profile, "search", "Search"))
        output = ui_profile.outputs(self.profile, self.content)
        self.assertIn(b"Cole Bemis", output[f"{ui_profile.OUTPUT}/public/assets/icons/LICENSE.txt"])

    def test_ownership_conflicts_preflight_all_writes_and_remove_only_owned_stale_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ui_profile.execute(root, "init")
            ui_profile.execute(root, "build")
            ui_profile.execute(root, "check")
            file = root / ui_profile.OUTPUT / "public/index.html"
            file.write_text("consumer edit")
            with self.assertRaisesRegex(ValueError, "Consumer edits"):
                ui_profile.execute(root, "build")
            self.assertEqual(file.read_text(), "consumer edit")
            with self.assertRaisesRegex(ValueError, "never overwrites"):
                ui_profile.execute(root, "init")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = ui_profile.outputs(self.profile, self.content)
            ui_profile.synchronize(root, expected, False)
            self.content["pages"][1]["intent"] = "private-app"
            self.content["pages"][1]["index"] = False
            ui_profile.synchronize(root, ui_profile.outputs(self.profile, self.content), False)
            self.assertFalse((root / ui_profile.OUTPUT / "public/guide/index.html").exists())

    def test_unowned_public_artifact_and_state_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ui_profile.execute(root, "init")
            ui_profile.execute(root, "build")
            (root / ui_profile.OUTPUT / "public/secret.txt").write_text("private")
            with self.assertRaisesRegex(ValueError, "Unowned public"):
                ui_profile.execute(root, "check")
            with self.assertRaises(ValueError):
                ui_profile.safe_path(root, "../../outside")

    def test_default_has_no_tracker_font_download_or_paid_model_dependency(self):
        output = ui_profile.outputs(self.profile, self.content)
        html = output[f"{ui_profile.OUTPUT}/public/index.html"].decode()
        self.assertNotIn("googletagmanager", html)
        self.assertNotIn("fonts.googleapis", html)
        self.assertNotIn("analytics.mjs", html)
        self.assertNotIn("/llms.txt", html)

    def test_packaged_browser_acceptance_is_cross_engine_and_multi_device(self):
        output = ui_profile.outputs(self.profile, self.content)
        html = output[f"{ui_profile.OUTPUT}/public/index.html"].decode()
        browser = output[f"{ui_profile.OUTPUT}/acceptance/tests/browser.mjs"].decode()
        self.assertIn('class="pk-skip" href="#main" tabindex="0"', html)
        for requirement in ("chromium", "firefox", "webkit", "phone-portrait", "phone-landscape", "tablet-portrait", "tablet-landscape", "hasTouch: true"):
            self.assertIn(requirement, browser)

    def test_isolated_ui_toolchain_has_hash_bound_bootstrap_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for target in (bootstrap_context.UI_PACKAGE_MANIFEST, bootstrap_context.UI_PACKAGE_LOCK):
                path = root / target
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ui_profile.TEMPLATES / "acceptance" / target.name).read_bytes())
            authority = bootstrap_context.managed_profile_pin_authority(root, {"selected_profiles": ["ui-experience-v1"]})
            self.assertEqual(set(authority["pins"]), {"node", "npm", "@playwright/test", "@axe-core/playwright", "@tailwindcss/cli", "tailwindcss"})
            self.assertEqual(len(authority["sources"]), 2)
            package = json.loads((root / bootstrap_context.UI_PACKAGE_MANIFEST).read_text())
            package["engines"]["node"] = "0.0.1"
            (root / bootstrap_context.UI_PACKAGE_MANIFEST).write_text(json.dumps(package))
            with self.assertRaisesRegex(bootstrap_context.ContextError, "mismatch"):
                bootstrap_context.managed_profile_pin_authority(root, {"selected_profiles": ["ui-experience-v1"]})

    def test_analytics_profile_selection_does_not_auto_activate_transport(self):
        self.profile["analytics"] = {"provider": "ga4", "measurementId": "G-TEST", "events": ["journey_started"]}
        output = ui_profile.outputs(self.profile, self.content)
        config = json.loads(output[f"{ui_profile.OUTPUT}/integration/analytics.json"])
        self.assertFalse(config["automaticActivation"])
        self.assertEqual(config["pages"], ["welcome", "guide"])
        self.assertNotIn(b"G-TEST", output[f"{ui_profile.OUTPUT}/public/index.html"])
        del self.profile["analytics"]["measurementId"]
        with self.assertRaisesRegex(ValueError, "measurementId"):
            ui_profile.outputs(self.profile, self.content)

    def test_provider_independent_evaluation_is_honest_about_lexical_limits(self):
        questions = {"version": "1.0", "questions": [{"id": "quota", "prompt": "What quota?", "requiredFacts": ["100", "per month"], "allowedCitations": ["https://example.invalid/guide"]}]}
        trials = {"version": "1.0", "trials": []}
        for provider in ("local", "hosted"):
            trials["trials"].append({"provider": provider, "model": "example", "version": "1", "trial": 1, "representation": "html", "answers": [{"questionId": "quota", "answer": "1000 requests per month", "citations": ["https://wrong.invalid"]}]})
        result = ui_evaluation.score(questions, trials)
        self.assertEqual(result["providers"], ["hosted", "local"])
        self.assertEqual(result["results"][0]["literalFactCoverage"], 0.5)
        self.assertFalse(result["results"][0]["canonicalCitationMatch"])
        self.assertEqual(result["results"][0]["semanticAdjudication"], "required")
        trials["trials"].append(trials["trials"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            ui_evaluation.score(questions, trials)


if __name__ == "__main__":
    unittest.main()
