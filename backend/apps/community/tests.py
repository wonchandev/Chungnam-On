from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.community.models import Comment, CompanionPost, Post
from apps.core.models import Notification
from apps.core.testing import client_for, make_employer, make_job, make_worker


class PostTest(TestCase):
    def setUp(self):
        self.a, self.b = make_worker("a", lang="th"), make_worker("b", lang="ko")
        self.ca, self.cb = client_for(self.a), client_for(self.b)

    def make(self, **kw):
        d = {"title": "천안 맛집", "body": "여기가 맛있어요", "category": "life", "region": "44130"}
        d.update(kw)
        return self.ca.post("/api/community/posts/", d, format="json")

    def test_create_requires_login_and_validates(self):
        self.assertEqual(client_for().post("/api/community/posts/", {"title": "x", "body": "y"}, format="json").status_code, 401)
        self.assertEqual(self.make(region="99999").status_code, 400)
        res = self.make()
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["source_lang"], "th")  # 작성자 언어가 원문 언어

    def test_translation_by_reader_language(self):
        pid = self.make().json()["id"]
        ko = self.cb.get(f"/api/community/posts/{pid}/").json()  # ko 독자 → th 원문을 ko 로 번역
        self.assertTrue(ko["title"].startswith("[ko]"))
        self.assertEqual(ko["original_title"], "천안 맛집")
        th = self.ca.get(f"/api/community/posts/{pid}/").json()  # 작성자 본인(th) → 번역 없음
        self.assertEqual(th["title"], "천안 맛집")
        self.assertTrue(th["is_mine"])

    def test_filters_and_counts(self):
        p1 = self.make().json()["id"]
        self.make(title="당진 후기", category="review", region="44270", body="일 잘했어요")
        c = client_for()
        self.assertEqual(c.get("/api/community/posts/", {"region": "44270"}).json()["count"], 1)
        self.assertEqual(c.get("/api/community/posts/", {"category": "life"}).json()["count"], 1)
        self.assertEqual(c.get("/api/community/posts/", {"q": "맛"}).json()["count"], 1)
        self.assertEqual(self.ca.get("/api/community/posts/", {"mine": "true"}).json()["count"], 2)
        self.assertEqual(self.cb.get("/api/community/posts/", {"mine": "true"}).json()["count"], 0)
        self.cb.post(f"/api/community/posts/{p1}/like/")
        self.cb.post(f"/api/community/posts/{p1}/like/")  # 멱등
        self.cb.post(f"/api/community/posts/{p1}/comments/", {"body": "좋아요"}, format="json")
        item = next(r for r in self.cb.get("/api/community/posts/").json()["results"] if r["id"] == p1)
        self.assertEqual((item["like_count"], item["comment_count"], item["is_liked"]), (1, 1, True))
        self.cb.delete(f"/api/community/posts/{p1}/like/")
        self.assertEqual(self.cb.get(f"/api/community/posts/{p1}/").json()["like_count"], 0)

    def test_edit_delete_author_only(self):
        pid = self.make().json()["id"]
        self.assertEqual(self.cb.patch(f"/api/community/posts/{pid}/", {"title": "x"}, format="json").status_code, 403)
        self.assertEqual(client_for().patch(f"/api/community/posts/{pid}/", {"title": "x"}, format="json").status_code, 401)
        self.assertEqual(self.ca.patch(f"/api/community/posts/{pid}/", {"title": "수정"}, format="json").json()["title"], "수정")
        self.assertEqual(self.cb.delete(f"/api/community/posts/{pid}/").status_code, 403)
        self.assertEqual(self.ca.delete(f"/api/community/posts/{pid}/").status_code, 204)
        self.assertEqual(client_for().get(f"/api/community/posts/{pid}/").status_code, 404)

    def test_comments_notify_translate_delete(self):
        pid = self.make().json()["id"]
        res = self.cb.post(f"/api/community/posts/{pid}/comments/", {"body": "안녕하세요"}, format="json")
        self.assertEqual(res.status_code, 201)
        n = Notification.objects.get(user=self.a)
        self.assertEqual((n.type, n.data["post_id"]), ("comment", pid))
        self.ca.post(f"/api/community/posts/{pid}/comments/", {"body": "내 글 댓글"}, format="json")
        self.assertEqual(Notification.objects.filter(user=self.a).count(), 1)  # 내 댓글은 알림 없음
        lst = self.ca.get(f"/api/community/posts/{pid}/comments/").json()["results"]  # th 독자 → ko 댓글 번역
        self.assertTrue(lst[0]["body"].startswith("[th]"))
        cid = lst[0]["id"]
        self.assertEqual(self.ca.delete(f"/api/community/comments/{cid}/").status_code, 404)  # 남의 댓글
        self.assertEqual(self.cb.delete(f"/api/community/comments/{cid}/").status_code, 204)

    def test_block_and_hidden(self):
        pid = self.make().json()["id"]
        self.cb.post(f"/api/blocks/{self.a.id}/")
        self.assertEqual(self.cb.get("/api/community/posts/").json()["count"], 0)  # 차단한 사람 글 숨김
        self.assertEqual(self.ca.get("/api/community/posts/").json()["count"], 1)  # 내 글은 내게 계속 보임
        Post.objects.filter(pk=pid).update(is_hidden=True)
        self.assertEqual(client_for().get(f"/api/community/posts/{pid}/").status_code, 404)


