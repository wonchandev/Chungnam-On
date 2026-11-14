import json
from unittest import mock

from django.contrib import admin
from django.test import RequestFactory, TestCase, override_settings

from apps.assistant import chatbot, llm
from apps.assistant.admin import ComplaintAdmin
from apps.assistant.models import AdminGuide, ChatTurn, Complaint, Conversation
from apps.core.models import Notification
from apps.core.testing import client_for, make_worker


class ComplaintTest(TestCase):
    def setUp(self):
        self.w = make_worker()
        self.c = client_for(self.w)

    def test_create_list_detail_isolated(self):
        res = self.c.post("/api/admin-info/complaints/", {"category": "wage", "title": "임금 체불", "body": "2주째 못 받음"}, format="json")
        self.assertEqual((res.status_code, res.json()["status"]), (201, "received"))
        cid = res.json()["id"]
        self.assertEqual(self.c.get("/api/admin-info/complaints/").json()["count"], 1)
        self.assertEqual(self.c.get("/api/admin-info/complaints/", {"status": "resolved"}).json()["count"], 0)
        other = client_for(make_worker("o"))
        self.assertEqual(other.get(f"/api/admin-info/complaints/{cid}/").status_code, 404)
        self.assertEqual(other.get("/api/admin-info/complaints/").json()["count"], 0)
        # 처리 상태/답변은 사용자가 바꿀 수 없음
        res = self.c.post("/api/admin-info/complaints/", {"category": "etc", "title": "t", "body": "b", "status": "resolved", "answer": "x"}, format="json")
        self.assertEqual((res.json()["status"], res.json()["answer"]), ("received", ""))

    def test_admin_answer_notifies(self):
        comp = Complaint.objects.create(user=self.w, title="문의", body="내용")
        ma = ComplaintAdmin(Complaint, admin.site)
        comp.status, comp.answer = "resolved", "확인했습니다"
        ma.save_model(RequestFactory().post("/"), comp, None, change=True)
        comp.refresh_from_db()
        self.assertIsNotNone(comp.answered_at)
        n = Notification.objects.get(user=self.w)
        self.assertEqual((n.type, n.data["complaint_id"]), ("complaint", comp.id))
        self.assertEqual(self.c.get(f"/api/admin-info/complaints/{comp.id}/").json()["answer"], "확인했습니다")


class SearchGuidesTest(TestCase):
    def test_ranking(self):
        a = AdminGuide.objects.create(category="visa", title="비자 연장", summary="체류기간 연장", body="비자 연장은 출입국에서 합니다")
        b = AdminGuide.objects.create(category="insurance", title="건강보험", body="비자와 무관")
        AdminGuide.objects.create(category="etc", title="비공개 비자", body="비자", is_published=False)
        res = chatbot.search_guides("비자 연장 방법")
        self.assertEqual(res[0].id, a.id)
        self.assertNotIn("비공개 비자", [g.title for g in res])
        self.assertEqual(chatbot.search_guides("!!"), [])


