from __future__ import annotations

from pathlib import Path
from typing import Any


class FirebaseAdminService:
    def __init__(self) -> None:
        self._db = None
        self._messaging = None
        self._firestore = None
        self._rtdb = None

    def _ensure_clients(self):
        if self._db is not None and self._messaging is not None:
            return self._db, self._messaging

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore, messaging
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency 'firebase-admin'. Run 'pip install -r requirements.txt' in lich-hoc-api."
            ) from exc

        service_account_path = Path(__file__).resolve().parent / "serviceAccount.json"
        if not service_account_path.exists():
            raise RuntimeError(f"Missing Firebase service account at: {service_account_path}")

        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(
                credentials.Certificate(str(service_account_path))
            )

        self._db = firestore.client(app)
        self._messaging = messaging
        self._firestore = firestore
        return self._db, self._messaging

    def list_users(self, query_text: str = "", limit: int = 50) -> list[dict[str, Any]]:
        db, _ = self._ensure_clients()
        normalized_query = query_text.strip().lower()
        safe_limit = max(1, min(limit, 100))

        users_ref = db.collection("users")
        docs = users_ref.stream()

        results: list[dict[str, Any]] = []
        for item in docs:
            data = item.to_dict() or {}
            candidate = {
                "studentId": data.get("studentId") or item.id,
                "name": data.get("name") or "",
                "className": data.get("className") or "",
                "schoolName": data.get("schoolName") or "",
                "major": data.get("major") or "",
                "avatar": data.get("avatar") or "",
                "cover": data.get("cover") or "",
            }

            if normalized_query:
                haystack = " ".join(
                    [
                        candidate["studentId"],
                        candidate["name"],
                        candidate["className"],
                        candidate["schoolName"],
                        candidate["major"],
                    ]
                ).lower()

                if normalized_query not in haystack:
                    continue

            results.append(candidate)
            if len(results) >= safe_limit:
                break

        return results

    def send_system_notification(
        self,
        *,
        student_id: str,
        title: str,
        body: str,
        sender_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        db, messaging = self._ensure_clients()

        notification_ref = (
            db.collection("notifications")
            .document(student_id)
            .collection("items")
            .document()
        )

        data = {
            "studentId": student_id,
            "senderId": sender_id,
            "title": title,
            "body": body,
            "type": "system",
            "data": payload or {},
            "unreadCount": 1,
            "createdAt": self._firestore.SERVER_TIMESTAMP,
            "updatedAt": self._firestore.SERVER_TIMESTAMP,
        }

        notification_ref.set(data)

        push_status: dict[str, Any] = {
            "attempted": False,
            "success": False,
            "messageId": None,
            "error": None,
        }

        token_doc = db.collection("fcm_tokens").document(student_id).get()
        fcm_token = token_doc.to_dict().get("fcmToken") if token_doc.exists else None

        if fcm_token:
            push_status["attempted"] = True
            try:
                message_id = messaging.send(
                    messaging.Message(
                        token=fcm_token,
                        notification=messaging.Notification(title=title, body=body),
                        data={
                            "type": "system",
                            "studentId": student_id,
                            "senderId": sender_id or "",
                        },
                    )
                )
                push_status["success"] = True
                push_status["messageId"] = message_id
            except Exception as exc:
                push_status["error"] = str(exc)

        return {
            "notificationId": notification_ref.id,
            "studentId": student_id,
            "title": title,
            "body": body,
            "type": "system",
            "push": push_status,
        }

    def send_fcm_push(
        self,
        *,
        student_id: str,
        title: str,
        body: str,
        type: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        db, messaging = self._ensure_clients()
        
        push_status: dict[str, Any] = {
            "attempted": False,
            "success": False,
            "messageId": None,
            "error": None,
        }

        token_doc = db.collection("fcm_tokens").document(student_id).get()
        fcm_token = token_doc.to_dict().get("fcmToken") if token_doc.exists else None

        if fcm_token:
            push_status["attempted"] = True
            try:
                # Prepare data payload (convert all values to strings for FCM)
                data_payload = {
                    "type": str(type),
                    "studentId": str(student_id),
                }
                if payload:
                    for k, v in payload.items():
                        data_payload[k] = str(v)

                message_id = messaging.send(
                    messaging.Message(
                        token=fcm_token,
                        notification=messaging.Notification(title=title, body=body),
                        data=data_payload,
                    )
                )
                push_status["success"] = True
                push_status["messageId"] = message_id
            except Exception as exc:
                push_status["error"] = str(exc)

        return push_status


firebase_admin_service = FirebaseAdminService()
