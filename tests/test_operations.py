from datetime import datetime, timezone
from app.models import User, UserRole, AccountStatus
from app.core.security import hash_password, create_access_token

def make_user(db, role, email):
    u=User(member_id=f'WAL-TEST-{email.split("@")[0]}',full_name='Test Person',email=email,phone='1234567',password_hash=hash_password('StrongPassword123!'),role=role,status=AccountStatus.APPROVED)
    db.add(u); db.commit(); db.refresh(u); return u

def headers(user): return {'Authorization':f'Bearer {create_access_token(user.id)}'}

def test_contribution_partial_payments_and_pdf_receipt(client, db, admin):
    member=make_user(db,UserRole.MEMBER,'paymember@example.com')
    h=headers(admin)
    c=client.post('/api/v1/contributions',headers=h,json={'member_id':member.id,'period':'2026-11','amount_due':'100.00'})
    assert c.status_code==201, c.text
    contribution_id=c.json()['id']
    first=client.post('/api/v1/payments',headers=h,json={'contribution_id':contribution_id,'amount':'35.00','method':'cash'})
    assert first.status_code==201, first.text
    second=client.post('/api/v1/payments',headers=h,json={'contribution_id':contribution_id,'amount':'65.00','method':'mobile'})
    assert second.status_code==201
    over=client.post('/api/v1/payments',headers=h,json={'contribution_id':contribution_id,'amount':'1.00','method':'bank'})
    assert over.status_code==400
    own=client.get('/api/v1/contributions',headers=headers(member))
    assert own.status_code==200 and own.json()[0]['balance']==0
    receipt=client.get(f"/api/v1/receipts/{first.json()['receipt_number']}.pdf",headers=headers(member))
    assert receipt.status_code==200 and receipt.content.startswith(b'%PDF')

def test_meeting_and_attendance_unique(client, db, admin):
    member=make_user(db,UserRole.MEMBER,'attendee@example.com')
    h=headers(admin)
    meeting=client.post('/api/v1/meetings',headers=h,json={'title':'Monthly Meeting','starts_at':datetime.now(timezone.utc).isoformat(),'location':'Main Hall'})
    assert meeting.status_code==201, meeting.text
    mid=meeting.json()['id']
    attendance=client.post(f'/api/v1/meetings/{mid}/attendance',headers=h,json={'member_id':member.id,'status':'present'})
    assert attendance.status_code==201
    duplicate=client.post(f'/api/v1/meetings/{mid}/attendance',headers=h,json={'member_id':member.id,'status':'present'})
    assert duplicate.status_code==409
    listing=client.get(f'/api/v1/meetings/{mid}/attendance',headers=h)
    assert listing.status_code==200 and listing.json()[0]['member_name']=='Test Person'

def test_member_directory_requires_staff_role(client, db):
    member=make_user(db,UserRole.MEMBER,'directory@example.com')
    assert client.get('/api/v1/members',headers=headers(member)).status_code==403

def test_contribution_accepts_public_member_code(client, db, admin):
    member=make_user(db,UserRole.MEMBER,'publiccode@example.com')
    response=client.post('/api/v1/contributions',headers=headers(admin),json={'member_id':member.member_id,'period':'2026-10','amount_due':'25.00'})
    assert response.status_code==201, response.text
    assert response.json()['member_id']==member.id