class ChatbotTest(TestCase):
    def setUp(self):
        self.w = make_worker(lang="en")
        self.c = client_for(self.w)
        self.g = AdminGuide.objects.create(category="visa", title="비자 연장", summary="체류기간 연장 안내", body="출입국 사무소에서 신청")

    def test_fallback_without_key(self):
        res = self.c.post("/api/assistant/chat/", {"message": "How to extend my visa 비자 연장"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        d = res.json()
        self.assertIn("비자 연장", d["answer"])
        self.assertEqual(d["sources"], [{"id": self.g.id, "title": "비자 연장"}])
        # 대화 저장 + 이어가기
        self.assertEqual(Conversation.objects.get().turns.count(), 2)
        res2 = self.c.post("/api/assistant/chat/", {"message": "고마워", "conversation_id": d["conversation_id"]}, format="json")
        self.assertEqual(res2.json()["conversation_id"], d["conversation_id"])
        self.assertEqual(Conversation.objects.get().turns.count(), 4)

    def test_no_guide_fallback_points_to_official(self):
        AdminGuide.objects.all().delete()
        d = self.c.post("/api/assistant/chat/", {"message": "zzzz qqqq"}, format="json").json()
        self.assertIn("1345", d["answer"])

    @override_settings(ANTHROPIC_API_KEY="k")
    def test_llm_stream_and_prompt(self):
        seen = {}

        def fake(system, messages):
            seen["system"], seen["messages"] = system, messages
            yield "Go to "
            yield "the immigration office."

        with mock.patch.object(llm, "stream_answer", fake):
            res = self.c.post("/api/assistant/chat/", {"message": "비자 연장 어떻게 해요?", "stream": True}, format="json")
            body = b"".join(res.streaming_content).decode()
        self.assertEqual(res["Content-Type"], "text/event-stream")
        events = [json.loads(l[6:]) for l in body.strip().split("\n\n")]
        self.assertEqual([e["type"] for e in events], ["delta", "delta", "done"])
        self.assertEqual(events[-1]["sources"][0]["id"], self.g.id)
        self.assertIn("Answer in the user's language: en", seen["system"])
        self.assertIn("출입국 사무소에서 신청", seen["system"])  # RAG 문맥 주입
        self.assertEqual(seen["messages"][-1], {"role": "user", "content": "비자 연장 어떻게 해요?"})
        self.assertEqual(ChatTurn.objects.filter(role="assistant").get().text, "Go to the immigration office.")

    @override_settings(ANTHROPIC_API_KEY="k")
    def test_history_passed_and_llm_failure(self):
        calls = []

        def ok(system, messages):
            calls.append(messages)
            yield "ok"

        with mock.patch.object(llm, "stream_answer", ok):
            cid = self.c.post("/api/assistant/chat/", {"message": "첫 질문"}, format="json").json()["conversation_id"]
            self.c.post("/api/assistant/chat/", {"message": "두번째", "conversation_id": cid}, format="json")
        self.assertEqual([m["role"] for m in calls[1]], ["user", "assistant", "user"])

        def boom(system, messages):
            raise RuntimeError("api down")
            yield  # pragma: no cover

        with mock.patch.object(llm, "stream_answer", boom):
            res = self.c.post("/api/assistant/chat/", {"message": "질문"}, format="json")
        self.assertEqual((res.status_code, res.json()["code"]), (503, "assistant_unavailable"))

    def test_conversations_isolated_and_deletable(self):
        cid = self.c.post("/api/assistant/chat/", {"message": "비자"}, format="json").json()["conversation_id"]
        other = client_for(make_worker("o"))
        self.assertEqual(other.post("/api/assistant/chat/", {"message": "x", "conversation_id": cid}, format="json").status_code, 404)
        self.assertEqual(other.get(f"/api/assistant/conversations/{cid}/").status_code, 404)
        self.assertEqual(self.c.get("/api/assistant/conversations/").json()["count"], 1)
        detail = self.c.get(f"/api/assistant/conversations/{cid}/").json()
        self.assertEqual([t["role"] for t in detail["turns"]], ["user", "assistant"])
        self.assertEqual(self.c.delete(f"/api/assistant/conversations/{cid}/").status_code, 204)
        self.assertEqual(client_for().post("/api/assistant/chat/", {"message": "x"}, format="json").status_code, 401)


class DocumentTest(TestCase):
    def test_templates_and_draft(self):
        c = client_for(make_worker(lang="th"))
        tpls = c.get("/api/assistant/documents/templates/").json()
        self.assertEqual(len(tpls), 3)
        res = c.post("/api/assistant/documents/", {"type": "absence_notice", "fields": {
            "name": "소마이", "workplace": "충남 건설", "absence_date": "11월 20일", "reason": "병원 진료"}}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        d = res.json()
        self.assertEqual(d["missing_fields"], [])
        self.assertIn("소마이", d["body_ko"])
        self.assertIn("병원 진료", d["body_ko"])
        self.assertTrue(d["body_translated"].startswith("[th]"))
        self.assertIn("확인하세요", d["notice"])

    def test_missing_fields_marked(self):
        d = client_for(make_worker()).post("/api/assistant/documents/", {"type": "visa_extension_reason", "fields": {"name": "A"}}, format="json").json()
        self.assertIn("reason", d["missing_fields"])
        self.assertIn("[입력 필요: 연장 사유]", d["body_ko"])
        self.assertIsNone(d["body_translated"])  # ko 사용자는 번역 불필요
        bad = client_for(make_worker("z")).post("/api/assistant/documents/", {"type": "nope", "fields": {}}, format="json")
        self.assertEqual(bad.status_code, 400)
