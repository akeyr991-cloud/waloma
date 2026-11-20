def test_registration_creates_pending_member_with_unique_id(client):
    payload = {"full_name":"A Test Member", "email":"member@example.com", "phone":"+251911000000", "password":"StrongPassword123!"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["role"] == "member"
    assert body["member_id"].startswith("WAL-")
    assert "password" not in body and "password_hash" not in body

def test_duplicate_email_is_rejected(client):
    payload = {"full_name":"A Test Member", "email":"member@example.com", "phone":"+251911000000", "password":"StrongPassword123!"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409

def test_pending_member_cannot_login(client):
    payload = {"full_name":"A Test Member", "email":"member@example.com", "phone":"+251911000000", "password":"StrongPassword123!"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/login", json={"email":"member@example.com", "password":"StrongPassword123!"})
    assert response.status_code == 403

def test_admin_can_approve_registration(client, admin):
    payload = {"full_name":"A Test Member", "email":"member@example.com", "phone":"+251911000000", "password":"StrongPassword123!"}
    member = client.post("/api/v1/auth/register", json=payload).json()
    from app.core.security import create_access_token
    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}
    pending = client.get("/api/v1/auth/registrations/pending", headers=headers)
    assert pending.status_code == 200 and len(pending.json()) == 1
    approved = client.patch(f"/api/v1/auth/registrations/{member['id']}/status", json={"status":"approved"}, headers=headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    login = client.post("/api/v1/auth/login", json={"email":"member@example.com", "password":"StrongPassword123!"})
    assert login.status_code == 200

def test_non_admin_cannot_review_registrations(client):
    response = client.get("/api/v1/auth/registrations/pending")
    assert response.status_code == 401

def test_member_role_cannot_access_admin_review(client, db):
    from app.models import User, UserRole, AccountStatus
    from app.core.security import hash_password, create_access_token
    member = User(member_id="WAL-2026-000099", full_name="Approved Member", email="approved@example.com", phone="1234567", password_hash=hash_password("StrongPassword123!"), role=UserRole.MEMBER, status=AccountStatus.APPROVED)
    db.add(member); db.commit(); db.refresh(member)
    headers = {"Authorization": f"Bearer {create_access_token(member.id)}"}
    response = client.get("/api/v1/auth/registrations/pending", headers=headers)
    assert response.status_code == 403

def test_admin_can_create_treasurer_and_secretary_accounts(client, admin):
    from app.core.security import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}

    for role, email in [
        ("treasurer", "treasurer@example.com"),
        ("secretary", "secretary@example.com"),
    ]:
        response = client.post(
            "/api/v1/auth/staff",
            headers=headers,
            json={
                "full_name": f"Test {role.title()}",
                "email": email,
                "phone": "1234567",
                "password": "StrongPassword123!",
                "role": role,
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["role"] == role
        assert body["status"] == "approved"
        assert body["is_active"] is True
        assert "password" not in body
        assert "password_hash" not in body

        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StrongPassword123!"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == role


def test_non_admin_cannot_create_staff_account(client, db):
    from app.models import User, UserRole, AccountStatus
    from app.core.security import hash_password, create_access_token

    member = User(
        member_id="WAL-2026-000098",
        full_name="Regular Member",
        email="regular@example.com",
        phone="1234567",
        password_hash=hash_password("StrongPassword123!"),
        role=UserRole.MEMBER,
        status=AccountStatus.APPROVED,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    headers = {"Authorization": f"Bearer {create_access_token(member.id)}"}

    response = client.post(
        "/api/v1/auth/staff",
        headers=headers,
        json={
            "full_name": "Unauthorized Treasurer",
            "email": "unauthorized@example.com",
            "phone": "1234567",
            "password": "StrongPassword123!",
            "role": "treasurer",
        },
    )

    assert response.status_code == 403


def test_staff_role_cannot_be_admin_or_member(client, admin):
    from app.core.security import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}

    for role in ["admin", "member"]:
        response = client.post(
            "/api/v1/auth/staff",
            headers=headers,
            json={
                "full_name": "Invalid Staff",
                "email": f"{role}@example.com",
                "phone": "1234567",
                "password": "StrongPassword123!",
                "role": role,
            },
        )
        assert response.status_code == 422



def test_authenticated_user_can_change_password(client, admin):
    from app.core.security import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "StrongPassword123!",
            "new_password": "AnotherStrongPassword456!",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["message"]
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "StrongPassword123!"},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AnotherStrongPassword456!"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(client, admin):
    from app.core.security import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongPassword123!", "new_password": "AnotherStrongPassword456!"},
    )
    assert response.status_code == 400


def test_change_password_requires_authentication(client):
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "StrongPassword123!", "new_password": "AnotherStrongPassword456!"},
    )
    assert response.status_code == 401
