from app.core.security import create_access_token
from app.models import User, UserRole, AccountStatus

def auth(user): return {'Authorization': f'Bearer {create_access_token(user.id)}'}

def test_admin_can_publish_announcement_to_approved_members(client, db, admin):
    member=User(member_id='WAL-M-001',full_name='Approved Member',email='m1@example.com',phone='1234567',password_hash='x',role=UserRole.MEMBER,status=AccountStatus.APPROVED)
    db.add(member); db.commit()
    r=client.post('/api/v1/announcements',json={'title':'Meeting notice','message':'Meeting on Saturday'},headers=auth(admin))
    assert r.status_code==201 and r.json()['recipients']==2
    inbox=client.get('/api/v1/notifications',headers=auth(member))
    assert inbox.status_code==200 and inbox.json()[0]['title']=='Meeting notice'

def test_offline_sync_operation_is_idempotent(client, admin):
    payload={'client_operation_id':'client-op-0001','operation_type':'draft_feedback','payload':{'text':'hello'}}
    first=client.post('/api/v1/sync/operations',json=payload,headers=auth(admin))
    second=client.post('/api/v1/sync/operations',json=payload,headers=auth(admin))
    assert first.status_code==202 and second.json()['duplicate'] is True
    assert first.json()['id']==second.json()['id']

def test_finance_reports_export_formats(client, admin):
    headers=auth(admin)
    assert client.get('/api/v1/reports/summary',headers=headers).status_code==200
    assert client.get('/api/v1/reports/payments.csv',headers=headers).headers['content-type'].startswith('text/csv')
    assert 'spreadsheetml' in client.get('/api/v1/reports/payments.xlsx',headers=headers).headers['content-type']
    assert client.get('/api/v1/reports/summary.pdf',headers=headers).headers['content-type']=='application/pdf'

def test_audit_log_is_admin_only(client, admin):
    assert client.get('/api/v1/audit-logs',headers=auth(admin)).status_code==200
    assert client.get('/api/v1/audit-logs').status_code==401