class CompanionTest(TestCase):
    def setUp(self):
        self.a, self.b, self.c = make_worker("a"), make_worker("b"), make_worker("c")
        self.boss = make_employer()
        self.job = make_job(self.boss.company, with_friend=True)
        self.ca = client_for(self.a)
        res = self.ca.post("/api/community/companions/", {
            "title": "같이 가요", "body": "천안역에서 만나요", "job": self.job.id, "region": "44130",
            "meet_place": "천안역 1번 출구", "meet_at": (timezone.now() + timedelta(days=1)).isoformat(), "capacity": 2,
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.pid = res.json()["id"]

    def test_join_leave_capacity(self):
        cb, cc = client_for(self.b), client_for(self.c)
        self.assertEqual(self.ca.post(f"/api/community/companions/{self.pid}/join/").json()["code"], "own_post")
        r = cb.post(f"/api/community/companions/{self.pid}/join/")
        self.assertEqual((r.status_code, r.json()["participant_count"], r.json()["is_joined"]), (200, 1, True))
        cb.post(f"/api/community/companions/{self.pid}/join/")  # 멱등
        self.assertEqual(Notification.objects.filter(user=self.a, type="companion").count(), 1)
        cc.post(f"/api/community/companions/{self.pid}/join/")
        self.assertEqual(CompanionPost.objects.get().status, "closed")  # 정원(2) 도달 → 자동 마감
        d = make_worker("d")
        self.assertEqual(client_for(d).post(f"/api/community/companions/{self.pid}/join/").json()["code"], "closed")
        r = cb.delete(f"/api/community/companions/{self.pid}/join/")  # 취소하면 다시 모집중
        self.assertEqual((r.json()["participant_count"], r.json()["status"]), (1, "open"))

    def test_create_preserves_content_and_validates_capacity(self):
        post = CompanionPost.objects.get(pk=self.pid)
        self.assertEqual((post.title, post.body), ("같이 가요", "천안역에서 만나요"))
        for payload in ({"body": "제목 없음"}, {"title": "  "}, {"title": "동행", "capacity": 0}):
            response = self.ca.post("/api/community/companions/", payload, format="json")
            self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(client_for().post("/api/community/companions/", {"title": "동행"}, format="json").status_code, 401)

    def test_list_filters_and_participants_privacy(self):
        c = client_for()
        self.assertEqual(c.get("/api/community/companions/", {"job": self.job.id}).json()["count"], 1)
        self.assertEqual(c.get("/api/community/companions/", {"region": "44270"}).json()["count"], 0)
        self.assertEqual(c.get("/api/community/companions/", {"status": "closed"}).json()["count"], 0)
        cb = client_for(self.b)
        self.assertEqual(cb.get(f"/api/community/companions/{self.pid}/participants/").status_code, 403)
        cb.post(f"/api/community/companions/{self.pid}/join/")
        self.assertEqual(cb.get(f"/api/community/companions/{self.pid}/participants/").json()["count"], 1)
        self.assertEqual(self.ca.get(f"/api/community/companions/{self.pid}/participants/").status_code, 200)
        self.assertEqual(c.get(f"/api/community/companions/{self.pid}/").json()["job_title"], "공장 신축 현장 보조")

    def test_delete_author_only(self):
        self.assertEqual(client_for(self.b).delete(f"/api/community/companions/{self.pid}/").status_code, 403)
        self.assertEqual(self.ca.delete(f"/api/community/companions/{self.pid}/").status_code, 204)
