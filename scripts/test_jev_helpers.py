"""gshorts Jev 도우미(comment-guide/scripts/jev_prefilter.py, foreign-clip-short/scripts/jev_focus.py)를
가짜 TypeSafe API에 붙여 돌린다. 키가 없거나 API가 실패하면 입력을 그대로 두는지(기존 동작)가 핵심."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "shorts" / "skills"
PREFILTER = SKILLS / "comment-guide" / "scripts" / "jev_prefilter.py"
FOCUS = SKILLS / "foreign-clip-short" / "scripts" / "jev_focus.py"
SECRET = "test-key-should-never-be-printed"


class FakeJev(BaseHTTPRequestHandler):
    mode = "ok"
    calls = 0

    def do_POST(self):
        FakeJev.calls += 1
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if FakeJev.mode == "error" or self.headers.get("Authorization") != f"Bearer {SECRET}":
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error":"bad"}')
            return
        if "assets" in body:  # focus: 얼굴이 왼쪽 끝에 있는 프레임
            ans = {"has": {"noul": 0.97}, "face": {"box": {"left": 0.02, "right": 0.2, "top": 0.1, "bottom": 0.5}, "confidence": 0.8}}
        else:
            t = body["state"]
            ans = {"spam": {"noul": 0.9 if "리딩방" in t else 0.05},
                   "fit": {"score": 2.6 if "공제" in t else 1.5 if "환급" in t else 0.3}}
        out = json.dumps({"answers": ans}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


needs_ffmpeg = unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg 없음")


class JevHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), FakeJev)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        FakeJev.mode, FakeJev.calls = "ok", 0
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_script(self, script, *args, key=True):
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        env["TYPESAFE_BASE_URL"] = self.url
        if key:
            env["TYPESAFE_API_KEY"] = SECRET
        r = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(SECRET, r.stdout + r.stderr)
        return r

    # --- 댓글 사전 필터 ---
    POSTS = {"지원금": [{"text": "환급 신청 언제까지?", "url": "a"}, {"text": "리딩방 무료 입장 DM", "url": "b"}],
             "연말정산": [{"text": "오늘 점심 뭐 먹지", "url": "c"}, {"text": "카드 공제 25% 넘으면 체크카드", "url": "d"}]}

    def prefilter(self, **kw):
        src = self.tmp / "cands.json"
        src.write_text(json.dumps(self.POSTS, ensure_ascii=False), encoding="utf-8")
        r = self.run_script(PREFILTER, str(src), **kw)
        return json.loads(r.stdout), r.stderr

    def test_prefilter_drops_spam_and_low_fit_and_ranks_rest(self):
        out, _ = self.prefilter()
        self.assertEqual(out["jev"], "ok")
        self.assertEqual([p["url"] for p in out["kept"]], ["d", "a"])
        self.assertEqual(sorted(p["url"] for p in out["dropped"]), ["b", "c"])

    def test_prefilter_without_key_keeps_everything_in_order(self):
        out, err = self.prefilter(key=False)
        self.assertEqual([p["url"] for p in out["kept"]], ["a", "b", "c", "d"])
        self.assertEqual(out["dropped"], [])
        self.assertIn("TYPESAFE_API_KEY", err)
        self.assertEqual(FakeJev.calls, 0)

    def test_prefilter_api_error_keeps_everything(self):
        FakeJev.mode = "error"
        out, _ = self.prefilter()
        self.assertTrue(out["jev"].startswith("skipped"))
        self.assertEqual(len(out["kept"]), 4)

    # --- 9:16 크롭 초점 ---
    def test_refocus_moves_only_when_face_leaves_window(self):
        spec = importlib.util.spec_from_file_location("jev_focus", FOCUS)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        r = 0.65  # box 프레임, 16:9 원본
        self.assertIsNone(m.refocus(0.5, r, [(0.4, 0.6)]))  # 가운데 창 안
        self.assertEqual(m.refocus(0.5, r, [(0.02, 0.2)]), 0)  # 왼쪽 끝 → 창도 왼쪽 끝
        self.assertEqual(m.refocus(0.5, r, [(0.8, 0.98)]), 1)
        self.assertIsNone(m.refocus(0.5, r, []))  # 사람 없음
        self.assertIsNone(m.refocus(0, r, [(0.01, 0.2)]))  # 이미 왼쪽 끝이면 바뀐 것 아님
        x = m.refocus(0.5, 0.4, [(0.2, 0.32)])  # 좁은 창(crop): 창 [0.3, 0.7] 밖
        lo, hi = m.window(x, 0.4)
        self.assertAlmostEqual((lo + hi) / 2, 0.26, places=2)  # 얼굴 중심이 창 중심

    def make_plan(self, video=False):
        out = self.tmp / "out"
        (out / "work").mkdir(parents=True)
        (out / "source").mkdir()
        plan = {"title": "t", "source": "source/v.mp4", "topHeadline": ["a", "b"], "segments": [
            {"type": "clip", "from": 0.5, "to": 1.5, "subs": []},
            {"type": "narration", "text": "n", "over": {"cuts": [[1.0, 2.0]], "x": 0.5}},
            {"type": "clip", "from": 2.0, "to": 3.0, "subs": [], "video": [{"cuts": [[2.0, 2.5], [2.5, 3.0]], "x": 0.5, "crop": 0.78}]}]}
        p = out / "work" / "plan.json"
        p.write_text(json.dumps(plan), encoding="utf-8")
        if video:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=4",
                            str(out / "source" / "v.mp4")], check=True)
        return p, plan

    def test_focus_without_key_leaves_plan_untouched(self):
        p, plan = self.make_plan()
        r = self.run_script(FOCUS, str(p), key=False)
        self.assertEqual(json.loads(p.read_text()), plan)
        self.assertIn("skipped", r.stderr)

    @needs_ffmpeg
    def test_focus_sets_x_on_every_framed_spot_and_writes_sheet(self):
        p, _ = self.make_plan(video=True)
        r = self.run_script(FOCUS, str(p))
        segs = json.loads(p.read_text())["segments"]
        self.assertEqual([segs[0]["x"], segs[1]["over"]["x"], segs[2]["video"][0]["x"]], [0, 0, 0], r.stderr)
        self.assertTrue((p.parent.parent / "check" / "jev-focus.jpg").exists())

    @needs_ffmpeg
    def test_focus_api_error_leaves_plan_untouched(self):
        p, plan = self.make_plan(video=True)
        FakeJev.mode = "error"
        r = self.run_script(FOCUS, str(p))
        self.assertEqual(json.loads(p.read_text()), plan)
        self.assertIn("skipped", r.stderr)


if __name__ == "__main__":
    unittest.main()
